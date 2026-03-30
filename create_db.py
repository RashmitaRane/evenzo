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

    # 3. SERVICES / PORTFOLIO TABLE
    # 🟢 FIXED: Removed the CHECK constraint on category to allow multiple selections
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            category TEXT,
            service_name TEXT NOT NULL,
            service_location TEXT,       
            services_offered TEXT,       
            experience_years INTEGER,    
            pricing TEXT,                
            images TEXT,                 
            description TEXT,
            FOREIGN KEY (manager_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 4. BOOKINGS TABLE
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    # ==========================================
    # --- SMART UPDATE LOGIC FOR EXISTING DB ---
    # ==========================================
    
    # 🟢 FIXED: Automatically remove the old CHECK constraint if it exists in an older database
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='services'")
    table_sql = cursor.fetchone()
    if table_sql and "CHECK(category IN" in table_sql[0]:
        print("🔧 Removing strict category rules from 'services' table to allow multiple selections...")
        cursor.execute("ALTER TABLE services RENAME TO services_old_temp")
        
        cursor.execute('''
            CREATE TABLE services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_id INTEGER NOT NULL,
                category TEXT,
                service_name TEXT NOT NULL,
                service_location TEXT,       
                services_offered TEXT,       
                experience_years INTEGER,    
                pricing TEXT,                
                images TEXT,                 
                description TEXT,
                FOREIGN KEY (manager_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Safely copy old data into the new table
        cursor.execute('''
            INSERT INTO services (id, manager_id, category, service_name, service_location, services_offered, experience_years, pricing, images, description)
            SELECT id, manager_id, category, service_name, service_location, services_offered, experience_years, pricing, images, description FROM services_old_temp
        ''')
        cursor.execute("DROP TABLE services_old_temp")
        print("✅ Strict category rules successfully removed!")

    # Check and upgrade manager_profiles table
    try:
        cursor.execute("ALTER TABLE manager_profiles ADD COLUMN profile_pic TEXT")
        print("🔧 Upgraded 'manager_profiles' table.")
    except sqlite3.OperationalError:
        pass # Column already exists

    # Check and upgrade services table for missing columns
    new_service_columns = [
        "service_location TEXT",
        "services_offered TEXT",
        "experience_years INTEGER",
        "pricing TEXT",
        "images TEXT"
    ]
    
    print("Checking services table for missing columns...")
    for column in new_service_columns:
        try:
            cursor.execute(f"ALTER TABLE services ADD COLUMN {column}")
            print(f"🔧 Added missing column: {column.split()[0]}")
        except sqlite3.OperationalError:
            pass # Column already exists

    conn.commit()
    conn.close()
    print("✅ Database is ready and fully up-to-date!")

if __name__ == "__main__":
    initialize_evenzo_database()