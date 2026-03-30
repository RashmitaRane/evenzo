import sqlite3
import os

def initialize_evenzo_database():
    # Define the database name
    db_name = 'database.db'
    
    # Connect to SQLite (this creates the file if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    print(f"Creating {db_name}...")

    # 1. USERS TABLE
    # Stores basic login info for Users, Admins, and Event Managers
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('user', 'admin', 'eventmanager')) NOT NULL,
            is_approved INTEGER DEFAULT 0, -- 0=Pending, 1=Approved by Admin
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. EVENT MANAGER PROFILES
    # Handles "Service Provider Profile Management"
    # Stores business name, phone, and the license file path for authenticity
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS manager_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            license_path TEXT, -- Path to uploaded JPEG/PDF license
            bio TEXT,
            base_price REAL DEFAULT 0.0,
            rating REAL DEFAULT 0.0, -- For the "Ratings/Reviews system"
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 3. SERVICES TABLE
    # Maps managers to the categories in your HTML (Wedding, Corporate, etc.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manager_id INTEGER NOT NULL,
            category TEXT CHECK(category IN ('Wedding', 'Personal', 'Corporate', 'Public')),
            service_name TEXT NOT NULL, -- e.g., "Sangeet", "Product Launch"
            description TEXT,
            FOREIGN KEY (manager_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 4. BOOKINGS TABLE
    # Supports "Booking, Payment & Scheduling" functional requirements
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            service_id INTEGER,
            event_date DATE NOT NULL,
            status TEXT DEFAULT 'pending', -- pending, confirmed, rejected
            total_amount REAL,
            payment_status TEXT DEFAULT 'unpaid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    # Optional: Insert a default Admin account for testing
    # Password should be hashed in your real app (e.g., using werkzeug.security)
    try:
        cursor.execute("INSERT INTO users (full_name, email, password, role, is_approved) VALUES (?, ?, ?, ?, ?)",
                       ('System Admin', 'admin@evenzo.com', 'admin123', 'admin', 1))
    except sqlite3.IntegrityError:
        pass # Admin already exists

    conn.commit()
    conn.close()
    print("✅ Database file 'database.db' has been created successfully!")

if __name__ == "__main__":
    initialize_evenzo_database()