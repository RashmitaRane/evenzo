import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    
    # Enable foreign keys
    conn.execute('PRAGMA foreign_keys = ON')

    # USERS TABLE (Role can be 'admin', 'eventmanager', 'user')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            is_approved INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # MANAGER PROFILES (Extended details for Event Managers)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS manager_profiles (
            user_id INTEGER PRIMARY KEY,
            business_name TEXT NOT NULL,
            phone TEXT,
            license_path TEXT,
            profile_pic TEXT,
            description TEXT,
            rating REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # SERVICES TABLE (Different services offered by Event Managers)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            service_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            pricing REAL NOT NULL,
            images TEXT, -- comma-separated filenames
            service_location TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (manager_id) REFERENCES users (id)
        )
    ''')

    # BOOKINGS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            service_id INTEGER,
            event_date DATE NOT NULL,
            event_location TEXT,
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'unpaid',
            client_phone TEXT,
            client_message TEXT,
            selected_package TEXT,
            cancelled_by TEXT,
            cancel_reason TEXT,
            transaction_id TEXT,
            receipt_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    booking_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(bookings)")
    }
    for column in ('transaction_id', 'receipt_number'):
        if column not in booking_columns:
            conn.execute(f"ALTER TABLE bookings ADD COLUMN {column} TEXT")

    # COMPLAINTS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER,
            booking_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')

    # REVIEWS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            booking_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT,
            is_visible INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')

    # NOTIFICATIONS TABLE
    conn.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notif_type TEXT DEFAULT 'info', -- success, info, warning, danger
            is_read INTEGER DEFAULT 0,
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # CATEGORIES DIRECTORY (For Explore Page & Filters)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # INSERT DEFAULT CATEGORIES
    default_cats = [
        ('Wedding Events', 'Complete wedding planning, decorators, and caterers.', 'fas fa-rings'),
        ('Personal & Birthday Parties', 'Birthday bashes, baby showers, and personal celebrations.', 'fas fa-birthday-cake'),
        ('Corporate Events', 'Seminars, conferences, and team-building events.', 'fas fa-briefcase'),
        ('Public Fests', 'Concerts, college fests, and public gatherings.', 'fas fa-music'),
        ('Photography', 'Pre-wedding, event coverage, and portfolio shoots.', 'fas fa-camera'),
        ('Catering', 'Buffets, custom menus, and food stalls.', 'fas fa-utensils'),
        ('Mehendi', 'Bridal and guest mehendi services.', 'fas fa-leaf'),
        ('Makeup & Beauty', 'Bridal makeup and party makeovers.', 'fas fa-magic'),
        ('Venue Rentals', 'Banquet halls, open grounds, and resort bookings.', 'fas fa-map-marker-alt')
    ]
    for c in default_cats:
        try:
            conn.execute("INSERT INTO categories (name, description, icon) VALUES (?,?,?)", c)
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()