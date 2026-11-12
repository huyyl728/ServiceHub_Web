"""Explicit fixtures for disposable tests only; never used by server.py startup."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server
from server import hash_password


def seed_demo_data():
    with server.connect() as c:
        if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
            users = [
                ('Admin ServiceHub','admin@servicehub.local','0900000000','Admin@12345',1),
                ('Nguyễn Thành Huy','huy@servicehub.local','0912345678','Huy@12345',0),
                ('Chủ sân mẫu','owner@servicehub.local','0987654321','Owner@12345',0),
            ]
            ids={}
            for name,email,phone,pw,admin in users:
                cur=c.execute('INSERT INTO users(name,email,phone,password_hash,is_admin) VALUES(?,?,?,?,?)',(name,email,phone,hash_password(pw),admin)); ids[email]=cur.lastrowid
            cur=c.execute('INSERT INTO businesses(name,category,address,phone,description,owner_id,status) VALUES(?,?,?,?,?,?,?)',('Huy Football','Sân bóng','Cầu Giấy, Hà Nội','0987654321','Sân bóng mẫu để thử đặt lịch.',ids['owner@servicehub.local'],'active'))
            bid=cur.lastrowid
            samples=[('Sân bóng 5 người','Sân cỏ nhân tạo, đặt theo giờ.',250000,60,'Sân bóng'),('Cắt tóc cơ bản','Dịch vụ cắt tóc nam.',80000,30,'Làm đẹp'),('Chăm sóc da thư giãn','Liệu trình chăm sóc da cơ bản.',300000,60,'Spa'),('Bàn ăn 2 người','Đặt bàn tại nhà hàng đối tác.',0,90,'Nhà hàng')]
            for n,d,p,dur,cat in samples:
                c.execute('INSERT INTO services(business_id,name,description,price,duration_minutes,category) VALUES(?,?,?,?,?,?)',(bid,n,d,p,dur,cat))
            c.execute('INSERT INTO membership_programs(business_id,name,description) VALUES(NULL,?,?,?)'.replace('VALUES(NULL,?,?,?)','VALUES(NULL,?,?)'),('ServiceHub Rewards','Chương trình hội viên nền tảng.'))
            c.execute('INSERT INTO membership_programs(business_id,name,description) VALUES(?,?,?)',(bid,'Huy Football Member','Hội viên riêng của cơ sở Huy Football.'))
            c.commit()
        # Seed a small set of clearly labelled demo businesses on both new and existing databases.
        owner = c.execute('SELECT id FROM users WHERE email=?', ('owner@servicehub.local',)).fetchone()
        if owner:
            demo_businesses = [
                ('Bếp Nhà Mình (Demo)', 'Nhà hàng', 'Ba Đình, Hà Nội', '0901112233', 'Nhà hàng demo với món Việt thân thuộc. Nội dung minh họa cho buổi trình diễn.', '/static/images/demo-restaurant.svg'),
                ('Mộc Hair Studio (Demo)', 'Làm đẹp', 'Đống Đa, Hà Nội', '0902223344', 'Tiệm tóc demo, đặt lịch cắt và tạo kiểu.', '/static/images/demo-salon.svg'),
                ('An Nhiên Spa (Demo)', 'Spa', 'Cầu Giấy, Hà Nội', '0903334455', 'Không gian spa demo để trình diễn luồng khám phá dịch vụ.', '/static/images/demo-spa.svg'),
                ('Sân Pickleball Phố (Demo)', 'Thể thao', 'Thanh Xuân, Hà Nội', '0904445566', 'Sân thể thao demo với lịch đặt theo giờ.', '/static/images/demo-sport.svg'),
                ('Cà phê Góc Phố (Demo)', 'Nhà hàng', 'Tây Hồ, Hà Nội', '0905556677', 'Quán cà phê demo, dữ liệu chỉ dùng để minh họa giao diện.', '/static/images/demo-cafe.svg'),
            ]
            for name, category, address, phone, desc, banner in demo_businesses:
                row = c.execute('SELECT id FROM businesses WHERE name=?', (name,)).fetchone()
                if row:
                    bid = row['id']
                    c.execute("UPDATE businesses SET banner_path=CASE WHEN banner_path IS NULL OR banner_path='' THEN ? ELSE banner_path END WHERE id=?", (banner, bid))
                else:
                    cur = c.execute('INSERT INTO businesses(name,category,address,phone,description,owner_id,status,banner_path) VALUES(?,?,?,?,?,?,?,?)', (name,category,address,phone,desc,owner['id'],'active',banner))
                    bid = cur.lastrowid
                existing = c.execute('SELECT COUNT(*) FROM services WHERE business_id=?', (bid,)).fetchone()[0]
                if existing == 0:
                    examples = {
                        'Nhà hàng': [('Bàn ăn 2 người','Đặt bàn tại quán (demo).',0,90,'Nhà hàng'),('Bữa tối đặc biệt','Thực đơn demo, vui lòng xác nhận trực tiếp.',220000,90,'Nhà hàng')],
                        'Làm đẹp': [('Cắt tóc và tạo kiểu','Dịch vụ demo của Mộc Hair Studio.',120000,45,'Làm đẹp'),('Gội đầu thư giãn','Dịch vụ demo.',80000,30,'Làm đẹp')],
                        'Spa': [('Chăm sóc da cơ bản','Liệu trình demo, không phải tư vấn y tế.',280000,60,'Spa'),('Massage thư giãn','Dịch vụ demo.',350000,60,'Spa')],
                        'Thể thao': [('Thuê sân 60 phút','Giá demo theo khung giờ.',180000,60,'Thể thao'),('Thuê sân 90 phút','Giá demo theo khung giờ.',250000,90,'Thể thao')],
                    }
                    for n,d,price,duration,cat in examples.get(category, []):
                        c.execute('INSERT INTO services(business_id,name,description,price,duration_minutes,category) VALUES(?,?,?,?,?,?)',(bid,n,d,price,duration,cat))
                # Explicitly label a demo cafe offering so discovery does not mistake
                # an ordinary restaurant booking for an actual coffee/drinks service.
                if name == 'Cà phê Góc Phố (Demo)' and not c.execute(
                    'SELECT 1 FROM services WHERE business_id=? AND name=?',
                    (bid, 'Trải nghiệm cà phê (Demo)')).fetchone():
                    c.execute('INSERT INTO services(business_id,name,description,price,duration_minutes,category) VALUES(?,?,?,?,?,?)',
                              (bid, 'Trải nghiệm cà phê (Demo)', 'Đặt chỗ trải nghiệm cà phê minh họa, không phải thực đơn thật.', 45000, 60, 'Đồ uống'))
            c.commit()


def main():
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not server.DB_PATH.is_relative_to(temp_root):
        raise RuntimeError("Test fixtures require a database under the temporary directory.")
    server.ADMIN_EMAIL = ''
    server.ADMIN_PASSWORD = ''
    server.seed()
    seed_demo_data()
    server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler).serve_forever()


if __name__ == "__main__":
    main()
