PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 phone TEXT DEFAULT '', address TEXT DEFAULT '', password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0,
 login_enabled INTEGER NOT NULL DEFAULT 1 CHECK(login_enabled IN (0,1)),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_settings (
 key TEXT PRIMARY KEY, value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS businesses (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL,
 address TEXT NOT NULL, phone TEXT NOT NULL, description TEXT DEFAULT '', owner_id INTEGER NOT NULL REFERENCES users(id),
 status TEXT NOT NULL DEFAULT 'active', banner_path TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS business_applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), business_name TEXT NOT NULL,
 category TEXT NOT NULL, address TEXT NOT NULL, phone TEXT NOT NULL, description TEXT DEFAULT '',
 status TEXT NOT NULL DEFAULT 'pending', review_note TEXT DEFAULT '', reviewed_by INTEGER REFERENCES users(id),
 business_id INTEGER REFERENCES businesses(id), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS services (
 id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
 name TEXT NOT NULL, description TEXT DEFAULT '', price INTEGER NOT NULL CHECK(price >= 0), duration_minutes INTEGER NOT NULL DEFAULT 60,
 category TEXT NOT NULL, image_path TEXT DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS bookings (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), service_id INTEGER NOT NULL REFERENCES services(id),
 business_id INTEGER NOT NULL REFERENCES businesses(id), booking_date TEXT NOT NULL, start_time TEXT NOT NULL,
 end_time TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', price INTEGER NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS membership_programs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER REFERENCES businesses(id) ON DELETE CASCADE,
 name TEXT NOT NULL, description TEXT DEFAULT '', points_per_currency INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1, benefits TEXT NOT NULL DEFAULT '', auto_approve_bookings INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_memberships (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), program_id INTEGER NOT NULL REFERENCES membership_programs(id),
 points INTEGER NOT NULL DEFAULT 0, joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, program_id)
);
CREATE TABLE IF NOT EXISTS notifications (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL,
 message TEXT NOT NULL, is_read INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL,
 entity_type TEXT NOT NULL DEFAULT '', entity_id TEXT DEFAULT '', details TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_services_business ON services(business_id, active);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id, booking_date, start_time);
CREATE INDEX IF NOT EXISTS idx_bookings_business ON bookings(business_id, booking_date, start_time);
CREATE INDEX IF NOT EXISTS idx_applications_user ON business_applications(user_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_id, created_at DESC);
