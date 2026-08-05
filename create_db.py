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
            is_active INTEGER DEFAULT 1,
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
            location TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 3. SERVICES / PORTFOLIO TABLE
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
            unavailable_dates TEXT,
            package_tier TEXT DEFAULT 'Standard',
            pkg_basic_name TEXT DEFAULT 'Basic (Silver)',
            pkg_basic_price REAL DEFAULT 0.0,
            pkg_basic_desc TEXT,
            pkg_premium_name TEXT DEFAULT 'Premium (Gold)',
            pkg_premium_price REAL DEFAULT 0.0,
            pkg_premium_desc TEXT,
            pkg_luxury_name TEXT DEFAULT 'Luxury (Platinum)',
            pkg_luxury_price REAL DEFAULT 0.0,
            pkg_luxury_desc TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
            event_location TEXT,
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'unpaid',
            client_phone TEXT,
            client_message TEXT,
            selected_package TEXT,
            cancelled_by TEXT,
            cancel_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    ''')

    # 5. REVIEWS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            manager_id INTEGER NOT NULL,
            booking_id INTEGER,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            review_text TEXT,
            is_visible INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (manager_id) REFERENCES users (id),
            FOREIGN KEY (booking_id) REFERENCES bookings (id)
        )
    ''')

    # 6. COMPLAINTS TABLE (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            booking_id INTEGER,
            manager_id INTEGER,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES users (id),
            FOREIGN KEY (booking_id) REFERENCES bookings (id),
            FOREIGN KEY (manager_id) REFERENCES users (id)
        )
    ''')

    # 7. NOTIFICATIONS TABLE (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            notif_type TEXT DEFAULT 'info',
            link TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')

    # 8. CATEGORIES TABLE (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            icon TEXT DEFAULT 'fas fa-star',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 9. OTP TABLE for password reset (NEW)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            otp TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 10. CHATBOT CUSTOM QUESTIONS TABLE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chatbot_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT 'General',
            keywords TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ─── SAFE MIGRATIONS (Add missing columns to existing tables) ─────────────
    migrations = [
        ("users",            "is_active INTEGER DEFAULT 1"),
        ("manager_profiles", "location TEXT"),
        ("services",         "package_tier TEXT DEFAULT 'Standard'"),
        ("services",         "is_active INTEGER DEFAULT 1"),
        ("services",         "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("services",         "pkg_basic_name TEXT DEFAULT 'Basic (Silver)'"),
        ("services",         "pkg_basic_price REAL DEFAULT 0.0"),
        ("services",         "pkg_basic_desc TEXT"),
        ("services",         "pkg_premium_name TEXT DEFAULT 'Premium (Gold)'"),
        ("services",         "pkg_premium_price REAL DEFAULT 0.0"),
        ("services",         "pkg_premium_desc TEXT"),
        ("services",         "pkg_luxury_name TEXT DEFAULT 'Luxury (Platinum)'"),
        ("services",         "pkg_luxury_price REAL DEFAULT 0.0"),
        ("services",         "pkg_luxury_desc TEXT"),
        ("bookings",         "selected_package TEXT"),
        ("bookings",         "event_location TEXT"),
        ("bookings",         "cancelled_by TEXT"),
        ("bookings",         "cancel_reason TEXT"),
        ("reviews",          "booking_id INTEGER"),
        ("reviews",          "is_visible INTEGER DEFAULT 1"),
    ]

    print("Running safe migrations...")
    for table, column_def in migrations:
        col_name = column_def.split()[0]
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
            print(f"  + Added '{col_name}' to '{table}'")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # ─── SEED DEFAULT CATEGORIES ──────────────────────────────────────────────
    default_categories = [
        ("Wedding",          "Full wedding planning and execution",       "fas fa-ring"),
        ("Birthday",         "Birthday party planning and decoration",    "fas fa-birthday-cake"),
        ("Corporate Events", "Professional corporate event management",   "fas fa-briefcase"),
        ("Photography",      "Event photography and videography",         "fas fa-camera"),
        ("Catering",         "Food and beverage services",                "fas fa-utensils"),
        ("Decoration",       "Event decoration and floral arrangements",  "fas fa-palette"),
        ("Music/DJ",         "Live music, DJs and entertainment",         "fas fa-music"),
        ("Makeup/Beauty",    "Bridal and event makeup services",          "fas fa-magic"),
        ("Venue",            "Venue booking and management",              "fas fa-building"),
        ("Mehendi",          "Mehendi and henna artists",                 "fas fa-hand-sparkles"),
        ("Entertainment",    "Entertainment and performers",              "fas fa-theater-masks"),
        ("Event Planning",   "Full event planning coordination",          "fas fa-clipboard-list"),
        ("Florists",         "Floral design and decoration",              "fas fa-flower"),
        ("Transportation",   "Event transportation and logistics",        "fas fa-car"),
        ("Personal Events",  "Birthdays, anniversaries, baby showers",   "fas fa-heart"),
        ("Public Events",    "Concerts, fests and public gatherings",     "fas fa-users"),
    ]
    for name, desc, icon in default_categories:
        try:
            cursor.execute(
                "INSERT INTO categories (name, description, icon) VALUES (?, ?, ?)",
                (name, desc, icon)
            )
        except sqlite3.IntegrityError:
            pass  # Already exists

    # ─── SEED DEFAULT CHATBOT QUESTIONS ───────────────────────────────────────
    default_questions = [
        (
            "What is Evenzo?",
            "Evenzo is an all-in-one premium event management platform connecting clients with top-rated event managers for weddings, corporate events, parties, photography, catering, and more!",
            "General",
            "evenzo, about, platform, what is"
        ),
        (
            "How do I book an event manager or vendor?",
            "Browse our Explore or Service pages, select your desired vendor, choose your event date & location, select a package (Basic, Premium, or Luxury), enter your contact details, and click 'Book Vendor'. Once approved by the manager, you can complete the payment!",
            "Booking",
            "book, booking, reserve, hire vendor, manager"
        ),
        (
            "How can I register as an Event Manager?",
            "Click on 'Login/Register' on the homepage, select the 'Event Manager' role option, fill in your full name, email, business name, phone number, and upload your business license for admin verification!",
            "Account",
            "register vendor, manager registration, business account, seller"
        ),
        (
            "How do I reset my password if forgotten?",
            "Click on 'Login', click the 'Forgot Password?' link, enter your registered email address to receive a 6-digit OTP code, then enter the OTP to reset your password instantly!",
            "Account",
            "forgot password, reset password, otp, password recovery"
        ),
        (
            "Can I customize event package tiers?",
            "Yes! Vendors offer Basic (Silver), Premium (Gold), and Luxury (Platinum) package tiers. You can also specify custom requirements in the message box when sending a booking request.",
            "Pricing",
            "package, customization, silver, gold, platinum, custom plan, pricing"
        ),
        (
            "How do payments work on Evenzo?",
            "After your booking request is confirmed by the Event Manager, a 'Pay Now' button will appear in your User Dashboard. You can pay securely using our mock payment gateway.",
            "Payment",
            "payment, pay, checkout, money, billing, mock payment"
        ),
        (
            "How do I leave a review or rating for a vendor?",
            "Once your booking is marked as confirmed and paid, navigate to the Vendor Details page to leave a star rating (1 to 5) along with a detailed review of your experience!",
            "Reviews",
            "review, rating, feedback, star, comment"
        ),
        (
            "What should I do if I have a complaint?",
            "You can submit an official complaint directly from your User Dashboard in the 'Complaints' tab. Our admin team will investigate and respond promptly.",
            "Support",
            "complaint, issue, problem, dispute, support, report"
        ),
        (
            "What event categories are available?",
            "Evenzo supports a wide range of event categories including Wedding Events, Personal & Birthday Parties, Corporate Events, Public Fests, Photography, Catering, Mehendi, Makeup & Beauty, and Venue Rentals!",
            "General",
            "categories, services, types of events, wedding, birthday, corporate"
        )
    ]

    for q, a, cat, kw in default_questions:
        cursor.execute("SELECT COUNT(*) FROM chatbot_questions WHERE question=?", (q,))
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO chatbot_questions (question, answer, category, keywords) VALUES (?, ?, ?, ?)",
                (q, a, cat, kw)
            )

    conn.commit()
    conn.close()
    print("✅ Database fully initialised with all tables and seed data!")

if __name__ == "__main__":
    initialize_evenzo_database()
