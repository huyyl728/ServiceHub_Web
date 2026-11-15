#!/usr/bin/env python3
"""ServiceHub MVP API server (Python standard library + SQLite).
Run: python3 server.py. No third-party packages required.
"""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import sqlite3, json, secrets, hashlib, hmac, os, mimetypes, traceback, logging, time, re, shlex
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parent

def load_local_env(path):
    """Read this project's .env for direct `python3 server.py` runs.

    Existing environment variables always take precedence (Docker/CI/CLI).
    This is a data-only parser: it never executes shell commands.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        item = line.strip()
        if not item or item.startswith('#'):
            continue
        if item.startswith('export '):
            item = item[7:].strip()
        key, delimiter, value = item.partition('=')
        key = key.strip()
        if not delimiter or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            continue
        try:
            tokens = shlex.split(value, comments=True, posix=True)
        except ValueError:
            logging.warning('Ignoring invalid .env syntax for variable %s', key)
            continue
        os.environ.setdefault(key, ' '.join(tokens) if tokens else '')

# Running Python directly now loads .env automatically. Docker still passes its own
# environment into the container, which takes priority over this local file.
load_local_env(ROOT / '.env')
DB_PATH = Path(os.environ.get('SERVICEHUB_DB_PATH', str(ROOT / 'servicehub.db'))).expanduser().resolve()
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = ROOT / 'static' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
# SERVICEHUB_PORT sets the Python server port. Docker explicitly uses 8000 inside
# the container, while SERVICEHUB_HOST_PORT maps the public host port.
# Fallback supports running Python directly with a .env made for Docker Compose.
HOST = os.environ.get('SERVICEHUB_HOST', '127.0.0.1')
PORT = int(os.environ.get('SERVICEHUB_PORT') or os.environ.get('SERVICEHUB_HOST_PORT') or '8000')
ADMIN_EMAIL = os.environ.get('SERVICEHUB_ADMIN_EMAIL', '').strip().lower()
ADMIN_PASSWORD = os.environ.get('SERVICEHUB_ADMIN_PASSWORD', '')
LEGACY_DEMO_EMAILS = ('admin@servicehub.local', 'huy@servicehub.local', 'owner@servicehub.local')
# Base64 expands a 5 MiB image to ~6.67 MiB; leave room for JSON overhead.
MAX_BODY = 8 * 1024 * 1024
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

SCHEMA = (ROOT / 'schema.sql').read_text(encoding='utf-8')

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    return conn

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec='seconds')


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 240000)
    return salt.hex() + ':' + digest.hex()
def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(':', 1)
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), 240000).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except Exception: return False

def audit(conn, actor, action, entity='', entity_id='', details=''):
    conn.execute('INSERT INTO audit_logs(actor_id,action,entity_type,entity_id,details) VALUES(?,?,?,?,?)', (actor, action, entity, str(entity_id), details[:1000]))

def notify(conn, user_id, title, message):
    """Persist an in-app notification within the caller's DB transaction."""
    conn.execute('INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)',
                 (user_id, title[:120], message[:500]))






def configure_admin():
    """Retire public demo logins once and provision the privately configured admin."""
    if bool(ADMIN_EMAIL) != bool(ADMIN_PASSWORD):
        raise RuntimeError('Set both SERVICEHUB_ADMIN_EMAIL and SERVICEHUB_ADMIN_PASSWORD.')
    if ADMIN_EMAIL and (not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', ADMIN_EMAIL)
                        or len(ADMIN_EMAIL)>254 or len(ADMIN_PASSWORD)<16):
        raise RuntimeError('Admin email must be valid and admin password must contain at least 16 characters.')
    with connect() as c:
        c.execute('BEGIN IMMEDIATE')
        if not c.execute("SELECT 1 FROM app_settings WHERE key='demo_logins_retired_v1'").fetchone():
            for email in LEGACY_DEMO_EMAILS:
                row=c.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
                if row:
                    c.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],))
                    c.execute('UPDATE users SET login_enabled=0,is_admin=0,password_hash=? WHERE id=?',
                              (hash_password(secrets.token_urlsafe(32)),row['id']))
                    audit(c,None,'demo_login_disabled','user',row['id'])
            c.execute("INSERT INTO app_settings(key,value) VALUES('demo_logins_retired_v1','done')")
        if ADMIN_EMAIL:
            row=c.execute('SELECT * FROM users WHERE email=?',(ADMIN_EMAIL,)).fetchone()
            # A config typo must never silently promote an ordinary customer's account.
            if row and not row['is_admin'] and not (row['email']=='admin@servicehub.local' and not row['login_enabled']):
                raise RuntimeError('Admin email belongs to a non-admin account. Choose a separate admin email.')
            if row:
                changed=not row['login_enabled'] or not row['is_admin'] or not verify_password(ADMIN_PASSWORD,row['password_hash'])
                if changed:
                    c.execute('DELETE FROM sessions WHERE user_id=?',(row['id'],))
                    c.execute('UPDATE users SET password_hash=?,is_admin=1,login_enabled=1 WHERE id=?',
                              (hash_password(ADMIN_PASSWORD),row['id']))
                    audit(c,None,'admin_credentials_configured','user',row['id'])
            else:
                uid=c.execute('INSERT INTO users(name,email,password_hash,is_admin) VALUES(?,?,?,1)',
                              ('Quản trị ServiceHub',ADMIN_EMAIL,hash_password(ADMIN_PASSWORD))).lastrowid
                audit(c,None,'admin_account_created','user',uid)

def validate_demo_environment():
    from contextlib import closing

    enabled = os.environ.get('SERVICEHUB_LOCAL_DEMO') == '1'

    environment = os.environ.get(
        'SERVICEHUB_ENV', ''
    ).strip().lower()

    hosting_vars = (
        'RENDER',
        'RENDER_SERVICE_ID',
        'VERCEL',
        'DYNO',
        'WEBSITE_SITE_NAME',
        'RAILWAY_ENVIRONMENT',
        'FLY_APP_NAME',
        'K_SERVICE',
        'AWS_EXECUTION_ENV',
        'KUBERNETES_SERVICE_HOST'
    )

    local_allowed = (
        HOST == '127.0.0.1'
        and DB_PATH == (ROOT / 'servicehub.db').resolve()
        and environment in ('', 'local', 'development', 'local-demo')
        and not any(os.environ.get(x) for x in hosting_vars)
    )

    if enabled and not local_allowed:
        raise RuntimeError(
            'Chế độ demo chỉ được phép chạy trên local.'
        )

    if not DB_PATH.exists():
        return

    # Kiểm tra database mà không thay đổi dữ liệu
    with closing(sqlite3.connect(
        DB_PATH.as_uri() + '?mode=ro',
        uri=True
    )) as c:

        has_settings = c.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type='table'
               AND name='app_settings'"""
        ).fetchone()
        if has_settings:
            markers = {
        row[0] for row in c.execute(
            'SELECT key FROM app_settings WHERE key IN (?,?)',
            (
                'main_local_demo_v1',
                'local_demo_booking_only_v1'
            )
        )
    }

    legacy_allowed = (
        not enabled
        and HOST == '127.0.0.1'
        and environment == 'local-demo'
        and DB_PATH == (
            ROOT / '.local-demo' / 'servicehub-demo.db'
        ).resolve()
        and not any(os.environ.get(x) for x in hosting_vars)
    )

    if (
        ('main_local_demo_v1' in markers
         and not (enabled and local_allowed))
        or
        ('local_demo_booking_only_v1' in markers
         and not legacy_allowed)
    ):
        raise RuntimeError(
            'Database chứa dữ liệu demo. '
            'Không được sử dụng ngoài chế độ demo local.'
        )

def seed():
    validate_demo_environment()

    with connect() as c:
        c.executescript(SCHEMA)
        # Safe migrations for databases created by earlier project versions.
        user_columns = {row['name'] for row in c.execute('PRAGMA table_info(users)')}
        if 'address' not in user_columns:
            c.execute("ALTER TABLE users ADD COLUMN address TEXT DEFAULT ''")
        business_columns = {row['name'] for row in c.execute('PRAGMA table_info(businesses)')}
        if 'banner_path' not in business_columns:
            c.execute("ALTER TABLE businesses ADD COLUMN banner_path TEXT DEFAULT ''")
        service_columns = {row['name'] for row in c.execute('PRAGMA table_info(services)')}
        if 'image_path' not in service_columns:
            c.execute("ALTER TABLE services ADD COLUMN image_path TEXT DEFAULT ''")
        membership_columns = {row['name'] for row in c.execute('PRAGMA table_info(membership_programs)')}
        if 'benefits' not in membership_columns:
            c.execute("ALTER TABLE membership_programs ADD COLUMN benefits TEXT NOT NULL DEFAULT ''")
        if 'auto_approve_bookings' not in membership_columns:
            c.execute("ALTER TABLE membership_programs ADD COLUMN auto_approve_bookings INTEGER NOT NULL DEFAULT 0")
        if 'login_enabled' not in user_columns:
            c.execute('ALTER TABLE users ADD COLUMN login_enabled INTEGER NOT NULL DEFAULT 1')
        c.commit()
    configure_admin()

class APIError(Exception):
    def __init__(self, status, code, message): self.status,self.code,self.message=status,code,message

class Handler(BaseHTTPRequestHandler):
    server_version = 'ServiceHubMVP/1.0'
    def log_message(self, fmt, *args): logging.info('%s - %s', self.address_string(), fmt % args)
    def send_json(self, status, payload, extra_headers=None):
        data=json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','same-origin')
        if extra_headers:
            for k,v in extra_headers.items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)
    def body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise APIError(400,'INVALID_LENGTH','Độ dài dữ liệu gửi lên không hợp lệ.')
        if length<0: raise APIError(400,'INVALID_LENGTH','Độ dài dữ liệu gửi lên không hợp lệ.')
        if length > MAX_BODY: raise APIError(413,'BODY_TOO_LARGE','Dữ liệu gửi lên quá lớn.')
        raw=self.rfile.read(length) if length else b'{}'
        try: return json.loads(raw.decode('utf-8'))
        except Exception: raise APIError(400,'INVALID_JSON','Dữ liệu JSON không hợp lệ.')
    def route_path(self): return urlparse(self.path).path
    def auth(self, required=True):
        token=self.headers.get('Authorization','').removeprefix('Bearer ').strip()
        if not token:
            if required: raise APIError(401,'AUTH_REQUIRED','Vui lòng đăng nhập.')
            return None
        token_hash=hashlib.sha256(token.encode()).hexdigest()
        with connect() as c:
            row=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>? AND u.login_enabled=1',(token_hash,now_iso())).fetchone()
        if not row:
            if required: raise APIError(401,'SESSION_INVALID','Phiên đăng nhập hết hạn hoặc không hợp lệ.')
            return None
        return dict(row)
    def admin(self,user):
        if not user or not user['is_admin']: raise APIError(403,'ADMIN_REQUIRED','Bạn không có quyền quản trị.')
    def owner_business(self, user, bid):
        with connect() as c: row=c.execute('SELECT * FROM businesses WHERE id=? AND owner_id=?',(bid,user['id'])).fetchone()
        if not row: raise APIError(403,'BUSINESS_ACCESS_DENIED','Bạn không có quyền quản lý cơ sở này.')
        return dict(row)
    def do_OPTIONS(self): self.send_response(204); self.send_header('Access-Control-Allow-Headers','Content-Type, Authorization'); self.send_header('Access-Control-Allow-Methods','GET, POST, PUT, DELETE, OPTIONS'); self.end_headers()
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')
    def handle_request(self, method):
        p=self.route_path()
        try:
            if p.startswith('/api/'): return self.api(method,p)
            if p == '/' or p == '/index.html': return self.serve(ROOT/'static'/'index.html')
            if p == '/robots.txt': return self.serve(ROOT/'static'/'robots.txt')
            if p in ('/privacy', '/privacy-policy'): return self.serve(ROOT/'static'/'privacy.html')
            if p == '/terms': return self.serve(ROOT/'static'/'terms.html')
            if p in ('/thank-you', '/cam-on'): return self.serve(ROOT/'static'/'thank-you.html')
            if p == '/404.html': return self.serve(ROOT/'static'/'404.html')
            if p.startswith('/static/'): return self.serve(ROOT/p.lstrip('/'))
            return self.serve(ROOT/'static'/'404.html', status=404)
        except APIError as e: return self.send_json(e.status,{'success':False,'error':{'code':e.code,'message':e.message}})
        except Exception:
            logging.exception('Unhandled request error')
            return self.send_json(500,{'success':False,'error':{'code':'INTERNAL_ERROR','message':'Đã xảy ra lỗi máy chủ. Hãy kiểm tra terminal để debug.'}})
    def serve(self,path,status=200):
        try:
            path=path.resolve(); path.relative_to((ROOT/'static').resolve())
            if not path.is_file(): raise FileNotFoundError
            data=path.read_bytes(); ctype=mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
            self.send_response(status); self.send_header('Content-Type',ctype + ('; charset=utf-8' if ctype.startswith('text/') or 'javascript' in ctype else '')); self.send_header('Content-Length',str(len(data))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
        except Exception: self.send_json(404,{'success':False,'error':{'code':'NOT_FOUND','message':'Không tìm thấy tệp.'}})
    def api(self,method,p):

        # Public catalog
        if method=='GET' and p=='/api/health': return self.send_json(200,{'success':True,'data':{'status':'ok','database':str(DB_PATH.name)}})
        if method=='GET' and p.startswith('/api/businesses/') and p!='/api/businesses/managed':
            try: bid=int(p.rstrip('/').split('/')[-1])
            except ValueError: raise APIError(400,'INVALID_BUSINESS','Mã cơ sở không hợp lệ.')
            with connect() as c:
                business=c.execute("SELECT id,name,category,address,phone,description,banner_path FROM businesses WHERE id=? AND status='active'",(bid,)).fetchone()
                if not business: raise APIError(404,'BUSINESS_NOT_FOUND','Không tìm thấy cơ sở này.')
                services=[dict(r) for r in c.execute('SELECT id,business_id,name,description,price,duration_minutes,category,image_path FROM services WHERE business_id=? AND active=1 ORDER BY id DESC',(bid,))]
                programs=[dict(r) for r in c.execute('SELECT id,business_id,name,description,points_per_currency FROM membership_programs WHERE business_id=? AND active=1 ORDER BY id DESC',(bid,))]
            return self.send_json(200,{'success':True,'data':{'business':dict(business),'services':services,'memberships':programs}})
        if method=='GET' and p=='/api/services':
            q=parse_qs(urlparse(self.path).query); search=q.get('q',[''])[0].strip(); category=q.get('category',[''])[0].strip()
            sql="SELECT s.*, b.name business_name,b.address business_address,b.status business_status,b.banner_path business_banner FROM services s JOIN businesses b ON b.id=s.business_id WHERE s.active=1 AND b.status='active'"; args=[]
            if search: sql+=' AND (s.name LIKE ? OR s.description LIKE ? OR b.name LIKE ?)'; args += [f'%{search}%']*3
            if category: sql+=' AND s.category=?'; args.append(category)
            sql+=' ORDER BY s.id DESC'
            with connect() as c: rows=[dict(r) for r in c.execute(sql,args)]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='GET' and p=='/api/categories':
            with connect() as c: rows=[r[0] for r in c.execute("SELECT DISTINCT s.category FROM services s JOIN businesses b ON b.id=s.business_id WHERE s.active=1 AND b.status='active' ORDER BY s.category")]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='POST' and p=='/api/auth/register':
            d=self.body(); name=str(d.get('name','')).strip(); email=str(d.get('email','')).strip().lower(); phone=str(d.get('phone','')).strip(); pw=str(d.get('password',''))
            if len(name)<2 or '@' not in email or len(pw)<8: raise APIError(400,'VALIDATION_ERROR','Nhập họ tên hợp lệ, email hợp lệ và mật khẩu ít nhất 8 ký tự.')
            if email in LEGACY_DEMO_EMAILS or email==ADMIN_EMAIL:
                raise APIError(400,'EMAIL_RESERVED','Địa chỉ này không dùng để đăng ký. Vui lòng dùng email cá nhân của bạn.')
            with connect() as c:
                try: cur=c.execute('INSERT INTO users(name,email,phone,password_hash) VALUES(?,?,?,?)',(name,email,phone,hash_password(pw)))
                except sqlite3.IntegrityError: raise APIError(409,'EMAIL_EXISTS','Email này đã được đăng ký.')
                uid=cur.lastrowid; c.commit()
            return self.login_user(uid)
        if method=='POST' and p=='/api/auth/login':
            d=self.body(); email=str(d.get('email','')).strip().lower(); pw=str(d.get('password',''))
            with connect() as c: row=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            if not row or not row['login_enabled'] or not verify_password(pw,row['password_hash']): raise APIError(401,'LOGIN_FAILED','Email hoặc mật khẩu không đúng.')
            return self.login_user(row['id'])
        if method=='POST' and p=='/api/auth/logout':
            user=self.auth()
            token=self.headers.get('Authorization','').removeprefix('Bearer ').strip()
            with connect() as c:
                audit(c,user['id'],'logout','session',user['id'])
                c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),)); c.commit()
            return self.send_json(200,{'success':True,'message':'Đã đăng xuất.'})
        user=self.auth() if p not in ('/api/auth/register','/api/auth/login','/api/health','/api/services','/api/categories') else None
        if method=='GET' and p=='/api/me':
            with connect() as c:
                apps=[dict(r) for r in c.execute('SELECT * FROM business_applications WHERE user_id=? ORDER BY id DESC',(user['id'],))]
                businesses=[dict(r) for r in c.execute('SELECT * FROM businesses WHERE owner_id=?',(user['id'],))]
                memberships=[dict(r) for r in c.execute('SELECT um.points,um.program_id,mp.name,mp.business_id,b.name business_name FROM user_memberships um JOIN membership_programs mp ON mp.id=um.program_id LEFT JOIN businesses b ON b.id=mp.business_id WHERE um.user_id=?',(user['id'],))]
            safe={k:user[k] for k in ('id','name','email','phone','address','is_admin','created_at')}
            return self.send_json(200,{'success':True,'data':{'user':safe,'applications':apps,'businesses':businesses,'memberships':memberships}})
        if method=='PUT' and p=='/api/me':
            d=self.body(); name=str(d.get('name','')).strip(); phone=str(d.get('phone','')).strip(); address=str(d.get('address','')).strip()
            if len(name)<2: raise APIError(400,'VALIDATION_ERROR','Họ tên phải có ít nhất 2 ký tự.')
            with connect() as c:
                c.execute('UPDATE users SET name=?,phone=?,address=? WHERE id=?',(name,phone,address,user['id']))
                audit(c,user['id'],'profile_updated','user',user['id'])
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã cập nhật hồ sơ.'})
        if method=='POST' and p=='/api/business-applications':
            d=self.body(); name=str(d.get('business_name','')).strip(); cat=str(d.get('category','')).strip(); addr=str(d.get('address','')).strip(); phone=str(d.get('phone','')).strip(); desc=str(d.get('description','')).strip()
            if not all([name,cat,addr,phone]): raise APIError(400,'VALIDATION_ERROR','Vui lòng nhập tên cơ sở, loại hình, địa chỉ và số điện thoại.')
            with connect() as c:
                existing=c.execute("SELECT id FROM business_applications WHERE user_id=? AND status IN ('pending','approved')",(user['id'],)).fetchone()
                if existing: raise APIError(409,'APPLICATION_EXISTS','Bạn đã có hồ sơ đang chờ duyệt hoặc đã được chấp thuận.')
                cur=c.execute('INSERT INTO business_applications(user_id,business_name,category,address,phone,description) VALUES(?,?,?,?,?,?)',(user['id'],name,cat,addr,phone,desc)); aid=cur.lastrowid
                audit(c,user['id'],'business_application_submitted','business_application',aid); c.commit()
            return self.send_json(201,{'success':True,'message':'Đã gửi hồ sơ.','data':{'id':aid,'status':'pending'}})
        if method=='PUT' and p.startswith('/api/business-applications/'):
            aid=self.int_tail(p); d=self.body()
            with connect() as c:
                row=c.execute('SELECT * FROM business_applications WHERE id=? AND user_id=?',(aid,user['id'])).fetchone()
                if not row: raise APIError(404,'APPLICATION_NOT_FOUND','Không tìm thấy hồ sơ.')
                if row['status'] not in ('changes_requested','rejected'): raise APIError(409,'APPLICATION_LOCKED','Hồ sơ này không thể chỉnh sửa ở trạng thái hiện tại.')
                vals=[str(d.get(k,row[col])).strip() for k,col in [('business_name','business_name'),('category','category'),('address','address'),('phone','phone'),('description','description')]]
                if not all(vals[:4]): raise APIError(400,'VALIDATION_ERROR','Vui lòng điền đủ thông tin bắt buộc.')
                c.execute("UPDATE business_applications SET business_name=?,category=?,address=?,phone=?,description=?,status='pending',review_note='',updated_at=CURRENT_TIMESTAMP WHERE id=?",(*vals,aid)); c.commit()
            return self.send_json(200,{'success':True,'message':'Đã gửi lại hồ sơ.'})
        if method=='GET' and p=='/api/business-applications/me':
            with connect() as c: rows=[dict(r) for r in c.execute('SELECT * FROM business_applications WHERE user_id=? ORDER BY id DESC',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if p=='/api/admin/applications':
            self.admin(user)
            if method=='GET':
                with connect() as c: rows=[dict(r) for r in c.execute('SELECT a.*,u.name user_name,u.email user_email FROM business_applications a JOIN users u ON u.id=a.user_id ORDER BY CASE a.status WHEN "pending" THEN 0 ELSE 1 END,a.id DESC')]
                return self.send_json(200,{'success':True,'data':rows})
        # Admin review routes are /api/admin/applications/{id}/approve|changes|reject
        if method=='POST' and p.startswith('/api/admin/applications/'):
            self.admin(user); parts=p.strip('/').split('/')
            if len(parts)!=5: raise APIError(404,'NOT_FOUND','Endpoint xét duyệt không hợp lệ.')
            aid=int(parts[3]); action=parts[4]; d=self.body(); note=str(d.get('note','')).strip()
            with connect() as c:
                app=c.execute('SELECT * FROM business_applications WHERE id=?',(aid,)).fetchone()
                if not app: raise APIError(404,'APPLICATION_NOT_FOUND','Không tìm thấy hồ sơ.')
                if app['status']!='pending': raise APIError(409,'APPLICATION_NOT_PENDING','Hồ sơ không còn ở trạng thái chờ duyệt.')
                if action=='approve':
                    cur=c.execute('INSERT INTO businesses(name,category,address,phone,description,owner_id,status) VALUES(?,?,?,?,?,?,?)',(app['business_name'],app['category'],app['address'],app['phone'],app['description'],app['user_id'],'active'))
                    bid=cur.lastrowid
                    c.execute("UPDATE business_applications SET status='approved',review_note=?,reviewed_by=?,business_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(note,user['id'],bid,aid))
                    c.execute('INSERT INTO membership_programs(business_id,name,description) VALUES(?,?,?)',(bid,app['business_name']+' Member','Chương trình hội viên do cơ sở quản lý.'))
                    c.execute('INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)',(app['user_id'],'Hồ sơ được chấp thuận',f'Cơ sở {app["business_name"]} đã được duyệt. Bạn có thể quản lý cơ sở.'))
                elif action in ('changes','reject'):
                    status='changes_requested' if action=='changes' else 'rejected'
                    if not note: raise APIError(400,'NOTE_REQUIRED','Vui lòng ghi lý do xử lý hồ sơ.')
                    c.execute('UPDATE business_applications SET status=?,review_note=?,reviewed_by=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(status,note,user['id'],aid))
                    title='Cần bổ sung hồ sơ' if action=='changes' else 'Hồ sơ chưa được chấp thuận'
                    c.execute('INSERT INTO notifications(user_id,title,message) VALUES(?,?,?)',(app['user_id'],title,note))
                else: raise APIError(404,'INVALID_ACTION','Thao tác xét duyệt không hợp lệ.')
                audit(c,user['id'],'application_'+action,'business_application',aid,note); c.commit()
            return self.send_json(200,{'success':True,'message':'Đã xử lý hồ sơ.'})
        if method=='GET' and p=='/api/businesses/managed':
            with connect() as c: rows=[dict(r) for r in c.execute('SELECT * FROM businesses WHERE owner_id=? ORDER BY id DESC',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='PUT' and p.startswith('/api/owner/businesses/'):
            bid=self.int_parts(p,3); business=self.owner_business(user,bid); d=self.body()
            name=str(d.get('name',business['name'])).strip(); category=str(d.get('category',business['category'])).strip(); address=str(d.get('address',business['address'])).strip(); phone=str(d.get('phone',business['phone'])).strip(); description=str(d.get('description',business['description'] or '')).strip()
            if len(name)<2 or not category or len(address)<3 or len(phone)<6: raise APIError(400,'VALIDATION_ERROR','Vui lòng nhập tên, loại hình, địa chỉ và số điện thoại hợp lệ.')
            with connect() as c:
                c.execute('UPDATE businesses SET name=?,category=?,address=?,phone=?,description=? WHERE id=? AND owner_id=?',(name,category,address,phone,description,bid,user['id']))
                audit(c,user['id'],'business_profile_updated','business',bid)
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã cập nhật thông tin cơ sở.'})
        if p=='/api/owner/services':
            if method=='GET':
                bid=int(parse_qs(urlparse(self.path).query).get('business_id',['0'])[0]); self.owner_business(user,bid)
                with connect() as c: rows=[dict(r) for r in c.execute('SELECT * FROM services WHERE business_id=? ORDER BY id DESC',(bid,))]
                return self.send_json(200,{'success':True,'data':rows})
            if method=='POST':
                d=self.body(); bid=int(d.get('business_id',0)); self.owner_business(user,bid)
                name=str(d.get('name','')).strip(); desc=str(d.get('description','')).strip(); cat=str(d.get('category','')).strip(); price=int(d.get('price',-1)); dur=int(d.get('duration_minutes',60))
                if not name or not cat or price<0 or dur<1 or dur>1440: raise APIError(400,'VALIDATION_ERROR','Tên, danh mục, giá hoặc thời lượng không hợp lệ.')
                with connect() as c: cur=c.execute('INSERT INTO services(business_id,name,description,price,duration_minutes,category) VALUES(?,?,?,?,?,?)',(bid,name,desc,price,dur,cat)); c.commit(); sid=cur.lastrowid
                return self.send_json(201,{'success':True,'data':{'id':sid},'message':'Đã tạo dịch vụ.'})
        if p.startswith('/api/owner/services/') and p.endswith('/image') and method=='POST':
            # Service photos are stored independently from the business banner.
            parts=p.strip('/').split('/')
            try: sid=int(parts[3])
            except (IndexError, TypeError, ValueError): raise APIError(400,'INVALID_SERVICE_ID','Dịch vụ được chọn không hợp lệ.')
            with connect() as c: svc=c.execute('SELECT * FROM services WHERE id=?',(sid,)).fetchone()
            if not svc: raise APIError(404,'SERVICE_NOT_FOUND','Không tìm thấy dịch vụ.')
            self.owner_business(user,svc['business_id'])
            d=self.body(); filename=Path(str(d.get('filename','image.png'))).name[:180]
            data_url=str(d.get('data_url',''))
            if not data_url.startswith('data:image/') or ';base64,' not in data_url: raise APIError(400,'INVALID_IMAGE','Chỉ chấp nhận ảnh PNG/JPEG/WebP dạng data URL.')
            import base64
            header,payload=data_url.split(';base64,',1); mime=header[5:]
            if mime not in ('image/png','image/jpeg','image/webp'): raise APIError(400,'INVALID_IMAGE_TYPE','Định dạng ảnh không được hỗ trợ. Hãy chọn PNG, JPG hoặc WebP.')
            try: raw=base64.b64decode(payload,validate=True)
            except Exception: raise APIError(400,'INVALID_IMAGE','Dữ liệu ảnh không hợp lệ. Hãy chọn lại ảnh và thử lại.')
            if not raw: raise APIError(400,'EMPTY_IMAGE','Tệp ảnh đang trống.')
            if len(raw)>5*1024*1024: raise APIError(413,'IMAGE_TOO_LARGE','Ảnh tối đa 5 MB.')
            signatures={'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'),
                        'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
                        'image/webp': len(raw)>=12 and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP'}
            if not signatures.get(mime,False): raise APIError(400,'IMAGE_CONTENT_MISMATCH','Nội dung tệp không khớp định dạng ảnh. Hãy chọn một ảnh PNG/JPG/WebP hợp lệ.')
            ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[mime]
            name=f'service-{sid}-{secrets.token_hex(8)}{ext}'; dest=UPLOAD_DIR/name; url='/static/uploads/'+name
            old_path=svc['image_path'] or ''
            try:
                dest.write_bytes(raw)
                with connect() as c:
                    updated=c.execute('UPDATE services SET image_path=? WHERE id=?',(url,sid))
                    if updated.rowcount != 1: raise APIError(404,'SERVICE_NOT_FOUND','Không tìm thấy dịch vụ.')
                    audit(c,user['id'],'service_image_uploaded','service',sid,filename); c.commit()
            except Exception:
                dest.unlink(missing_ok=True)
                raise
            # Remove only the previous uploaded service image, never the business banner or another service image.
            if old_path.startswith('/static/uploads/service-'+str(sid)+'-'):
                try: (ROOT / old_path.lstrip('/')).unlink(missing_ok=True)
                except OSError: logging.warning('Could not remove old service image %s', old_path)
            return self.send_json(201,{'success':True,'data':{'url':url,'service_id':sid,'business_id':svc['business_id']},'message':'Đã cập nhật ảnh riêng cho dịch vụ.'})
        if p.startswith('/api/owner/services/'):
            sid=self.int_tail(p)
            with connect() as c: svc=c.execute('SELECT * FROM services WHERE id=?',(sid,)).fetchone()
            if not svc: raise APIError(404,'SERVICE_NOT_FOUND','Không tìm thấy dịch vụ.')
            self.owner_business(user,svc['business_id'])
            if method=='PUT':
                d=self.body(); name=str(d.get('name',svc['name'])).strip(); desc=str(d.get('description',svc['description'])).strip(); cat=str(d.get('category',svc['category'])).strip(); price=int(d.get('price',svc['price'])); dur=int(d.get('duration_minutes',svc['duration_minutes'])); active=1 if d.get('active',bool(svc['active'])) else 0
                if not name or price<0 or dur<1: raise APIError(400,'VALIDATION_ERROR','Thông tin dịch vụ không hợp lệ.')
                with connect() as c: c.execute('UPDATE services SET name=?,description=?,category=?,price=?,duration_minutes=?,active=? WHERE id=?',(name,desc,cat,price,dur,active,sid))
                return self.send_json(200,{'success':True,'message':'Đã cập nhật dịch vụ.'})
            if method=='DELETE':
                with connect() as c: c.execute('UPDATE services SET active=0 WHERE id=?',(sid,))
                return self.send_json(200,{'success':True,'message':'Đã ngừng cung cấp dịch vụ.'})
        if method=='GET' and p=='/api/owner/membership':
            bid=int(parse_qs(urlparse(self.path).query).get('business_id',['0'])[0]); self.owner_business(user,bid)
            with connect() as c:
                row=c.execute('SELECT * FROM membership_programs WHERE business_id=? ORDER BY id DESC LIMIT 1',(bid,)).fetchone()
                if not row:
                    cur=c.execute('INSERT INTO membership_programs(business_id,name,description,benefits,auto_approve_bookings) VALUES(?,?,?,?,0)',(bid,'Hội viên thân thiết','Chương trình hội viên của cơ sở','Ưu đãi dành riêng cho hội viên.'))
                    c.commit(); row=c.execute('SELECT * FROM membership_programs WHERE id=?',(cur.lastrowid,)).fetchone()
            return self.send_json(200,{'success':True,'data':dict(row)})
        if method=='PUT' and p=='/api/owner/membership':
            d=self.body(); bid=int(d.get('business_id',0)); self.owner_business(user,bid)
            name=str(d.get('name','')).strip()[:120]; description=str(d.get('description','')).strip()[:1000]; benefits=str(d.get('benefits','')).strip()[:2000]; points=max(0,min(1000,int(d.get('points_per_currency',1)))); auto=1 if d.get('auto_approve_bookings') else 0; active=1 if d.get('active',True) else 0
            if not name: raise APIError(400,'VALIDATION_ERROR','Tên chương trình hội viên không được để trống.')
            with connect() as c:
                row=c.execute('SELECT id FROM membership_programs WHERE business_id=? ORDER BY id DESC LIMIT 1',(bid,)).fetchone()
                if row: c.execute('UPDATE membership_programs SET name=?,description=?,benefits=?,points_per_currency=?,auto_approve_bookings=?,active=? WHERE id=?',(name,description,benefits,points,auto,active,row['id']))
                else: c.execute('INSERT INTO membership_programs(business_id,name,description,benefits,points_per_currency,auto_approve_bookings,active) VALUES(?,?,?,?,?,?,?)',(bid,name,description,benefits,points,auto,active))
                audit(c,user['id'],'membership_program_updated','business',bid,'auto_approve_bookings='+str(auto)); c.commit()
            return self.send_json(200,{'success':True,'message':'Đã lưu chương trình hội viên của cơ sở.'})
        if method=='GET' and p=='/api/owner/members':
            try: bid=int(parse_qs(urlparse(self.path).query).get('business_id',['0'])[0])
            except ValueError: raise APIError(400,'INVALID_BUSINESS_ID','Mã cơ sở không hợp lệ.')
            self.owner_business(user,bid)
            with connect() as c:
                rows=[dict(r) for r in c.execute('SELECT u.name member_name,um.points,um.joined_at,mp.name program_name FROM user_memberships um JOIN membership_programs mp ON mp.id=um.program_id JOIN users u ON u.id=um.user_id WHERE mp.business_id=? ORDER BY um.joined_at DESC,um.id DESC LIMIT 100',(bid,))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='GET' and p=='/api/owner/bookings':
            bid=int(parse_qs(urlparse(self.path).query).get('business_id',['0'])[0]); self.owner_business(user,bid)
            with connect() as c: rows=[dict(r) for r in c.execute('SELECT bk.*,s.name service_name,u.name customer_name,u.phone customer_phone FROM bookings bk JOIN services s ON s.id=bk.service_id JOIN users u ON u.id=bk.user_id WHERE bk.business_id=? ORDER BY bk.booking_date DESC,bk.start_time',(bid,))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='POST' and p.startswith('/api/owner/bookings/'):
            parts=p.strip('/').split('/'); bid=int(parts[3]); action=parts[4]; self.owner_business(user,bid); d=self.body(); booking_id=int(d.get('booking_id',0))
            if action not in ('confirm','complete','cancel'): raise APIError(404,'INVALID_ACTION','Thao tác không hợp lệ.')
            status={'confirm':'confirmed','complete':'completed','cancel':'cancelled'}[action]
            with connect() as c:
                row=c.execute('SELECT * FROM bookings WHERE id=? AND business_id=?',(booking_id,bid)).fetchone()
                if not row: raise APIError(404,'BOOKING_NOT_FOUND','Không tìm thấy lịch đặt.')
                allowed={'confirm':['pending'],'complete':['confirmed'],'cancel':['pending','confirmed']}
                if row['status'] not in allowed[action]: raise APIError(409,'INVALID_BOOKING_STATE','Không thể chuyển lịch đặt từ trạng thái hiện tại.')
                c.execute('UPDATE bookings SET status=? WHERE id=?',(status,booking_id)); notify(c,row['user_id'],'Lịch đặt được cập nhật',f'Lịch đặt #{booking_id} hiện có trạng thái {status}.'); c.commit()
            return self.send_json(200,{'success':True,'message':'Đã cập nhật lịch đặt.'})
        if method=='GET' and p=='/api/bookings/me':
            with connect() as c: rows=[dict(r) for r in c.execute('SELECT bk.*,s.name service_name,b.name business_name,b.address business_address FROM bookings bk JOIN services s ON s.id=bk.service_id JOIN businesses b ON b.id=bk.business_id WHERE bk.user_id=? ORDER BY bk.booking_date DESC,bk.start_time DESC',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='GET' and p.startswith('/api/services/') and p.endswith('/availability'):
            sid=int(p.split('/')[3]); q=parse_qs(urlparse(self.path).query); date=q.get('date',[''])[0]
            try: datetime.strptime(date,'%Y-%m-%d')
            except Exception: raise APIError(400,'INVALID_DATE','Ngày phải có định dạng YYYY-MM-DD.')
            with connect() as c:
                svc=c.execute('SELECT * FROM services WHERE id=? AND active=1',(sid,)).fetchone()
                if not svc: raise APIError(404,'SERVICE_NOT_FOUND','Không tìm thấy dịch vụ.')
                booked=c.execute("SELECT start_time,end_time FROM bookings WHERE service_id=? AND booking_date=? AND status IN ('pending','confirmed')",(sid,date)).fetchall()
            slots=[]
            for hour in range(8,21):
                start=f'{hour:02d}:00'; enddt=datetime.strptime(start,'%H:%M')+timedelta(minutes=svc['duration_minutes']); end=enddt.strftime('%H:%M')
                if enddt.hour>22 or (enddt.hour==22 and enddt.minute>0): continue
                busy=any(start < r['end_time'] and end > r['start_time'] for r in booked)
                if not busy: slots.append({'start_time':start,'end_time':end})
            return self.send_json(200,{'success':True,'data':slots})
        if method=='POST' and p=='/api/bookings':
            d=self.body(); sid=int(d.get('service_id',0)); date=str(d.get('date','')); start=str(d.get('start_time',''))
            try: datetime.strptime(date,'%Y-%m-%d'); st=datetime.strptime(start,'%H:%M')
            except Exception: raise APIError(400,'INVALID_DATETIME','Ngày hoặc giờ không hợp lệ.')
            with connect() as c:
                c.execute('BEGIN IMMEDIATE')  # Serialize competing booking attempts before checking availability.
                svc=c.execute('SELECT s.*,b.status business_status FROM services s JOIN businesses b ON b.id=s.business_id WHERE s.id=? AND s.active=1',(sid,)).fetchone()
                if not svc or svc['business_status']!='active': raise APIError(404,'SERVICE_UNAVAILABLE','Dịch vụ không còn khả dụng.')
                end=(st+timedelta(minutes=svc['duration_minutes'])).strftime('%H:%M')
                if st.hour<8 or (st+timedelta(minutes=svc['duration_minutes'])).hour>22: raise APIError(400,'OUTSIDE_HOURS','Chỉ hỗ trợ đặt lịch trong khoảng 08:00–22:00.')
                if date < datetime.now().strftime('%Y-%m-%d'): raise APIError(400,'PAST_DATE','Không thể đặt lịch trong quá khứ.')
                overlap=c.execute("SELECT id FROM bookings WHERE service_id=? AND booking_date=? AND status IN ('pending','confirmed') AND start_time < ? AND end_time > ?",(sid,date,end,start)).fetchone()
                if overlap: raise APIError(409,'SLOT_TAKEN','Khung giờ vừa được người khác đặt. Hãy chọn giờ khác.')
                auto_program=c.execute('SELECT mp.id FROM membership_programs mp JOIN user_memberships um ON um.program_id=mp.id AND um.user_id=? WHERE mp.business_id=? AND mp.active=1 AND mp.auto_approve_bookings=1 ORDER BY mp.id DESC LIMIT 1',(user['id'],svc['business_id'])).fetchone()
                booking_status='confirmed' if auto_program else 'pending'
                cur=c.execute('INSERT INTO bookings(user_id,service_id,business_id,booking_date,start_time,end_time,status,price) VALUES(?,?,?,?,?,?,?,?)',(user['id'],sid,svc['business_id'],date,start,end,booking_status,svc['price'])); bid=cur.lastrowid
                owner_id=c.execute('SELECT owner_id FROM businesses WHERE id=?',(svc['business_id'],)).fetchone()[0]
                note='Hội viên được tự động xác nhận lịch đặt' if auto_program else 'Có lịch đặt mới'
                notify(c,owner_id,note,f'Lịch đặt #{bid} được tạo với trạng thái {booking_status}.')
                notify(c,user['id'],'Đặt lịch thành công' if auto_program else 'Đã gửi yêu cầu đặt lịch',f'Lịch đặt #{bid} tại cơ sở đã có trạng thái {booking_status}.')
                audit(c,user['id'],'booking_created','booking',bid,'service_id='+str(sid)+'; date='+date+'; start='+start+'; status='+booking_status)
                c.commit()
            msg='Đặt lịch đã được tự động xác nhận nhờ quyền lợi hội viên.' if auto_program else 'Đã tạo yêu cầu đặt lịch.'
            return self.send_json(201,{'success':True,'message':msg,'data':{'id':bid,'status':booking_status,'price':svc['price']}})
        if method=='POST' and p.startswith('/api/bookings/') and p.endswith('/cancel'):
            bid=self.int_parts(p,2)
            with connect() as c:
                row=c.execute('SELECT * FROM bookings WHERE id=? AND user_id=?',(bid,user['id'])).fetchone()
                if not row: raise APIError(404,'BOOKING_NOT_FOUND','Không tìm thấy lịch đặt.')
                if row['status'] not in ('pending','confirmed'): raise APIError(409,'BOOKING_CANNOT_CANCEL','Lịch đặt không thể hủy ở trạng thái hiện tại.')
                c.execute("UPDATE bookings SET status='cancelled' WHERE id=?",(bid,)); audit(c,user['id'],'booking_cancelled','booking',bid)
                owner_id=c.execute('SELECT owner_id FROM businesses WHERE id=?',(row['business_id'],)).fetchone()[0]
                notify(c,owner_id,'Khách hủy lịch',f'Lịch đặt #{bid} đã được khách hàng hủy.')
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã hủy lịch đặt.'})
        if method=='GET' and p=='/api/activity/me':
            with connect() as c:
                rows=[dict(r) for r in c.execute('SELECT action,entity_type,entity_id,details,created_at FROM audit_logs WHERE actor_id=? ORDER BY id DESC LIMIT 100',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='GET' and p=='/api/memberships/me':
            with connect() as c: rows=[dict(r) for r in c.execute('SELECT mp.*,b.name business_name,um.points,um.joined_at FROM membership_programs mp LEFT JOIN businesses b ON b.id=mp.business_id LEFT JOIN user_memberships um ON um.program_id=mp.id AND um.user_id=? WHERE mp.active=1',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='POST' and p.startswith('/api/memberships/') and p.endswith('/join'):
            pid=self.int_parts(p,2)
            with connect() as c:
                prog=c.execute('SELECT * FROM membership_programs WHERE id=? AND active=1',(pid,)).fetchone()
                if not prog: raise APIError(404,'PROGRAM_NOT_FOUND','Không tìm thấy chương trình hội viên.')
                added=c.execute('INSERT OR IGNORE INTO user_memberships(user_id,program_id) VALUES(?,?)',(user['id'],pid)).rowcount
                if added:
                    notify(c,user['id'],'Đăng ký hội viên thành công',f'Bạn đã tham gia chương trình {prog["name"]}.')
                    audit(c,user['id'],'membership_joined','membership_program',pid)
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã tham gia chương trình hội viên.'})
        # Sprint 4: customer notification center (all operations scoped by user_id).
        if method=='GET' and p=='/api/notifications/unread-count':
            with connect() as c:
                unread=c.execute('SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0',(user['id'],)).fetchone()[0]
            return self.send_json(200,{'success':True,'data':{'unread':unread}})
        if method=='GET' and p=='/api/notifications':
            with connect() as c:
                rows=[dict(r) for r in c.execute('SELECT id,title,message,is_read,created_at FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50',(user['id'],))]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='POST' and p=='/api/notifications/read-all':
            with connect() as c:
                changed=c.execute('UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0',(user['id'],)).rowcount
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã đánh dấu tất cả thông báo là đã đọc.','data':{'updated':changed}})
        if method=='POST' and p.startswith('/api/notifications/') and p.endswith('/read'):
            nid=self.int_parts(p,2)
            with connect() as c:
                row=c.execute('SELECT id FROM notifications WHERE id=? AND user_id=?',(nid,user['id'])).fetchone()
                if not row: raise APIError(404,'NOTIFICATION_NOT_FOUND','Không tìm thấy thông báo của bạn.')
                c.execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?',(nid,user['id']))
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã đọc thông báo.'})
        if method=='POST' and p=='/api/media/upload':
            # Dependency-free JSON data URL upload for this local demo.
            d=self.body()
            try: bid=int(d.get('business_id',0))
            except (TypeError,ValueError): raise APIError(400,'INVALID_BUSINESS_ID','Cơ sở được chọn không hợp lệ.')
            business=self.owner_business(user,bid)
            filename=Path(str(d.get('filename','image.png'))).name[:180]
            data_url=str(d.get('data_url',''))
            if not data_url.startswith('data:image/') or ';base64,' not in data_url: raise APIError(400,'INVALID_IMAGE','Chỉ chấp nhận ảnh PNG/JPEG/WebP dạng data URL.')
            import base64
            header,payload=data_url.split(';base64,',1); mime=header[5:]
            if mime not in ('image/png','image/jpeg','image/webp'): raise APIError(400,'INVALID_IMAGE_TYPE','Định dạng ảnh không được hỗ trợ. Hãy chọn PNG, JPG hoặc WebP.')
            try: raw=base64.b64decode(payload,validate=True)
            except Exception: raise APIError(400,'INVALID_IMAGE','Dữ liệu ảnh không hợp lệ. Hãy chọn lại ảnh và thử lại.')
            if not raw: raise APIError(400,'EMPTY_IMAGE','Tệp ảnh đang trống.')
            if len(raw)>5*1024*1024: raise APIError(413,'IMAGE_TOO_LARGE','Ảnh tối đa 5 MB.')
            # Validate actual file signature, not only the browser-provided MIME type.
            signatures={'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'),
                        'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
                        'image/webp': len(raw)>=12 and raw[:4]==b'RIFF' and raw[8:12]==b'WEBP'}
            if not signatures.get(mime,False): raise APIError(400,'IMAGE_CONTENT_MISMATCH','Nội dung tệp không khớp định dạng ảnh. Hãy chọn một ảnh PNG/JPG/WebP hợp lệ.')
            ext={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[mime]
            name=secrets.token_hex(12)+ext; dest=UPLOAD_DIR/name; url='/static/uploads/'+name
            try:
                dest.write_bytes(raw)
                with connect() as c:
                    updated=c.execute('UPDATE businesses SET banner_path=? WHERE id=? AND owner_id=?',(url,bid,user['id']))
                    if updated.rowcount != 1: raise APIError(403,'BUSINESS_ACCESS_DENIED','Bạn không có quyền cập nhật ảnh cơ sở này.')
                    audit(c,user['id'],'media_uploaded','business',bid,filename); c.commit()
            except Exception:
                try: dest.unlink(missing_ok=True)
                except Exception: pass
                raise
            return self.send_json(201,{'success':True,'data':{'url':url,'business_id':bid,'business_name':business['name']},'message':'Đã tải banner lên và cập nhật cơ sở thành công.'})
        if method=='GET' and p=='/api/admin/stats':
            self.admin(user)
            with connect() as c: data={'users':c.execute('SELECT COUNT(*) FROM users WHERE is_admin=0').fetchone()[0],'pending_applications':c.execute("SELECT COUNT(*) FROM business_applications WHERE status='pending'").fetchone()[0],'businesses':c.execute('SELECT COUNT(*) FROM businesses').fetchone()[0],'bookings':c.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]}
            return self.send_json(200,{'success':True,'data':data})
        if method=='GET' and p=='/api/admin/reports':
            self.admin(user)
            with connect() as c:
                booking_rows=[dict(r) for r in c.execute('SELECT status,COUNT(*) amount FROM bookings GROUP BY status')]
                report={
                    'active_businesses':c.execute("SELECT COUNT(*) FROM businesses WHERE status='active'").fetchone()[0],
                    'suspended_businesses':c.execute("SELECT COUNT(*) FROM businesses WHERE status='suspended'").fetchone()[0],
                    'active_services':c.execute("SELECT COUNT(*) FROM services s JOIN businesses b ON b.id=s.business_id WHERE s.active=1 AND b.status='active'").fetchone()[0],
                    'memberships':c.execute('SELECT COUNT(*) FROM user_memberships').fetchone()[0],
                    'booking_statuses':{r['status']:r['amount'] for r in booking_rows},
                }
            return self.send_json(200,{'success':True,'data':report})
        if method=='GET' and p=='/api/admin/audit':
            self.admin(user)
            with connect() as c:
                rows=[dict(r) for r in c.execute('SELECT a.id,u.name actor_name,a.action,a.entity_type,a.entity_id,a.created_at FROM audit_logs a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 50')]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='GET' and p=='/api/admin/businesses':
            self.admin(user)
            with connect() as c:
                rows=[dict(r) for r in c.execute('SELECT b.id,b.name,b.category,b.status,u.name owner_name,(SELECT COUNT(*) FROM services WHERE business_id=b.id) service_count FROM businesses b JOIN users u ON u.id=b.owner_id ORDER BY b.id DESC LIMIT 100')]
            return self.send_json(200,{'success':True,'data':rows})
        if method=='POST' and p.startswith('/api/admin/businesses/') and p.endswith('/status'):
            self.admin(user)
            bid=self.int_parts(p,3)
            d=self.body(); status=str(d.get('status','')).strip()
            if status not in ('active','suspended'):
                raise APIError(400,'INVALID_STATUS','Trạng thái phải là active hoặc suspended.')
            with connect() as c:
                row=c.execute('SELECT id,owner_id,name,status FROM businesses WHERE id=?',(bid,)).fetchone()
                if not row: raise APIError(404,'BUSINESS_NOT_FOUND','Không tìm thấy cơ sở.')
                if row['status']==status:
                    raise APIError(409,'STATUS_UNCHANGED','Cơ sở đã ở trạng thái được chọn.')
                c.execute('UPDATE businesses SET status=? WHERE id=?',(status,bid))
                notify(c,row['owner_id'],'Trạng thái cơ sở thay đổi',f'Cơ sở {row["name"]} đã được {"kích hoạt" if status=="active" else "tạm dừng"} bởi quản trị viên.')
                audit(c,user['id'],'business_status_changed','business',bid,'status='+status)
                c.commit()
            return self.send_json(200,{'success':True,'message':'Đã cập nhật trạng thái cơ sở.'})
        raise APIError(404,'ENDPOINT_NOT_FOUND',f'Không tìm thấy API: {method} {p}')
    def int_tail(self,p):
        try: return int(p.rstrip('/').split('/')[-1])
        except Exception: raise APIError(400,'INVALID_ID','ID không hợp lệ.')
    def int_parts(self,p,index):
        try: return int(p.strip('/').split('/')[index])
        except Exception: raise APIError(400,'INVALID_ID','ID không hợp lệ.')
    def login_user(self,uid):
        token=secrets.token_urlsafe(36); token_hash=hashlib.sha256(token.encode()).hexdigest(); expiry=(datetime.now(timezone.utc)+timedelta(hours=12)).isoformat(timespec='seconds')
        with connect() as c:
            c.execute('INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',(token_hash,uid,expiry)); audit(c,uid,'login','session',uid); row=c.execute('SELECT id,name,email,phone,address,is_admin,created_at FROM users WHERE id=?',(uid,)).fetchone(); c.commit()
        return self.send_json(200,{'success':True,'data':{'token':token,'user':dict(row)},'message':'Đăng nhập thành công.'})
def seed_local_demo():

    # Chỉ chạy khi bật chế độ demo
    if os.environ.get('SERVICEHUB_LOCAL_DEMO') != '1':
        return

    from contextlib import closing
    from scripts.local_demo import (
        CUSTOMERS, OWNERS, BUSINESSES,
        private_json_write
    )

    # Không cho phép tạo demo khi triển khai public
    hosting_vars = (
        'RENDER', 'RENDER_SERVICE_ID', 'VERCEL',
        'DYNO', 'WEBSITE_SITE_NAME'
    )

    if (
        HOST != '127.0.0.1'
        or DB_PATH != (ROOT / 'servicehub.db').resolve()
        or any(os.environ.get(x) for x in hosting_vars)
        or os.environ.get('SERVICEHUB_ENV', '').lower()
        in ('production', 'prod')
    ):
        raise RuntimeError('Demo chỉ được phép chạy trên local.')

    store = ROOT / '.local-demo'
    store.mkdir(mode=0o700, exist_ok=True)
    store.chmod(0o700)

    credentials_path = store / 'main-credentials.json'
    marker = 'main_local_demo_v1'

    with closing(connect()) as c, c:
        c.execute('BEGIN IMMEDIATE')

        # Không tạo lại dữ liệu sau mỗi lần chạy
        if c.execute(
            'SELECT 1 FROM app_settings WHERE key=?',
            (marker,)
        ).fetchone():
            logging.info('Dữ liệu demo local đã được khởi tạo.')
            return

        # Giữ nguyên Admin cá nhân
        admin = c.execute(
            '''SELECT id FROM users
               WHERE email=? AND is_admin=1
               AND login_enabled=1''',
            (ADMIN_EMAIL,)
        ).fetchone()

        if not admin:
            raise RuntimeError('Hãy cấu hình Admin trước.')

        if credentials_path.exists():
            raise RuntimeError(
                'Đã tồn tại file thông tin demo. '
                'Cần kiểm tra trước khi tạo lại.'
            )

        users = []
        ids = {}

        # Tạo 3 Customer và 3 Owner
        for email, name, role in CUSTOMERS + OWNERS:

            if c.execute(
                'SELECT 1 FROM users WHERE email=?',
                (email,)
            ).fetchone():
                raise RuntimeError(
                    'Email demo đã tồn tại: ' + email
                )

            password = secrets.token_urlsafe(24)

            cursor = c.execute(
                '''INSERT INTO users
                   (name,email,password_hash,is_admin)
                   VALUES(?,?,?,0)''',
                (name, email, hash_password(password))
            )

            ids[email] = cursor.lastrowid

            users.append({
                'email': email,
                'name': name,
                'role': role,
                'password': password
            })

        # Tạo cơ sở và dịch vụ mẫu
        for owner, business in zip(OWNERS, BUSINESSES):

            owner_id = ids[owner[0]]
            name, category, address, banner, services = business

            business_id = c.execute(
                '''INSERT INTO businesses
                   (name,category,address,phone,description,
                    owner_id,status,banner_path)
                   VALUES(?,?,?,?,?,?,?,?)''',
                (
                    name, category, address,
                    '0000000000', 'Cơ sở demo local',
                    owner_id, 'active', banner
                )
            ).lastrowid

            c.execute(
                '''INSERT INTO business_applications
                   (user_id,business_name,category,address,
                    phone,description,status,reviewed_by,business_id)
                   VALUES(?,?,?,?,?,?,?,?,?)''',
                (
                    owner_id, name, category, address,
                    '0000000000', 'Dữ liệu demo',
                    'approved', admin['id'], business_id
                )
            )

            for service_name, price, duration in services:
                c.execute(
                    '''INSERT INTO services
                       (business_id,name,description,price,
                        duration_minutes,category,image_path)
                       VALUES(?,?,?,?,?,?,?)''',
                    (
                        business_id, service_name,
                        'Dịch vụ demo', price,
                        duration, category, banner
                    )
                )

        c.execute(
            'INSERT INTO app_settings(key,value) VALUES(?,?)',
            (marker, 'local-only')
        )

        private_json_write(credentials_path, {
            'notice': 'Local only. Do not commit or share.',
            'users': users
        })

    logging.info('Đã tạo 6 tài khoản demo local.')
    logging.info('Thông tin đăng nhập: %s', credentials_path)
if __name__=='__main__':
    seed()
    seed_local_demo()

    logging.info('ServiceHub running at http://%s:%s', HOST, PORT)

    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
