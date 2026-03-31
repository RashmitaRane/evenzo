from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import timedelta

# 🟢 EMAIL LIBRARIES
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ⚠️ REPLACE THESE WITH YOUR REAL CREDENTIALS FOR PRODUCTION ⚠️
EMAIL_SENDER = "shelicoa26@gmail.com" 
EMAIL_APP_PASSWORD = "ywlg kisi dkwj rjhi" 

app = Flask(__name__, 
            template_folder='frontend/templates', 
            static_folder='frontend/static')

app.secret_key = 'evenzo_secret_key_123'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  
    return conn

# --- 🟢 SECURE PROFESSIONAL EMAIL FUNCTIONS ---
def send_booking_email(manager_email, manager_name, client_name, client_email, client_phone, event_dates, service_name, message, package_name):
    subject = f"New Booking Request: {service_name} by {client_name}"
    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #953553; margin: 0;">Evenzo</h1>
            <p style="color: #888; font-size: 14px; margin-top: 5px;">You have a new booking request!</p>
        </div>
        <p>Hello <strong>{manager_name}</strong>,</p>
        <p>A client has requested to book your service: <strong>{service_name}</strong>.</p>
        <div style="background: #fdf5f7; padding: 20px; border-left: 5px solid #953553; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #953553; margin-top: 0;">Client Details</h3>
            <p style="margin: 5px 0;"><strong>Name:</strong> {client_name}</p>
            <p style="margin: 5px 0;"><strong>Email:</strong> <a href="mailto:{client_email}">{client_email}</a></p>
            <p style="margin: 5px 0;"><strong>Phone:</strong> +91 {client_phone}</p>
            <p style="margin: 5px 0;"><strong>Requested Date(s):</strong> {event_dates}</p>
            <p style="margin: 5px 0;"><strong>Selected Package:</strong> <span style="color: #953553; font-weight: bold;">{package_name}</span></p>
            <h3 style="color: #953553; margin-top: 20px;">Message from Client:</h3>
            <p style="background: white; padding: 15px; border-radius: 6px; border: 1px solid #eee; font-style: italic;">"{message}"</p>
        </div>
        <p>Please log in to your Evenzo Event Manager Dashboard to Approve or Reject this request.</p>
    </body>
    </html>
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Evenzo Notifications <{EMAIL_SENDER}>"
        msg['To'] = manager_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Email sending failed:", str(e))

def send_status_email(client_email, client_name, manager_name, service_name, event_dates, status):
    if status == 'confirmed':
        subject = f"Booking Confirmed! {service_name}"
        header_color = "#2e7d32"
        icon = "🎉"
        body_text = f"Great news! Your booking for <strong>{event_dates}</strong> has been officially accepted and confirmed by {manager_name}."
    else:
        subject = f"Booking Update: {service_name}"
        header_color = "#d32f2f"
        icon = "📝"
        body_text = f"We regret to inform you that {manager_name} is currently unavailable and had to decline your booking request for <strong>{event_dates}</strong>."

    html_content = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 20px;">
            <h1 style="color: #953553; margin: 0;">Evenzo</h1>
            <h2 style="color: {header_color};">{icon} Booking {status.capitalize()}</h2>
        </div>
        <p>Hello <strong>{client_name}</strong>,</p>
        <p>{body_text}</p>
        <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>Service:</strong> {service_name}</p>
            <p style="margin: 5px 0;"><strong>Vendor:</strong> {manager_name}</p>
            <p style="margin: 5px 0;"><strong>Status:</strong> <span style="color: {header_color}; font-weight: bold; text-transform: uppercase;">{status}</span></p>
        </div>
        <p>Log in to your Evenzo Dashboard for more details.</p>
        <br>
        <p>Best regards,<br><strong>The Evenzo Team</strong></p>
    </body>
    </html>
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Evenzo Notifications <{EMAIL_SENDER}>"
        msg['To'] = client_email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Status Email failed:", str(e))

# --- ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/weddingservices')
def weddingservices(): return render_template('weddingservices.html')

@app.route('/specialservices')
def specialservices(): return render_template('Specialservices.html')

@app.route('/corporateservices')
def corporateservices(): return render_template('Corporateservices.html')

@app.route('/publicservices')
def publicservices(): return render_template('publicservices.html')

@app.route('/register', methods=['POST'])
def register():
    role = request.form.get('regUserRole')
    full_name = request.form.get('regFullName')
    email = request.form.get('regEmail')
    password = request.form.get('regPass')

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (full_name, email, password, role, is_approved) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, password, role, 1 if role == 'user' else 0)
        )
        user_id = cursor.lastrowid

        if role == 'eventmanager':
            biz_name = request.form.get('regBusinessName')
            phone = request.form.get('regPhone')
            file = request.files.get('regLicense')
            filename = ""
            if file:
                filename = secure_filename(f"{user_id}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cursor.execute(
                "INSERT INTO manager_profiles (user_id, business_name, phone, license_path) VALUES (?, ?, ?, ?)",
                (user_id, biz_name, phone, filename)
            )

        conn.commit()
        flash("Registration Successful! Please Login.")
    except sqlite3.IntegrityError:
        flash("Email already exists.")
    finally:
        conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    role_requested = request.form.get('userRole')

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ? AND password = ? AND role = ?", (email, password, role_requested)).fetchone()
    conn.close()

    if user:
        session.permanent = True 
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']
        if user['role'] == 'eventmanager': return redirect(url_for('dashboard'))
        elif user['role'] == 'user': return redirect(url_for('user_dashboard'))
        return redirect(url_for('index'))
    else:
        flash("Invalid Credentials or Role.")
        return redirect(url_for('index'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user': return redirect(url_for('index'))
    conn = get_db_connection()
    user_info = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    my_bookings = conn.execute('''
        SELECT b.*, m.business_name, s.service_name, s.pricing 
        FROM bookings b JOIN manager_profiles m ON b.manager_id = m.user_id LEFT JOIN services s ON b.service_id = s.id
        WHERE b.client_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('user_dashboard.html', user=user_info, bookings=my_bookings)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'eventmanager': 
        return redirect(url_for('index'))
        
    conn = get_db_connection()
    profile = conn.execute("SELECT * FROM manager_profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    
    bookings = conn.execute('''
        SELECT b.*, u.full_name as client_name 
        FROM bookings b JOIN users u ON b.client_id = u.id 
        WHERE b.manager_id = ? ORDER BY b.created_at DESC
    ''', (session['user_id'],)).fetchall()
    
    total_bookings = len(bookings)
    pending_count = sum(1 for b in bookings if b['status'] == 'pending')
    total_revenue = sum((b['total_amount'] or 0) for b in bookings if b['payment_status'] == 'paid')
    
    conn.close()
    return render_template('dashboard.html', profile=profile, bookings=bookings, total_bookings=total_bookings, pending_count=pending_count, total_revenue=total_revenue)

@app.route('/profile')
def profile():
    if 'user_id' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.business_name, m.phone, m.profile_pic
        FROM users u JOIN manager_profiles m ON u.id = m.user_id WHERE u.id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user_data)

from flask import send_from_directory
@app.route('/uploads/<filename>')
def uploaded_file(filename): return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session: return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        business_name = request.form.get('business_name')
        file = request.files.get('profile_pic')
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, session['user_id']))
        if file and file.filename != '':
            filename = secure_filename(f"pp_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE manager_profiles SET business_name = ?, profile_pic = ? WHERE user_id = ?", (business_name, filename, session['user_id']))
        else:
            conn.execute("UPDATE manager_profiles SET business_name = ? WHERE user_id = ?", (business_name, session['user_id']))
        conn.commit()
        session['user_name'] = full_name
        flash("Profile updated successfully!")
        return redirect(url_for('edit_profile'))
    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.business_name, m.phone, m.profile_pic 
        FROM users u JOIN manager_profiles m ON u.id = m.user_id WHERE u.id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user_data)

# 🟢 UPDATED: Portfolio Route captures all 3 packages
@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'user_id' not in session or session['role'] != 'eventmanager': return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        category = ", ".join(request.form.getlist('category'))
        service_name = request.form.get('service_name')
        service_location = request.form.get('service_location')
        services_offered = request.form.get('services_offered')
        experience_years = request.form.get('experience_years')
        description = request.form.get('description')
        unavailable_dates = request.form.get('unavailable_dates')
        pricing_amount = request.form.get('pricing_amount')
        pricing_unit = request.form.get('pricing_unit')
        combined_pricing = f"{pricing_amount} {pricing_unit}"
        
        # 🟢 Package Info
        pkg_basic_name = request.form.get('pkg_basic_name', 'Basic (Silver)')
        pkg_basic_price = request.form.get('pkg_basic_price', 0)
        pkg_basic_desc = request.form.get('pkg_basic_desc', '')
        pkg_premium_name = request.form.get('pkg_premium_name', 'Premium (Gold)')
        pkg_premium_price = request.form.get('pkg_premium_price', 0)
        pkg_premium_desc = request.form.get('pkg_premium_desc', '')
        pkg_luxury_name = request.form.get('pkg_luxury_name', 'Luxury (Platinum)')
        pkg_luxury_price = request.form.get('pkg_luxury_price', 0)
        pkg_luxury_desc = request.form.get('pkg_luxury_desc', '')
        
        uploaded_images = request.files.getlist('event_images')
        image_filenames = []
        for file in uploaded_images:
            if file and file.filename != '':
                filename = secure_filename(f"port_{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filenames.append(filename)
                
        images_str = ",".join(image_filenames)
        
        conn.execute('''
            INSERT INTO services (
                manager_id, category, service_name, service_location, 
                services_offered, experience_years, pricing, images, description, unavailable_dates,
                pkg_basic_name, pkg_basic_price, pkg_basic_desc,
                pkg_premium_name, pkg_premium_price, pkg_premium_desc,
                pkg_luxury_name, pkg_luxury_price, pkg_luxury_desc
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], category, service_name, service_location, services_offered, 
              experience_years, combined_pricing, images_str, description, unavailable_dates,
              pkg_basic_name, pkg_basic_price, pkg_basic_desc,
              pkg_premium_name, pkg_premium_price, pkg_premium_desc,
              pkg_luxury_name, pkg_luxury_price, pkg_luxury_desc))
        conn.commit()
        flash("Portfolio item added successfully!")
        return redirect(url_for('portfolio'))

    my_services = conn.execute("SELECT * FROM services WHERE manager_id = ?", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('portfolio.html', services=my_services)

# 🟢 UPDATED: Edit Portfolio handles all 3 packages
@app.route('/edit_portfolio/<int:service_id>', methods=['POST'])
def edit_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager': return redirect(url_for('index'))
    conn = get_db_connection()
    service = conn.execute("SELECT * FROM services WHERE id = ? AND manager_id = ?", (service_id, session['user_id'])).fetchone()
    if not service:
        flash("Unauthorized action.")
        return redirect(url_for('portfolio'))

    category = ", ".join(request.form.getlist('category'))
    service_name = request.form.get('service_name')
    service_location = request.form.get('service_location')
    services_offered = request.form.get('services_offered')
    experience_years = request.form.get('experience_years')
    description = request.form.get('description')
    unavailable_dates = request.form.get('unavailable_dates')
    pricing_amount = request.form.get('pricing_amount')
    pricing_unit = request.form.get('pricing_unit')
    combined_pricing = f"{pricing_amount} {pricing_unit}"
    
    # 🟢 Package Info Update
    pkg_basic_name = request.form.get('pkg_basic_name', 'Basic (Silver)')
    pkg_basic_price = request.form.get('pkg_basic_price', 0)
    pkg_basic_desc = request.form.get('pkg_basic_desc', '')
    pkg_premium_name = request.form.get('pkg_premium_name', 'Premium (Gold)')
    pkg_premium_price = request.form.get('pkg_premium_price', 0)
    pkg_premium_desc = request.form.get('pkg_premium_desc', '')
    pkg_luxury_name = request.form.get('pkg_luxury_name', 'Luxury (Platinum)')
    pkg_luxury_price = request.form.get('pkg_luxury_price', 0)
    pkg_luxury_desc = request.form.get('pkg_luxury_desc', '')
    
    current_images = service['images'].split(',') if service['images'] else []
    images_to_delete = request.form.getlist('delete_images')
    updated_images = [img for img in current_images if img not in images_to_delete]
    
    uploaded_images = request.files.getlist('event_images')
    for file in uploaded_images:
        if file and file.filename != '':
            filename = secure_filename(f"port_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            updated_images.append(filename)
            
    images_str = ",".join(updated_images)
    
    conn.execute('''
        UPDATE services SET category=?, service_name=?, service_location=?, 
        services_offered=?, experience_years=?, pricing=?, description=?, images=?, unavailable_dates=?,
        pkg_basic_name=?, pkg_basic_price=?, pkg_basic_desc=?,
        pkg_premium_name=?, pkg_premium_price=?, pkg_premium_desc=?,
        pkg_luxury_name=?, pkg_luxury_price=?, pkg_luxury_desc=?
        WHERE id=? AND manager_id=?
    ''', (category, service_name, service_location, services_offered, experience_years, combined_pricing, 
          description, images_str, unavailable_dates, 
          pkg_basic_name, pkg_basic_price, pkg_basic_desc,
          pkg_premium_name, pkg_premium_price, pkg_premium_desc,
          pkg_luxury_name, pkg_luxury_price, pkg_luxury_desc,
          service_id, session['user_id']))

    conn.commit()
    conn.close()
    flash("Portfolio item updated successfully!")
    return redirect(url_for('portfolio'))

@app.route('/delete_portfolio/<int:service_id>', methods=['POST'])
def delete_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager': return redirect(url_for('index'))
    conn = get_db_connection()
    service = conn.execute("SELECT images FROM services WHERE id = ? AND manager_id = ?", (service_id, session['user_id'])).fetchone()
    if service:
        conn.execute("DELETE FROM services WHERE id = ? AND manager_id = ?", (service_id, session['user_id']))
        conn.commit()
        if service['images']:
            for img in service['images'].split(','):
                if img.strip():
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img.strip())
                    if os.path.exists(img_path): os.remove(img_path)
        flash("Portfolio item deleted successfully!")
    else: flash("Unauthorized action or item not found.")
    conn.close()
    return redirect(url_for('portfolio'))

@app.route('/explore')
def explore():
    if 'user_id' not in session or session['role'] != 'user': return redirect(url_for('index'))
    conn = get_db_connection()
    all_services = conn.execute('SELECT s.*, m.business_name, m.profile_pic FROM services s JOIN manager_profiles m ON s.manager_id = m.user_id').fetchall()
    conn.close()
    return render_template('explore.html', services=all_services)

@app.route('/vendor_details/<int:service_id>')
def vendor_details(service_id):
    if 'user_id' not in session or session['role'] != 'user': return redirect(url_for('index'))
    conn = get_db_connection()
    service = conn.execute('''
        SELECT s.*, m.business_name, m.phone, u.full_name as manager_name 
        FROM services s JOIN manager_profiles m ON s.manager_id = m.user_id JOIN users u ON m.user_id = u.id WHERE s.id = ?
    ''', (service_id,)).fetchone()
    
    if not service:
        conn.close()
        flash("Vendor not found.")
        return redirect(url_for('explore'))
        
    active_bookings = conn.execute("SELECT event_date FROM bookings WHERE service_id = ? AND status IN ('pending', 'confirmed')", (service_id,)).fetchall()
    conn.close()
    
    service_dict = dict(service)
    blocked_dates = []
    if service_dict['unavailable_dates']:
        blocked_dates.extend([d.strip() for d in service_dict['unavailable_dates'].split(',') if d.strip()])
    for b in active_bookings:
        if b['event_date']:
            blocked_dates.extend([d.strip() for d in b['event_date'].split(',') if d.strip()])
    service_dict['unavailable_dates'] = ", ".join(list(set(blocked_dates)))

    return render_template('vendors_details.html', service=service_dict)

# 🟢 UPDATED: Saves the selected package directly into the database
@app.route('/book_vendor', methods=['POST'])
def book_vendor():
    if 'user_id' not in session or session['role'] != 'user': return redirect(url_for('index'))
    manager_id = request.form.get('manager_id')
    service_id = request.form.get('service_id')
    event_date = request.form.get('event_date')
    client_phone = request.form.get('client_phone')
    client_message = request.form.get('client_message')
    notify_email = request.form.get('notify_email')
    
    total_amount = request.form.get('total_amount', 0)
    selected_package = request.form.get('selected_package', 'Custom') 
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO bookings (client_id, manager_id, service_id, event_date, status, client_phone, client_message, total_amount, selected_package)
        VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?)
    ''', (session['user_id'], manager_id, service_id, event_date, client_phone, client_message, total_amount, selected_package))
    conn.commit()

    if notify_email == 'on':
        manager = conn.execute("SELECT u.email, u.full_name, s.service_name FROM users u JOIN services s ON u.id = s.manager_id WHERE s.id = ?", (service_id,)).fetchone()
        client = conn.execute("SELECT email FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if manager and client:
            send_booking_email(manager['email'], manager['full_name'], session['user_name'], client['email'], client_phone, event_date, manager['service_name'], client_message, selected_package)

    conn.close()
    flash("Booking Request Sent Successfully!")
    return redirect(url_for('user_dashboard'))

@app.route('/view_booking/<int:booking_id>')
def view_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'eventmanager': return redirect(url_for('index'))
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, u.full_name as client_name, u.email as client_email,
               s.service_name, s.category, s.pricing, s.images
        FROM bookings b JOIN users u ON b.client_id = u.id LEFT JOIN services s ON b.service_id = s.id
        WHERE b.id = ? AND b.manager_id = ?
    ''', (booking_id, session['user_id'])).fetchone()
    conn.close()

    if not booking:
        flash("Booking not found or unauthorized.")
        return redirect(url_for('dashboard'))

    return render_template('view_booking.html', booking=booking)

@app.route('/update_booking/<int:booking_id>/<action>', methods=['POST'])
def update_booking(booking_id, action):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, u.email as client_email, u.full_name as client_name, 
               m.business_name, s.service_name 
        FROM bookings b JOIN users u ON b.client_id = u.id JOIN manager_profiles m ON b.manager_id = m.user_id LEFT JOIN services s ON b.service_id = s.id 
        WHERE b.id = ? AND b.manager_id = ?
    ''', (booking_id, session['user_id'])).fetchone()
    
    if booking:
        new_status = 'confirmed' if action == 'approve' else 'rejected'
        conn.execute('UPDATE bookings SET status = ? WHERE id = ?', (new_status, booking_id))
        
        if new_status == 'confirmed' and booking['service_id']:
            svc = conn.execute('SELECT unavailable_dates FROM services WHERE id = ?', (booking['service_id'],)).fetchone()
            existing_dates = svc['unavailable_dates'] if svc and svc['unavailable_dates'] else ""
            new_dates_list = [d.strip() for d in booking['event_date'].split(',') if d.strip()]
            
            if existing_dates:
                existing_list = [d.strip() for d in existing_dates.split(',') if d.strip()]
                updated_dates_str = ", ".join(list(set(existing_list + new_dates_list)))
            else:
                updated_dates_str = ", ".join(new_dates_list)
            conn.execute('UPDATE services SET unavailable_dates = ? WHERE id = ?', (updated_dates_str, booking['service_id']))
        conn.commit()
        
        service_name = booking['service_name'] if booking['service_name'] else 'Custom Package'
        send_status_email(booking['client_email'], booking['client_name'], booking['business_name'], service_name, booking['event_date'], new_status)
        flash(f"Booking successfully {new_status}!")
    
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)