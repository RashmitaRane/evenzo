from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import sqlite3
import os
import random
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── CONFIG ───────────────────────────────────────────────────────────────────
EMAIL_SENDER       = "shelicoa26@gmail.com"
EMAIL_APP_PASSWORD = "ywlg kisi dkwj rjhi"

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'avif'}
MAX_UPLOAD_MB      = 10

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
app.secret_key = os.environ.get('EVENZO_SECRET', 'evenzo_secret_key_2025_upgrade')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ─── DB HELPER ────────────────────────────────────────────────────────────────
def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── CHATBOT DB INITIALIZER ───────────────────────────────────────────────────
def init_chatbot_db():
    try:
        conn = get_db_connection()
        conn.execute('''
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
            count = conn.execute("SELECT COUNT(*) FROM chatbot_questions WHERE question=?", (q,)).fetchone()[0]
            if count == 0:
                conn.execute(
                    "INSERT INTO chatbot_questions (question, answer, category, keywords) VALUES (?, ?, ?, ?)",
                    (q, a, cat, kw)
                )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Chatbot DB init error:", e)

init_chatbot_db()

# ─── GEMINI AI HELPER ─────────────────────────────────────────────────────────
import urllib.request
import json

def call_gemini_ai(user_prompt):
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        system_instruction = "You are Evenzo's friendly AI Concierge for an event planning platform. Answer concisely in 2-4 sentences using simple HTML tags like <b> and <br>."
        payload = {
            "contents": [{"parts": [{"text": f"{system_instruction}\nUser Question: {user_prompt}"}]}]
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            text = res_data['candidates'][0]['content']['parts'][0]['text']
            return text.replace('\n', '<br>')
    except Exception as e:
        print("Gemini API call exception:", e)
        return None

# ─── NOTIFICATION HELPER ──────────────────────────────────────────────────────
def add_notification(user_id, title, message, notif_type='info', link=None):
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO notifications (user_id, title, message, notif_type, link) VALUES (?,?,?,?,?)",
            (user_id, title, message, notif_type, link)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Notification error:", e)

def get_unread_count(user_id):
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0", (user_id,)
    ).fetchone()[0]
    conn.close()
    return count

# ─── EMAIL HELPERS ────────────────────────────────────────────────────────────
def _send_email(to_addr, subject, html_body):
    try:
        msg = MIMEMultipart()
        msg['From']    = f"Evenzo <{EMAIL_SENDER}>"
        msg['To']      = to_addr
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))
        srv = smtplib.SMTP('smtp.gmail.com', 587)
        srv.starttls()
        srv.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        srv.send_message(msg)
        srv.quit()
    except Exception as e:
        print("Email error:", e)

def send_booking_email(manager_email, manager_name, client_name, client_email,
                       client_phone, event_dates, service_name, message, package_tier):
    subject = f"New Booking Request: {service_name} by {client_name}"
    body = f"""<html><body style="font-family:Segoe UI,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px;">
    <h1 style="color:#953553;">Evenzo</h1>
    <p>Hello <b>{manager_name}</b>, you have a new booking request!</p>
    <div style="background:#fdf5f7;padding:20px;border-left:5px solid #953553;border-radius:8px;margin:20px 0;">
        <p><b>Client:</b> {client_name}</p><p><b>Email:</b> {client_email}</p>
        <p><b>Phone:</b> +91 {client_phone}</p><p><b>Date(s):</b> {event_dates}</p>
        <p><b>Service:</b> {service_name}</p><p><b>Package:</b> {package_tier}</p>
        <p><b>Message:</b> <i>"{message}"</i></p>
    </div>
    <p>Log in to your dashboard to accept or reject this request.</p>
    </body></html>"""
    _send_email(manager_email, subject, body)

def send_status_email(client_email, client_name, manager_name, service_name, event_dates, status):
    color  = "#2e7d32" if status == 'confirmed' else "#d32f2f"
    emoji  = "🎉" if status == 'confirmed' else "📝"
    text   = (f"Your booking for <b>{event_dates}</b> has been confirmed by {manager_name}."
              if status == 'confirmed' else
              f"{manager_name} declined your booking request for <b>{event_dates}</b>.")
    subject = f"Booking {status.capitalize()}: {service_name}"
    body = f"""<html><body style="font-family:Segoe UI,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px;">
    <h1 style="color:#953553;">Evenzo</h1><h2 style="color:{color};">{emoji} Booking {status.capitalize()}</h2>
    <p>Hello <b>{client_name}</b>,</p><p>{text}</p>
    <p><b>Service:</b> {service_name}<br><b>Status:</b> <span style="color:{color};font-weight:bold;text-transform:uppercase;">{status}</span></p>
    </body></html>"""
    _send_email(client_email, subject, body)

def send_manager_approval_email(manager_email, manager_name):
    subject = "Your Evenzo Account is Approved!"
    body = f"""<html><body style="font-family:Segoe UI,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px;">
    <h1 style="color:#953553;">Evenzo</h1><h2 style="color:#2e7d32;">Account Approved! 🎉</h2>
    <p>Hello <b>{manager_name}</b>,</p>
    <p>Your Event Handler registration has been <b>approved</b>. You can now log in and start receiving bookings.</p>
    <div style="text-align:center;margin-top:30px;">
    <a href="http://127.0.0.1:5000/" style="background:#953553;color:white;padding:12px 25px;text-decoration:none;border-radius:6px;font-weight:bold;">Log In Now</a>
    </div></body></html>"""
    _send_email(manager_email, subject, body)


# ─── STATIC PAGES ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/weddingservices')
def weddingservices():
    return render_template('weddingservices.html')

@app.route('/specialservices')
def specialservices():
    return render_template('Specialservices.html')

@app.route('/corporateservices')
def corporateservices():
    return render_template('Corporateservices.html')

@app.route('/publicservices')
def publicservices():
    return render_template('publicservices.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ─── AUTH: REGISTER ───────────────────────────────────────────────────────────
@app.route('/register', methods=['POST'])
def register():
    role       = request.form.get('regUserRole', 'user')
    full_name  = request.form.get('regFullName', '').strip()
    email      = request.form.get('regEmail', '').strip().lower()
    password   = request.form.get('regPass', '')

    if not full_name or not email or not password:
        flash("All fields are required.")
        return redirect(url_for('index'))

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (full_name, email, password, role, is_approved) VALUES (?,?,?,?,?)",
            (full_name, email, hashed_pw, role, 1 if role == 'user' else 0)
        )
        user_id = cur.lastrowid

        if role == 'eventmanager':
            biz_name = request.form.get('regBusinessName', '').strip()
            phone    = request.form.get('regPhone', '').strip()
            file     = request.files.get('regLicense')
            filename = ""
            if file and file.filename:
                ext = file.filename.rsplit('.', 1)[-1].lower()
                if ext in {'pdf', 'jpg', 'jpeg', 'png'}:
                    filename = secure_filename(f"{user_id}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur.execute(
                "INSERT INTO manager_profiles (user_id, business_name, phone, license_path) VALUES (?,?,?,?)",
                (user_id, biz_name, phone, filename)
            )
            # Notify admin
            admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
            if admin:
                add_notification(admin['id'], "New Vendor Registration",
                    f"{biz_name} ({full_name}) has applied to become an event manager.",
                    'info', url_for('admin_dashboard'))

        conn.commit()
        if role == 'eventmanager':
            flash("Registration successful! Awaiting admin approval.")
        else:
            flash("Registration successful! Please login.")
    except sqlite3.IntegrityError:
        flash("This email is already registered.")
    finally:
        conn.close()
    return redirect(url_for('index'))


# ─── AUTH: LOGIN ──────────────────────────────────────────────────────────────
@app.route('/login', methods=['POST'])
def login():
    email          = request.form.get('email', '').strip().lower()
    password       = request.form.get('password', '')
    role_requested = request.form.get('userRole', 'user')

    conn = get_db_connection()

    # Hard-coded admin shortcut (backward compatible)
    if email == "shelicoa26@gmail.com" and password == "shelico_evenzo":
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if not user:
            pw = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (full_name,email,password,role,is_approved) VALUES (?,?,?,?,?)",
                ("System Admin", email, pw, "admin", 1)
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    else:
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND role=?", (email, role_requested)
        ).fetchone()

    conn.close()

    if not user:
        flash("Invalid credentials or role.")
        return redirect(url_for('index'))

    # Check password (support both hashed and legacy plain-text)
    pwd_ok = False
    stored = user['password']
    if stored.startswith('pbkdf2:') or stored.startswith('scrypt:'):
        pwd_ok = check_password_hash(stored, password)
    else:
        pwd_ok = (stored == password)  # legacy plain-text

    if not pwd_ok and not (email == "shelicoa26@gmail.com" and password == "shelico_evenzo"):
        flash("Invalid credentials or role.")
        return redirect(url_for('index'))

    if user['role'] == 'eventmanager' and user['is_approved'] == 0:
        flash("Your account is pending admin approval.")
        return redirect(url_for('index'))

    if user['is_active'] == 0 if 'is_active' in user.keys() else False:
        flash("Your account has been deactivated. Contact support.")
        return redirect(url_for('index'))

    session.permanent = True
    session['user_id']   = user['id']
    session['user_name'] = user['full_name']
    session['role']      = user['role']

    if user['role'] == 'admin':        return redirect(url_for('admin_dashboard'))
    elif user['role'] == 'eventmanager': return redirect(url_for('dashboard'))
    else:                               return redirect(url_for('user_dashboard'))

# ─── AUTH: LOGOUT ─────────────────────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── OTP / PASSWORD RESET ─────────────────────────────────────────────────────
@app.route('/send_otp', methods=['POST'])
def send_otp():
    email = request.form.get('email', '').strip().lower()
    conn  = get_db_connection()
    user  = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'Email not found.'})
    otp = str(random.randint(100000, 999999))
    conn.execute("DELETE FROM otp_store WHERE email=?", (email,))
    conn.execute("INSERT INTO otp_store (email, otp) VALUES (?,?)", (email, otp))
    conn.commit()
    conn.close()
    subject = "Your Evenzo OTP"
    body    = f"<p>Your OTP is <b>{otp}</b>. It expires in 10 minutes.</p>"
    _send_email(email, subject, body)
    return jsonify({'success': True, 'message': 'OTP sent to your email.'})

@app.route('/reset_password', methods=['POST'])
def reset_password():
    email    = request.form.get('email', '').strip().lower()
    otp      = request.form.get('otp', '').strip()
    new_pass = request.form.get('new_password', '')
    conn     = get_db_connection()
    record   = conn.execute(
        "SELECT * FROM otp_store WHERE email=? AND otp=?", (email, otp)
    ).fetchone()
    if not record:
        conn.close()
        return jsonify({'success': False, 'message': 'Invalid or expired OTP.'})
    hashed = generate_password_hash(new_pass)
    conn.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
    conn.execute("DELETE FROM otp_store WHERE email=?", (email,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Password reset successfully!'})


# ═══════════════════════════════════════════════════════════════════════════════
# USER MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    conn = get_db_connection()
    user_info = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    my_bookings = conn.execute('''
        SELECT b.*, m.business_name, s.service_name, s.pricing, s.images
        FROM bookings b
        JOIN manager_profiles m ON b.manager_id = m.user_id
        LEFT JOIN services s ON b.service_id = s.id
        WHERE b.client_id=? ORDER BY b.created_at DESC
    ''', (session['user_id'],)).fetchall()

    total   = len(my_bookings)
    pending = sum(1 for b in my_bookings if b['status'] == 'pending')
    confirmed = sum(1 for b in my_bookings if b['status'] == 'confirmed')
    completed = sum(1 for b in my_bookings if b['status'] == 'completed')
    cancelled = sum(1 for b in my_bookings if b['status'] in ('cancelled', 'rejected'))

    complaints = conn.execute('''
        SELECT c.*, m.business_name
        FROM complaints c
        LEFT JOIN manager_profiles m ON c.manager_id = m.user_id
        WHERE c.client_id=? ORDER BY c.created_at DESC
    ''', (session['user_id'],)).fetchall()

    reviews = conn.execute('''
        SELECT r.*, s.service_name, m.business_name
        FROM reviews r
        LEFT JOIN services s ON r.booking_id IN (SELECT id FROM bookings WHERE service_id=s.id)
        LEFT JOIN manager_profiles m ON r.manager_id = m.user_id
        WHERE r.client_id=? ORDER BY r.created_at DESC
    ''', (session['user_id'],)).fetchall()

    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (session['user_id'],)
    ).fetchall()
    unread_count = sum(1 for n in notifs if not n['is_read'])

    all_services = conn.execute('''
        SELECT s.*, m.business_name, m.profile_pic, m.rating
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON s.manager_id = u.id
        WHERE u.is_approved=1 AND u.is_active=1 AND s.is_active=1
        ORDER BY m.rating DESC
    ''').fetchall()

    conn.close()
    return render_template('user_dashboard.html',
        user=user_info, bookings=my_bookings, services=all_services,
        total=total, pending=pending, confirmed=confirmed,
        completed=completed, cancelled=cancelled,
        complaints=complaints, reviews=reviews,
        notifications=notifs, unread_count=unread_count)

@app.route('/user/edit_profile', methods=['GET', 'POST'])
def user_edit_profile():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        conn.execute("UPDATE users SET full_name=? WHERE id=?", (full_name, session['user_id']))
        conn.commit()
        session['user_name'] = full_name
        flash("Profile updated!")
        conn.close()
        return redirect(url_for('user_edit_profile'))
    user_info = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('user_edit_profile.html', user=user_info)


# ─── EXPLORE / VENDOR DISCOVERY ───────────────────────────────────────────────
@app.route('/explore')
def explore():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    conn = get_db_connection()

    search   = request.args.get('q', '')
    category = request.args.get('category', '')
    service  = request.args.get('service', '')
    location = request.args.get('location', '')
    sort_by  = request.args.get('sort', 'rating')

    query = '''
        SELECT s.*, m.business_name, m.profile_pic, m.rating
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON s.manager_id = u.id
        WHERE u.is_approved=1 AND u.is_active=1 AND s.is_active=1
    '''
    params = []
    if search:
        query += " AND (s.service_name LIKE ? OR m.business_name LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if category:
        query += " AND s.category LIKE ?"
        params.append(f'%{category}%')
    if service:
        query += " AND s.services_offered LIKE ?"
        params.append(f'%{service}%')
    if location:
        query += " AND s.service_location LIKE ?"
        params.append(f'%{location}%')

    order_map = {
        'rating':    'm.rating DESC',
        'price_asc': 'CAST(s.pricing AS REAL) ASC',
        'price_desc':'CAST(s.pricing AS REAL) DESC',
        'newest':    's.id DESC',
        'name':      's.service_name ASC',
    }
    query += f" ORDER BY {order_map.get(sort_by, 'm.rating DESC')}"

    all_services = conn.execute(query, params).fetchall()
    my_bookings  = conn.execute(
        "SELECT b.*, m.business_name FROM bookings b JOIN manager_profiles m ON b.manager_id=m.user_id WHERE b.client_id=?",
        (session['user_id'],)
    ).fetchall()
    categories = conn.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY name").fetchall()
    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? AND is_read=0 ORDER BY created_at DESC LIMIT 10",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('explore.html',
        services=all_services, bookings=my_bookings,
        categories=categories, notifications=notifs,
        search=search, category=category, service=service,
        location=location, sort_by=sort_by)

@app.route('/vendor_details/<int:service_id>')
def vendor_details(service_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    service = conn.execute('''
        SELECT s.*, m.business_name, m.rating, m.phone, m.bio,
               u.full_name as manager_name
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON m.user_id = u.id
        WHERE s.id=?
    ''', (service_id,)).fetchone()
    if not service:
        flash("Vendor not found.")
        return redirect(url_for('explore'))

    reviews = conn.execute('''
        SELECT r.*, u.full_name as client_name
        FROM reviews r JOIN users u ON r.client_id = u.id
        WHERE r.manager_id=? AND r.is_visible=1
        ORDER BY r.created_at DESC
    ''', (service['manager_id'],)).fetchall()

    paid_booking = conn.execute('''
        SELECT id FROM bookings
        WHERE client_id=? AND service_id=? AND status='confirmed' AND payment_status='paid'
        LIMIT 1
    ''', (session['user_id'], service_id)).fetchone()
    can_review = paid_booking is not None

    already_reviewed = conn.execute(
        "SELECT id FROM reviews WHERE client_id=? AND manager_id=?",
        (session['user_id'], service['manager_id'])
    ).fetchone()

    conn.close()
    return render_template('vendors_details.html',
        service=service, reviews=reviews,
        can_review=can_review and not already_reviewed)


# ─── BOOKING ──────────────────────────────────────────────────────────────────
@app.route('/book_vendor', methods=['POST'])
def book_vendor():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    manager_id     = request.form.get('manager_id')
    service_id     = request.form.get('service_id')
    event_date     = request.form.get('event_date')
    event_location = request.form.get('event_location', '')
    client_phone   = request.form.get('client_phone')
    client_message = request.form.get('client_message', '')
    notify_email   = request.form.get('notify_email')
    total_amount   = request.form.get('total_amount', 0)
    sel_package    = request.form.get('selected_package', '')

    if not event_date or not client_phone:
        flash("Please fill all required fields.")
        return redirect(url_for('vendor_details', service_id=service_id))

    conn = get_db_connection()

    # Check availability
    svc = conn.execute("SELECT * FROM services WHERE id=?", (service_id,)).fetchone()
    if svc and svc['unavailable_dates']:
        booked = [d.strip() for d in svc['unavailable_dates'].split(',')]
        requested = [d.strip() for d in event_date.split(',')]
        conflicts = [d for d in requested if d in booked]
        if conflicts:
            conn.close()
            flash(f"Vendor is unavailable on: {', '.join(conflicts)}. Please choose different dates.")
            return redirect(url_for('vendor_details', service_id=service_id))

    # Prevent duplicate pending booking
    dup = conn.execute(
        "SELECT id FROM bookings WHERE client_id=? AND service_id=? AND status='pending'",
        (session['user_id'], service_id)
    ).fetchone()
    if dup:
        conn.close()
        flash("You already have a pending booking for this service.")
        return redirect(url_for('vendor_details', service_id=service_id))

    conn.execute('''
        INSERT INTO bookings
        (client_id, manager_id, service_id, event_date, event_location,
         status, client_phone, client_message, total_amount, selected_package)
        VALUES (?,?,?,?,?,'pending',?,?,?,?)
    ''', (session['user_id'], manager_id, service_id, event_date, event_location,
          client_phone, client_message, total_amount, sel_package))
    conn.commit()

    # In-app notification for manager
    add_notification(int(manager_id), "New Booking Request",
        f"{session['user_name']} has requested a booking for {svc['service_name'] if svc else 'your service'}.",
        'booking', url_for('dashboard'))

    if notify_email == 'on' and svc:
        manager = conn.execute("SELECT u.email, u.full_name FROM users u WHERE id=?", (manager_id,)).fetchone()
        client  = conn.execute("SELECT email FROM users WHERE id=?", (session['user_id'],)).fetchone()
        if manager and client:
            send_booking_email(manager['email'], manager['full_name'],
                session['user_name'], client['email'], client_phone,
                event_date, svc['service_name'], client_message, sel_package or svc['package_tier'])

    conn.close()
    flash("Booking request sent successfully!")
    return redirect(url_for('user_dashboard'))

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    reason = request.form.get('cancel_reason', '')
    conn = get_db_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id=? AND client_id=? AND status IN ('pending','confirmed')",
        (booking_id, session['user_id'])
    ).fetchone()
    if booking:
        conn.execute(
            "UPDATE bookings SET status='cancelled', cancelled_by='user', cancel_reason=? WHERE id=?",
            (reason, booking_id)
        )
        conn.commit()
        add_notification(booking['manager_id'], "Booking Cancelled",
            f"{session['user_name']} cancelled their booking.",
            'warning', url_for('dashboard'))
        flash("Booking cancelled.")
    conn.close()
    return redirect(url_for('user_dashboard'))

@app.route('/pay_booking', methods=['POST'])
def pay_booking():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    booking_id = request.form.get('booking_id')
    conn = get_db_connection()
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id=? AND client_id=? AND status='confirmed'",
        (booking_id, session['user_id'])
    ).fetchone()
    if booking:
        conn.execute("UPDATE bookings SET payment_status='paid' WHERE id=?", (booking_id,))
        conn.commit()
        flash("Mock payment successful! You can now leave a review.")
    else:
        flash("Booking not found or not ready for payment.")
    conn.close()
    return redirect(url_for('user_dashboard'))


# ─── REVIEWS ──────────────────────────────────────────────────────────────────
@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    manager_id  = request.form.get('manager_id')
    service_id  = request.form.get('service_id')
    rating      = request.form.get('rating')
    review_text = request.form.get('review_text', '').strip()

    conn = get_db_connection()
    paid = conn.execute(
        "SELECT id FROM bookings WHERE client_id=? AND service_id=? AND status='confirmed' AND payment_status='paid' LIMIT 1",
        (session['user_id'], service_id)
    ).fetchone()
    if not paid:
        conn.close()
        flash("You need a confirmed and paid booking to leave a review.")
        return redirect(url_for('vendor_details', service_id=service_id))

    existing = conn.execute(
        "SELECT id FROM reviews WHERE client_id=? AND manager_id=?",
        (session['user_id'], manager_id)
    ).fetchone()
    if existing:
        conn.close()
        flash("You have already reviewed this vendor.")
        return redirect(url_for('vendor_details', service_id=service_id))

    conn.execute(
        "INSERT INTO reviews (client_id, manager_id, booking_id, rating, review_text) VALUES (?,?,?,?,?)",
        (session['user_id'], manager_id, paid['id'], rating, review_text)
    )
    avg = conn.execute("SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1", (manager_id,)).fetchone()[0]
    conn.execute("UPDATE manager_profiles SET rating=? WHERE user_id=?", (round(avg or 0, 1), manager_id))
    conn.commit()
    add_notification(int(manager_id), "New Review",
        f"{session['user_name']} left a {rating}-star review.", 'success', url_for('dashboard'))
    conn.close()
    flash("Review submitted. Thank you!")
    return redirect(url_for('vendor_details', service_id=service_id))

@app.route('/edit_review/<int:review_id>', methods=['POST'])
def edit_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    service_id  = request.form.get('service_id')
    new_rating  = request.form.get('rating')
    new_text    = request.form.get('review_text', '')
    conn = get_db_connection()
    rev = conn.execute("SELECT manager_id FROM reviews WHERE id=? AND client_id=?", (review_id, session['user_id'])).fetchone()
    if not rev:
        conn.close()
        flash("Unauthorized.")
        return redirect(url_for('vendor_details', service_id=service_id))
    conn.execute("UPDATE reviews SET rating=?, review_text=? WHERE id=?", (new_rating, new_text, review_id))
    avg = conn.execute("SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1", (rev['manager_id'],)).fetchone()[0]
    conn.execute("UPDATE manager_profiles SET rating=? WHERE user_id=?", (round(avg or 0, 1), rev['manager_id']))
    conn.commit()
    conn.close()
    flash("Review updated.")
    return redirect(url_for('vendor_details', service_id=service_id))

@app.route('/delete_review/<int:review_id>', methods=['POST'])
def delete_review(review_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    service_id = request.form.get('service_id')
    conn = get_db_connection()
    rev = conn.execute("SELECT manager_id FROM reviews WHERE id=? AND client_id=?", (review_id, session['user_id'])).fetchone()
    if not rev:
        conn.close()
        flash("Unauthorized.")
        return redirect(url_for('vendor_details', service_id=service_id))
    conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))
    avg = conn.execute("SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1", (rev['manager_id'],)).fetchone()[0]
    conn.execute("UPDATE manager_profiles SET rating=? WHERE user_id=?", (round(avg or 0, 1), rev['manager_id']))
    conn.commit()
    conn.close()
    flash("Review deleted.")
    return redirect(url_for('vendor_details', service_id=service_id))


# ─── COMPLAINTS ───────────────────────────────────────────────────────────────
@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))
    booking_id  = request.form.get('booking_id') or None
    manager_id  = request.form.get('manager_id') or None
    category    = request.form.get('complaint_category', '')
    description = request.form.get('complaint_description', '').strip()
    if not category or not description:
        flash("Please fill all complaint fields.")
        return redirect(url_for('user_dashboard'))
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO complaints (client_id, booking_id, manager_id, category, description) VALUES (?,?,?,?,?)",
        (session['user_id'], booking_id, manager_id, category, description)
    )
    conn.commit()
    admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
    if admin:
        add_notification(admin['id'], "New Complaint",
            f"{session['user_name']} submitted a complaint: {category}",
            'warning', url_for('admin_complaints'))
    conn.close()
    flash("Complaint submitted successfully.")
    return redirect(url_for('user_dashboard'))

# ─── NOTIFICATIONS ────────────────────────────────────────────────────────────
@app.route('/notifications/mark_read', methods=['POST'])
def mark_notifications_read():
    if 'user_id' not in session:
        return jsonify({'success': False})
    conn = get_db_connection()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session['user_id'],))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/notifications/mark_one/<int:notif_id>', methods=['POST'])
def mark_one_read(notif_id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    conn = get_db_connection()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?", (notif_id, session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── PUBLIC EXPLORE ───────────────────────────────────────────────────────────
@app.route('/public_explore')
def public_explore():
    conn = get_db_connection()
    all_services = conn.execute('''
        SELECT s.*, m.business_name, m.profile_pic, m.rating
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON s.manager_id = u.id
        WHERE u.is_approved=1 AND u.is_active=1 AND s.is_active=1
        ORDER BY m.rating DESC
    ''').fetchall()
    categories = conn.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY name").fetchall()
    conn.close()
    return render_template('public_explore.html', services=all_services, categories=categories)

@app.route('/public_vendor_details/<int:service_id>')
def public_vendor_details(service_id):
    conn = get_db_connection()
    service = conn.execute('''
        SELECT s.*, m.business_name, m.rating, m.phone, u.full_name as manager_name
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON m.user_id = u.id
        WHERE s.id=?
    ''', (service_id,)).fetchone()
    if not service:
        flash("Vendor not found.")
        return redirect(url_for('public_explore'))
    reviews = conn.execute('''
        SELECT r.*, u.full_name as client_name FROM reviews r
        JOIN users u ON r.client_id = u.id
        WHERE r.manager_id=? AND r.is_visible=1
        ORDER BY r.created_at DESC
    ''', (service['manager_id'],)).fetchall()
    conn.close()
    return render_template('public_vendor_details.html', service=service, reviews=reviews)


# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR / EVENT MANAGER MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    profile  = conn.execute("SELECT * FROM manager_profiles WHERE user_id=?", (session['user_id'],)).fetchone()
    bookings = conn.execute('''
        SELECT b.*, u.full_name as client_name, s.service_name, s.category
        FROM bookings b
        JOIN users u ON b.client_id = u.id
        LEFT JOIN services s ON b.service_id = s.id
        WHERE b.manager_id=? ORDER BY b.created_at DESC
    ''', (session['user_id'],)).fetchall()

    total_bk   = len(bookings)
    pending_bk = sum(1 for b in bookings if b['status'] == 'pending')
    confirmed_bk = sum(1 for b in bookings if b['status'] == 'confirmed')
    completed_bk = sum(1 for b in bookings if b['status'] == 'completed')
    revenue    = sum((b['total_amount'] or 0) for b in bookings if b['payment_status'] == 'paid')

    reviews = conn.execute('''
        SELECT r.*, u.full_name as client_name FROM reviews r
        JOIN users u ON r.client_id = u.id
        WHERE r.manager_id=? AND r.is_visible=1 ORDER BY r.created_at DESC LIMIT 5
    ''', (session['user_id'],)).fetchall()

    avg_rating = conn.execute(
        "SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1",
        (session['user_id'],)
    ).fetchone()[0] or 0

    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (session['user_id'],)
    ).fetchall()
    unread_count = sum(1 for n in notifs if not n['is_read'])

    conn.close()
    return render_template('dashboard.html',
        profile=profile, bookings=bookings,
        total_bookings=total_bk, pending_count=pending_bk,
        confirmed_count=confirmed_bk, completed_count=completed_bk,
        total_revenue=revenue, reviews=reviews, avg_rating=round(avg_rating, 1),
        notifications=notifs, unread_count=unread_count)

@app.route('/profile')
def profile():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.*
        FROM users u JOIN manager_profiles m ON u.id = m.user_id
        WHERE u.id=?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user_data)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        full_name    = request.form.get('full_name', '').strip()
        business_name= request.form.get('business_name', '').strip()
        phone        = request.form.get('phone', '').strip()
        bio          = request.form.get('bio', '').strip()
        location     = request.form.get('location', '').strip()
        file         = request.files.get('profile_pic')

        conn.execute("UPDATE users SET full_name=? WHERE id=?", (full_name, session['user_id']))

        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(f"pp_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute(
                "UPDATE manager_profiles SET business_name=?, phone=?, bio=?, location=?, profile_pic=? WHERE user_id=?",
                (business_name, phone, bio, location, filename, session['user_id'])
            )
        else:
            conn.execute(
                "UPDATE manager_profiles SET business_name=?, phone=?, bio=?, location=? WHERE user_id=?",
                (business_name, phone, bio, location, session['user_id'])
            )
        conn.commit()
        session['user_name'] = full_name
        flash("Profile updated successfully!")
        conn.close()
        return redirect(url_for('edit_profile'))

    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.*
        FROM users u JOIN manager_profiles m ON u.id = m.user_id WHERE u.id=?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user_data)


# ─── PORTFOLIO (VENDOR SERVICES) ──────────────────────────────────────────────
@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        category        = ", ".join(request.form.getlist('category'))
        service_name    = request.form.get('service_name', '').strip()
        service_location= request.form.get('service_location', '').strip()
        services_offered= request.form.get('services_offered', '')
        package_tier    = request.form.get('package_tier', 'Standard')
        experience_years= request.form.get('experience_years', 0)
        description     = request.form.get('description', '').strip()
        unavail_dates   = request.form.get('unavailable_dates', '')
        pricing_amount  = request.form.get('pricing_amount', '0')
        pricing_unit    = request.form.get('pricing_unit', 'per event')
        combined_pricing= f"{pricing_amount} {pricing_unit}"

        uploaded = request.files.getlist('event_images')
        imgs = []
        for f in uploaded:
            if f and f.filename and allowed_file(f.filename):
                fn = secure_filename(f"port_{session['user_id']}_{f.filename}")
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
                imgs.append(fn)
        images_str = ",".join(imgs)

        conn.execute('''
            INSERT INTO services
            (manager_id, category, service_name, service_location, services_offered,
             package_tier, experience_years, pricing, images, description, unavailable_dates)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', (session['user_id'], category, service_name, service_location, services_offered,
              package_tier, experience_years, combined_pricing, images_str, description, unavail_dates))
        conn.commit()
        flash("Portfolio item added!")
        conn.close()
        return redirect(url_for('portfolio'))

    my_services = conn.execute("SELECT * FROM services WHERE manager_id=? ORDER BY id DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('portfolio.html', services=my_services)

@app.route('/edit_portfolio/<int:service_id>', methods=['POST'])
def edit_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    svc = conn.execute("SELECT * FROM services WHERE id=? AND manager_id=?", (service_id, session['user_id'])).fetchone()
    if not svc:
        flash("Unauthorized.")
        conn.close()
        return redirect(url_for('portfolio'))

    category        = ", ".join(request.form.getlist('category'))
    service_name    = request.form.get('service_name', '').strip()
    service_location= request.form.get('service_location', '').strip()
    services_offered= request.form.get('services_offered', '')
    package_tier    = request.form.get('package_tier', 'Standard')
    experience_years= request.form.get('experience_years', 0)
    description     = request.form.get('description', '').strip()
    unavail_dates   = request.form.get('unavailable_dates', '')
    pricing_amount  = request.form.get('pricing_amount', '0')
    pricing_unit    = request.form.get('pricing_unit', 'per event')
    combined_pricing= f"{pricing_amount} {pricing_unit}"

    curr_imgs    = [i for i in (svc['images'] or '').split(',') if i]
    to_delete    = request.form.getlist('delete_images')
    updated_imgs = [i for i in curr_imgs if i not in to_delete]

    for f in request.files.getlist('event_images'):
        if f and f.filename and allowed_file(f.filename):
            fn = secure_filename(f"port_{session['user_id']}_{f.filename}")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn))
            updated_imgs.append(fn)

    conn.execute('''
        UPDATE services SET category=?,service_name=?,service_location=?,services_offered=?,
        package_tier=?,experience_years=?,pricing=?,description=?,images=?,unavailable_dates=?
        WHERE id=? AND manager_id=?
    ''', (category, service_name, service_location, services_offered,
          package_tier, experience_years, combined_pricing, description,
          ",".join(updated_imgs), unavail_dates, service_id, session['user_id']))
    conn.commit()
    conn.close()
    flash("Portfolio updated!")
    return redirect(url_for('portfolio'))

@app.route('/delete_portfolio/<int:service_id>', methods=['POST'])
def delete_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    svc = conn.execute("SELECT images FROM services WHERE id=? AND manager_id=?", (service_id, session['user_id'])).fetchone()
    if svc:
        conn.execute("DELETE FROM services WHERE id=? AND manager_id=?", (service_id, session['user_id']))
        conn.commit()
        for img in (svc['images'] or '').split(','):
            img = img.strip()
            p = os.path.join(app.config['UPLOAD_FOLDER'], img)
            if img and os.path.exists(p):
                os.remove(p)
        flash("Portfolio item deleted.")
    conn.close()
    return redirect(url_for('portfolio'))


# ─── BOOKING MANAGEMENT (VENDOR) ──────────────────────────────────────────────
@app.route('/view_booking/<int:booking_id>')
def view_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, u.full_name as client_name, u.email as client_email,
               s.service_name, s.category, s.pricing, s.images, s.package_tier
        FROM bookings b
        JOIN users u ON b.client_id = u.id
        LEFT JOIN services s ON b.service_id = s.id
        WHERE b.id=? AND b.manager_id=?
    ''', (booking_id, session['user_id'])).fetchone()
    conn.close()
    if not booking:
        flash("Booking not found.")
        return redirect(url_for('dashboard'))
    return render_template('view_booking.html', booking=booking)

@app.route('/update_booking/<int:booking_id>/<action>', methods=['POST'])
def update_booking(booking_id, action):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, u.email as client_email, u.full_name as client_name,
               m.business_name, s.service_name, s.id as sid
        FROM bookings b
        JOIN users u ON b.client_id = u.id
        JOIN manager_profiles m ON b.manager_id = m.user_id
        LEFT JOIN services s ON b.service_id = s.id
        WHERE b.id=? AND b.manager_id=?
    ''', (booking_id, session['user_id'])).fetchone()

    if booking and booking['status'] == 'pending':
        new_status = 'confirmed' if action == 'approve' else 'rejected'
        conn.execute("UPDATE bookings SET status=? WHERE id=?", (new_status, booking_id))

        if new_status == 'confirmed' and booking['sid']:
            svc = conn.execute("SELECT unavailable_dates FROM services WHERE id=?", (booking['sid'],)).fetchone()
            existing = [d.strip() for d in (svc['unavailable_dates'] or '').split(',') if d.strip()]
            new_dates = [d.strip() for d in booking['event_date'].split(',') if d.strip()]
            merged   = ", ".join(list(set(existing + new_dates)))
            conn.execute("UPDATE services SET unavailable_dates=? WHERE id=?", (merged, booking['sid']))

        conn.commit()
        svc_name = booking['service_name'] or 'your service'
        send_status_email(booking['client_email'], booking['client_name'],
            booking['business_name'], svc_name, booking['event_date'], new_status)
        add_notification(booking['client_id'], f"Booking {new_status.capitalize()}",
            f"Your booking for {svc_name} has been {new_status}.",
            'success' if new_status == 'confirmed' else 'danger',
            url_for('user_dashboard'))
        flash(f"Booking {new_status}!")
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/complete_booking/<int:booking_id>', methods=['POST'])
def complete_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute(
        "UPDATE bookings SET status='completed' WHERE id=? AND manager_id=? AND status='confirmed'",
        (booking_id, session['user_id'])
    )
    conn.commit()
    conn.close()
    flash("Booking marked as completed.")
    return redirect(url_for('dashboard'))


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()

    pending_managers = conn.execute('''
        SELECT u.id, u.full_name, u.email, u.created_at,
               m.business_name, m.phone, m.license_path
        FROM users u JOIN manager_profiles m ON u.id = m.user_id
        WHERE u.role='eventmanager' AND u.is_approved=0
        ORDER BY u.created_at DESC
    ''').fetchall()

    stats = {}
    stats['total_users']      = conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0]
    stats['total_vendors']    = conn.execute("SELECT COUNT(*) FROM users WHERE role='eventmanager' AND is_approved=1").fetchone()[0]
    stats['pending_vendors']  = conn.execute("SELECT COUNT(*) FROM users WHERE role='eventmanager' AND is_approved=0").fetchone()[0]
    stats['total_bookings']   = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    stats['pending_bookings'] = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='pending'").fetchone()[0]
    stats['confirmed_bookings']= conn.execute("SELECT COUNT(*) FROM bookings WHERE status='confirmed'").fetchone()[0]
    stats['completed_bookings']= conn.execute("SELECT COUNT(*) FROM bookings WHERE status='completed'").fetchone()[0]
    stats['total_complaints'] = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    stats['pending_complaints']= conn.execute("SELECT COUNT(*) FROM complaints WHERE status='pending'").fetchone()[0]
    stats['total_reviews']    = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    recent_bookings = conn.execute('''
        SELECT b.*, u.full_name as client_name, m.business_name, s.service_name
        FROM bookings b
        JOIN users u ON b.client_id=u.id
        JOIN manager_profiles m ON b.manager_id=m.user_id
        LEFT JOIN services s ON b.service_id=s.id
        ORDER BY b.created_at DESC LIMIT 10
    ''').fetchall()

    notifs = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 20",
        (session['user_id'],)
    ).fetchall()
    unread_count = sum(1 for n in notifs if not n['is_read'])

    conn.close()
    return render_template('admin_dashboard.html',
        pending_managers=pending_managers, stats=stats,
        recent_bookings=recent_bookings,
        notifications=notifs, unread_count=unread_count)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    search = request.args.get('q', '')
    role_f = request.args.get('role', '')
    query  = '''
        SELECT u.id, u.full_name, u.email, u.role, u.is_approved, u.is_active, u.created_at,
               m.business_name, m.phone, m.license_path
        FROM users u LEFT JOIN manager_profiles m ON u.id = m.user_id
        WHERE u.role != 'admin'
    '''
    params = []
    if search:
        query += " AND (u.full_name LIKE ? OR u.email LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if role_f:
        query += " AND u.role=?"
        params.append(role_f)
    query += " ORDER BY u.created_at DESC"
    all_users = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin_users.html', all_users=all_users, search=search, role_f=role_f)

@app.route('/admin/toggle_user/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    user = conn.execute("SELECT is_active FROM users WHERE id=?", (user_id,)).fetchone()
    if user:
        new_status = 0 if user['is_active'] else 1
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (new_status, user_id))
        conn.commit()
        flash("User status updated.")
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>', methods=['GET', 'POST'])
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute("DELETE FROM manager_profiles WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted.")
    return redirect(url_for('admin_users'))


# ─── ADMIN: VENDOR APPROVAL ───────────────────────────────────────────────────
@app.route('/admin_action/<int:manager_id>/<action>', methods=['POST'])
def admin_action(manager_id, action):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT email, full_name FROM users WHERE id=?", (manager_id,)).fetchone()
        if action == 'approve':
            conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (manager_id,))
            conn.commit()
            if user:
                send_manager_approval_email(user['email'], user['full_name'])
                add_notification(manager_id, "Account Approved",
                    "Your event manager account has been approved! You can now log in.",
                    'success', '/')
            flash("Vendor approved and notified.")
        elif action == 'reject':
            conn.execute("DELETE FROM manager_profiles WHERE user_id=?", (manager_id,))
            conn.execute("DELETE FROM users WHERE id=?", (manager_id,))
            conn.commit()
            flash("Vendor registration rejected.")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {e}")
    finally:
        conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_manager/<int:user_id>')
def approve_manager(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    user = conn.execute("SELECT email, full_name FROM users WHERE id=?", (user_id,)).fetchone()
    conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (user_id,))
    conn.commit()
    if user:
        send_manager_approval_email(user['email'], user['full_name'])
        add_notification(user_id, "Account Approved",
            "Your vendor account has been approved!", 'success', '/')
    conn.close()
    flash("Manager approved!")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_manager/<int:user_id>')
def reject_manager(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute("DELETE FROM manager_profiles WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("Manager rejected and removed.")
    return redirect(url_for('admin_dashboard'))

# ─── ADMIN: BOOKINGS ─────────────────────────────────────────────────────────
@app.route('/admin/bookings')
def admin_bookings():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    status_f = request.args.get('status', '')
    search   = request.args.get('q', '')
    query = '''
        SELECT b.*, u.full_name as client_name, m.business_name, s.service_name
        FROM bookings b
        JOIN users u ON b.client_id=u.id
        JOIN manager_profiles m ON b.manager_id=m.user_id
        LEFT JOIN services s ON b.service_id=s.id WHERE 1=1
    '''
    params = []
    if status_f:
        query += " AND b.status=?"
        params.append(status_f)
    if search:
        query += " AND (u.full_name LIKE ? OR m.business_name LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    query += " ORDER BY b.created_at DESC"
    bookings = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin_bookings.html', bookings=bookings, status_f=status_f, search=search)

# ─── ADMIN: COMPLAINTS ────────────────────────────────────────────────────────
@app.route('/admin/complaints')
def admin_complaints():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    status_f = request.args.get('status', '')
    query = '''
        SELECT c.*, u.full_name as client_name, m.business_name
        FROM complaints c
        JOIN users u ON c.client_id=u.id
        LEFT JOIN manager_profiles m ON c.manager_id=m.user_id WHERE 1=1
    '''
    params = []
    if status_f:
        query += " AND c.status=?"
        params.append(status_f)
    query += " ORDER BY c.created_at DESC"
    complaints = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('admin_complaints.html', complaints=complaints, status_f=status_f)

@app.route('/admin/resolve_complaint/<int:complaint_id>', methods=['POST'])
def resolve_complaint(complaint_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    response   = request.form.get('admin_response', '').strip()
    new_status = request.form.get('status', 'resolved')
    conn = get_db_connection()
    complaint = conn.execute("SELECT client_id FROM complaints WHERE id=?", (complaint_id,)).fetchone()
    conn.execute(
        "UPDATE complaints SET status=?, admin_response=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (new_status, response, complaint_id)
    )
    conn.commit()
    if complaint:
        add_notification(complaint['client_id'], "Complaint Update",
            f"Your complaint has been {new_status}.",
            'info', url_for('user_dashboard'))
    conn.close()
    flash("Complaint updated.")
    return redirect(url_for('admin_complaints'))


# ─── ADMIN: REVIEWS ──────────────────────────────────────────────────────────
@app.route('/admin/reviews')
def admin_reviews():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    reviews = conn.execute('''
        SELECT r.*, u.full_name as client_name, m.business_name
        FROM reviews r
        JOIN users u ON r.client_id=u.id
        JOIN manager_profiles m ON r.manager_id=m.user_id
        ORDER BY r.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('admin_reviews.html', reviews=reviews)

@app.route('/admin/toggle_review/<int:review_id>', methods=['POST'])
def toggle_review_visibility(review_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    rev = conn.execute("SELECT is_visible, manager_id FROM reviews WHERE id=?", (review_id,)).fetchone()
    if rev:
        new_vis = 0 if rev['is_visible'] else 1
        conn.execute("UPDATE reviews SET is_visible=? WHERE id=?", (new_vis, review_id))
        avg = conn.execute(
            "SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1", (rev['manager_id'],)
        ).fetchone()[0]
        conn.execute("UPDATE manager_profiles SET rating=? WHERE user_id=?",
            (round(avg or 0, 1), rev['manager_id']))
        conn.commit()
        flash("Review visibility toggled.")
    conn.close()
    return redirect(url_for('admin_reviews'))

@app.route('/admin/delete_review/<int:review_id>', methods=['POST'])
def admin_delete_review(review_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    rev = conn.execute("SELECT manager_id FROM reviews WHERE id=?", (review_id,)).fetchone()
    if rev:
        conn.execute("DELETE FROM reviews WHERE id=?", (review_id,))
        avg = conn.execute(
            "SELECT AVG(rating) FROM reviews WHERE manager_id=? AND is_visible=1", (rev['manager_id'],)
        ).fetchone()[0]
        conn.execute("UPDATE manager_profiles SET rating=? WHERE user_id=?",
            (round(avg or 0, 1), rev['manager_id']))
        conn.commit()
    conn.close()
    flash("Review deleted.")
    return redirect(url_for('admin_reviews'))

# ─── ADMIN: CATEGORIES ────────────────────────────────────────────────────────
@app.route('/admin/categories')
def admin_categories():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template('admin_categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['POST'])
def add_category():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    icon = request.form.get('icon', 'fas fa-star').strip()
    if not name:
        flash("Category name is required.")
        return redirect(url_for('admin_categories'))
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO categories (name, description, icon) VALUES (?,?,?)", (name, desc, icon))
        conn.commit()
        flash(f"Category '{name}' added.")
    except sqlite3.IntegrityError:
        flash("Category already exists.")
    finally:
        conn.close()
    return redirect(url_for('admin_categories'))

@app.route('/admin/categories/delete/<int:cat_id>', methods=['POST'])
def delete_category(cat_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()
    flash("Category deleted.")
    return redirect(url_for('admin_categories'))

# ─── ADMIN: REPORTS ───────────────────────────────────────────────────────────
@app.route('/admin/reports')
def admin_reports():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    monthly = conn.execute('''
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as total,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled,
               SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END) as revenue
        FROM bookings GROUP BY month ORDER BY month DESC LIMIT 12
    ''').fetchall()
    top_vendors = conn.execute('''
        SELECT m.business_name, u.full_name, m.rating,
               COUNT(b.id) as total_bookings,
               SUM(CASE WHEN b.payment_status='paid' THEN b.total_amount ELSE 0 END) as revenue
        FROM manager_profiles m
        JOIN users u ON m.user_id=u.id
        LEFT JOIN bookings b ON b.manager_id=u.id
        WHERE u.is_approved=1 GROUP BY u.id ORDER BY total_bookings DESC LIMIT 10
    ''').fetchall()
    conn.close()
    return render_template('admin_reports.html', monthly=monthly, top_vendors=top_vendors)


# ═══════════════════════════════════════════════════════════════════════════════
# AI CHATBOT & CUSTOM QUESTIONS MODULE
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/chatbot/questions', methods=['GET'])
def get_chatbot_questions():
    conn = get_db_connection()
    questions = conn.execute(
        "SELECT id, question, category FROM chatbot_questions WHERE is_active=1 ORDER BY category, id"
    ).fetchall()
    conn.close()
    return jsonify([dict(q) for q in questions])

@app.route('/api/chatbot', methods=['POST'])
def chatbot_reply():
    data = request.get_json(silent=True) or {}
    user_msg = (data.get('message') or '').strip()
    q_id = data.get('question_id')

    conn = get_db_connection()

    # 1. Direct Question ID match (from quick chip selection)
    if q_id:
        q_item = conn.execute(
            "SELECT * FROM chatbot_questions WHERE id=? AND is_active=1", (q_id,)
        ).fetchone()
        if q_item:
            suggestions = conn.execute(
                "SELECT id, question FROM chatbot_questions WHERE id != ? AND is_active=1 ORDER BY RANDOM() LIMIT 3",
                (q_id,)
            ).fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'question': q_item['question'],
                'answer': q_item['answer'],
                'suggested_questions': [dict(s) for s in suggestions]
            })

    if not user_msg:
        conn.close()
        return jsonify({'success': False, 'answer': "Please type a message or select one of the suggested custom questions."})

    user_lower = user_msg.lower()

    # 2. Dynamic Live Data Intelligence
    # Vendor search / top vendors
    if any(k in user_lower for k in ['vendor', 'manager', 'who', 'top rated', 'services offered', 'available vendors']):
        top_vendors = conn.execute('''
            SELECT m.business_name, m.rating, s.service_name, s.category, s.pricing
            FROM manager_profiles m
            JOIN users u ON m.user_id=u.id
            JOIN services s ON s.manager_id=u.id
            WHERE u.is_approved=1 AND u.is_active=1 AND s.is_active=1
            ORDER BY m.rating DESC LIMIT 3
        ''').fetchall()
        if top_vendors:
            v_list = "<br>".join([
                f"• <b>{v['business_name']}</b> ({v['category']}) — Rating: ⭐{v['rating']} ({v['service_name']} @ {v['pricing']})"
                for v in top_vendors
            ])
            answer = f"Here are some of our top-rated event managers and services available on Evenzo:<br><br>{v_list}<br><br>Click the button below to explore all vendors!"
            suggestions = conn.execute("SELECT id, question FROM chatbot_questions WHERE is_active=1 LIMIT 3").fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'answer': answer,
                'action': {'text': 'Explore All Vendors', 'url': url_for('public_explore')},
                'suggested_questions': [dict(s) for s in suggestions]
            })

    # Categories list
    if any(k in user_lower for k in ['category', 'categories', 'event type', 'types of events', 'what events']):
        cats = conn.execute("SELECT name FROM categories WHERE is_active=1 ORDER BY name").fetchall()
        cat_names = ", ".join([c['name'] for c in cats])
        answer = f"Evenzo offers a rich variety of event categories including:<br><br><b>{cat_names}</b>.<br><br>Whether you're organizing a grand Wedding, Birthday, Corporate Gathering, or Live Show, Evenzo has verified experts ready for you!"
        suggestions = conn.execute("SELECT id, question FROM chatbot_questions WHERE is_active=1 LIMIT 3").fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'answer': answer,
            'action': {'text': 'View Wedding Services', 'url': url_for('weddingservices')},
            'suggested_questions': [dict(s) for s in suggestions]
        })

    # Logged-in user's active bookings
    if any(k in user_lower for k in ['my booking', 'my status', 'check booking', 'my order', 'my event']) and session.get('user_id'):
        user_bks = conn.execute('''
            SELECT b.id, b.status, b.event_date, m.business_name, s.service_name
            FROM bookings b
            JOIN manager_profiles m ON b.manager_id=m.user_id
            LEFT JOIN services s ON b.service_id=s.id
            WHERE b.client_id=? ORDER BY b.created_at DESC LIMIT 3
        ''', (session['user_id'],)).fetchall()
        if user_bks:
            b_list = "<br>".join([
                f"• <b>{b['service_name'] or 'Event Service'}</b> with {b['business_name']} on {b['event_date']} — Status: <b style='text-transform:uppercase;'>{b['status']}</b>"
                for b in user_bks
            ])
            answer = f"Here is the status of your recent bookings:<br><br>{b_list}"
            suggestions = conn.execute("SELECT id, question FROM chatbot_questions WHERE is_active=1 LIMIT 3").fetchall()
            conn.close()
            return jsonify({
                'success': True,
                'answer': answer,
                'action': {'text': 'Open My Dashboard', 'url': url_for('user_dashboard')},
                'suggested_questions': [dict(s) for s in suggestions]
            })

    # 3. Match against database of Custom Questions (Keywords & String Similarity)
    all_qs = conn.execute("SELECT * FROM chatbot_questions WHERE is_active=1").fetchall()

    best_match = None
    max_score = 0
    words = [w for w in user_lower.split() if len(w) > 2]

    for q in all_qs:
        score = 0
        q_text = q['question'].lower()
        kw_text = (q['keywords'] or '').lower()

        # Direct substring match
        if q_text in user_lower or user_lower in q_text:
            score += 12

        for w in words:
            if w in q_text:
                score += 3
            if w in kw_text:
                score += 4

        if score > max_score:
            max_score = score
            best_match = q

    if best_match and max_score >= 3:
        suggestions = conn.execute(
            "SELECT id, question FROM chatbot_questions WHERE id != ? AND is_active=1 ORDER BY RANDOM() LIMIT 3",
            (best_match['id'],)
        ).fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'question': best_match['question'],
            'answer': best_match['answer'],
            'suggested_questions': [dict(s) for s in suggestions]
        })

    # 4. Gemini Generative AI Fallback (if API key available)
    gemini_reply = call_gemini_ai(user_msg)
    if gemini_reply:
        suggestions = conn.execute("SELECT id, question FROM chatbot_questions WHERE is_active=1 ORDER BY RANDOM() LIMIT 3").fetchall()
        conn.close()
        return jsonify({
            'success': True,
            'answer': f"🤖 <b>AI Concierge:</b><br>{gemini_reply}",
            'suggested_questions': [dict(s) for s in suggestions]
        })

    # 5. Smart Fallback response with custom question suggestions
    suggestions = conn.execute("SELECT id, question FROM chatbot_questions WHERE is_active=1 ORDER BY RANDOM() LIMIT 4").fetchall()
    conn.close()
    return jsonify({
        'success': True,
        'answer': f"I'm Evenzo's AI Concierge! 🤖<br>I didn't find an exact match for <i>\"{user_msg}\"</i>, but I can answer key questions about vendor booking, pricing, account setup, or complaints.<br><br>Select a popular custom question below:",
        'suggested_questions': [dict(s) for s in suggestions]
    })



# ─── ADMIN: CHATBOT Q&A MANAGEMENT ─────────────────────────────────────────────
@app.route('/admin/chatbot')
def admin_chatbot():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    questions = conn.execute("SELECT * FROM chatbot_questions ORDER BY category, id DESC").fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM chatbot_questions WHERE category IS NOT NULL").fetchall()
    conn.close()
    return render_template('admin_chatbot.html', questions=questions, categories=categories)

@app.route('/admin/chatbot/add', methods=['POST'])
def admin_add_chatbot_question():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    q = request.form.get('question', '').strip()
    a = request.form.get('answer', '').strip()
    cat = request.form.get('category', 'General').strip()
    kw = request.form.get('keywords', '').strip()
    if not q or not a:
        flash("Question and Answer are required.")
        return redirect(url_for('admin_chatbot'))
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO chatbot_questions (question, answer, category, keywords) VALUES (?,?,?,?)",
        (q, a, cat, kw)
    )
    conn.commit()
    conn.close()
    flash("New custom chatbot question added successfully!")
    return redirect(url_for('admin_chatbot'))

@app.route('/admin/chatbot/edit/<int:q_id>', methods=['POST'])
def admin_edit_chatbot_question(q_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    q = request.form.get('question', '').strip()
    a = request.form.get('answer', '').strip()
    cat = request.form.get('category', 'General').strip()
    kw = request.form.get('keywords', '').strip()
    conn = get_db_connection()
    conn.execute(
        "UPDATE chatbot_questions SET question=?, answer=?, category=?, keywords=? WHERE id=?",
        (q, a, cat, kw, q_id)
    )
    conn.commit()
    conn.close()
    flash("Chatbot custom question updated!")
    return redirect(url_for('admin_chatbot'))

@app.route('/admin/chatbot/toggle/<int:q_id>', methods=['POST'])
def admin_toggle_chatbot_question(q_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    q = conn.execute("SELECT is_active FROM chatbot_questions WHERE id=?", (q_id,)).fetchone()
    if q:
        new_s = 0 if q['is_active'] else 1
        conn.execute("UPDATE chatbot_questions SET is_active=? WHERE id=?", (new_s, q_id))
        conn.commit()
        flash("Question active status updated.")
    conn.close()
    return redirect(url_for('admin_chatbot'))

@app.route('/admin/chatbot/delete/<int:q_id>', methods=['POST'])
def admin_delete_chatbot_question(q_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    conn = get_db_connection()
    conn.execute("DELETE FROM chatbot_questions WHERE id=?", (q_id,))
    conn.commit()
    conn.close()
    flash("Chatbot custom question deleted.")
    return redirect(url_for('admin_chatbot'))

# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
