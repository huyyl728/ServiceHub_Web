PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
 phone TEXT DEFAULT '', address TEXT DEFAULT '', password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
CREATE TABLE IF NOT EXISTS wallets (
 user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, balance INTEGER NOT NULL DEFAULT 0 CHECK(balance >= 0)
);
CREATE TABLE IF NOT EXISTS wallet_transactions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), amount INTEGER NOT NULL,
 kind TEXT NOT NULL, description TEXT NOT NULL, reference TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
CREATE TABLE IF NOT EXISTS payments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
 booking_id INTEGER NOT NULL REFERENCES bookings(id), amount INTEGER NOT NULL, status TEXT NOT NULL,
 provider TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_booking_provider ON payments(booking_id, provider);

CREATE TABLE IF NOT EXISTS wallet_transfers (
 id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL REFERENCES users(id), recipient_id INTEGER NOT NULL REFERENCES users(id),
 amount INTEGER NOT NULL CHECK(amount > 0), request_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'completed',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(sender_id, request_id), CHECK(sender_id <> recipient_id)
);
CREATE INDEX IF NOT EXISTS idx_wallet_transfers_sender ON wallet_transfers(sender_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_wallet_transfers_recipient ON wallet_transfers(recipient_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_actor ON audit_logs(actor_id, created_at DESC);

-- Bank-transfer QR requests: QR generation does not prove that funds arrived.
-- This table is separate from wallet_transactions; confirmation does not credit demo wallets.
CREATE TABLE IF NOT EXISTS bank_qr_requests (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL REFERENCES users(id),
 amount INTEGER NOT NULL CHECK(amount >= 10000 AND amount <= 5000000),
 reference TEXT NOT NULL UNIQUE,
 request_id TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','confirmed','rejected')),
 bank_transaction_ref TEXT UNIQUE,
 reviewed_by INTEGER REFERENCES users(id),
 reviewed_at TEXT,
 admin_note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id, request_id)
);
CREATE INDEX IF NOT EXISTS idx_bank_qr_user ON bank_qr_requests(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bank_qr_status ON bank_qr_requests(status, created_at DESC);

