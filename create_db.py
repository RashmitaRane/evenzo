import sqlite3

def initialize_evenzo_database():
    db_name = 'database.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(f"Initializing {db_name}...")

    # 1. USERS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('user', 'admin', 'eventmanager')) NOT NULL,
            is_approved INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. EVENT MANAGER PROFILES
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manager_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            license_path TEXT,
            profile_pic TEXT, 
            bio TEXT,
            base_price REAL DEFAULT 0.0,
            rating REAL DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 3. SERVICES / PORTFOLIO TABLE (Updated for 3 Packages)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            category TEXT,
            service_name TEXT NOT NULL,
            service_location TEXT,       
            services_offered TEXT,       
            experience_years INTEGER,    
            pricing TEXT,  -- We will keep this as the "Starting At" price              
            images TEXT,                 
            description TEXT,
            unavailable_dates TEXT,
            pkg_basic_name TEXT DEFAULT 'Basic (Silver)',
            pkg_basic_price REAL DEFAULT 0.0,
            pkg_basic_desc TEXT,
            pkg_premium_name TEXT DEFAULT 'Premium (Gold)',
            pkg_premium_price REAL DEFAULT 0.0,
            pkg_premium_desc TEXT,
            pkg_luxury_name TEXT DEFAULT 'Luxury (Platinum)',
            pkg_luxury_price REAL DEFAULT 0.0,
            pkg_luxury_desc TEXT,
            FOREIGN KEY (manager_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 4. BOOKINGS TABLE (Updated to store selected package)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            service_id INTEGER,
            event_date DATE NOT NULL,
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'unpaid',
            client_phone TEXT,
            client_message TEXT,
            selected_package TEXT, -- 🟢 NEW: Stores which tier they chose
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    # 5. REVIEWS TABLE (🟢 NEWLY ADDED)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id)
        )
    ''')

    # --- SMART UPDATE LOGIC (Safely adds new columns to existing DB) ---
    new_service_columns = [
        "pkg_basic_name TEXT DEFAULT 'Basic (Silver)'",
        "pkg_basic_price REAL DEFAULT 0.0",
        "pkg_basic_desc TEXT",
        "pkg_premium_name TEXT DEFAULT 'Premium (Gold)'",
        "pkg_premium_price REAL DEFAULT 0.0",
        "pkg_premium_desc TEXT",
        "pkg_luxury_name TEXT DEFAULT 'Luxury (Platinum)'",
        "pkg_luxury_price REAL DEFAULT 0.0",
        "pkg_luxury_desc TEXT"
    ]
    
    print("Checking services table for package columns...")
    for column in new_service_columns:
        try:
            cursor.execute(f"ALTER TABLE services ADD COLUMN {column}")
            print(f"🔧 Added column: {column.split()[0]}")
        except sqlite3.OperationalError:
            pass

    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN selected_package TEXT")
        print("🔧 Added 'selected_package' to bookings.")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("✅ Database is ready with Review and Tiered Package systems!")

if __name__ == "__main__":
    initialize_evenzo_database()