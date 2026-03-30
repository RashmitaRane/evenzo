from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import timedelta

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
    user = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password = ? AND role = ?",
        (email, password, role_requested)
    ).fetchone()
    conn.close()

    if user:
        session.permanent = True 
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']

        if user['role'] == 'eventmanager':
            return redirect(url_for('dashboard'))
        elif user['role'] == 'user':
            return redirect(url_for('user_dashboard'))
        return redirect(url_for('index'))
    else:
        flash("Invalid Credentials or Role.")
        return redirect(url_for('index'))

@app.route('/user_dashboard')
def user_dashboard():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    conn = get_db_connection()
    user_info = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # 🟢 Uses s.pricing to correctly show vendor price
    my_bookings = conn.execute('''
        SELECT b.*, m.business_name, s.service_name, s.pricing 
        FROM bookings b 
        JOIN manager_profiles m ON b.manager_id = m.user_id 
        LEFT JOIN services s ON b.service_id = s.id
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
        FROM bookings b 
        JOIN users u ON b.client_id = u.id 
        WHERE b.manager_id = ?
    ''', (session['user_id'],)).fetchall()
    
    total_bookings = len(bookings)
    pending_count = sum(1 for b in bookings if b['status'] == 'pending')
    total_revenue = sum(b['total_amount'] for b in bookings if b['payment_status'] == 'paid')
    conn.close()

    return render_template('dashboard.html', profile=profile, bookings=bookings, total_bookings=total_bookings, pending_count=pending_count, total_revenue=total_revenue)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.business_name, m.phone, m.profile_pic
        FROM users u
        JOIN manager_profiles m ON u.id = m.user_id
        WHERE u.id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user_data)

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    conn = get_db_connection()
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        business_name = request.form.get('business_name')
        file = request.files.get('profile_pic')

        conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, session['user_id']))
        
        if file and file.filename != '':
            filename = secure_filename(f"pp_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE manager_profiles SET business_name = ?, profile_pic = ? WHERE user_id = ?",
                         (business_name, filename, session['user_id']))
        else:
            conn.execute("UPDATE manager_profiles SET business_name = ? WHERE user_id = ?",
                         (business_name, session['user_id']))
            
        conn.commit()
        session['user_name'] = full_name
        flash("Profile updated successfully!")
        return redirect(url_for('edit_profile'))

    user_data = conn.execute('''
        SELECT u.full_name, u.email, m.business_name, m.phone, m.profile_pic 
        FROM users u 
        JOIN manager_profiles m ON u.id = m.user_id 
        WHERE u.id = ?
    ''', (session['user_id'],)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user_data)


@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

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
                services_offered, experience_years, pricing, images, description, unavailable_dates
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], category, service_name, service_location, 
              services_offered, experience_years, combined_pricing, images_str, description, unavailable_dates))
        
        conn.commit()
        flash("Portfolio item added successfully!")
        return redirect(url_for('portfolio'))

    my_services = conn.execute("SELECT * FROM services WHERE manager_id = ?", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('portfolio.html', services=my_services)

@app.route('/edit_portfolio/<int:service_id>', methods=['POST'])
def edit_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

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
        services_offered=?, experience_years=?, pricing=?, description=?, images=?, unavailable_dates=?
        WHERE id=? AND manager_id=?
    ''', (category, service_name, service_location, services_offered, experience_years, 
          combined_pricing, description, images_str, unavailable_dates, service_id, session['user_id']))

    conn.commit()
    conn.close()
    flash("Portfolio item updated successfully!")
    return redirect(url_for('portfolio'))

@app.route('/delete_portfolio/<int:service_id>', methods=['POST'])
def delete_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

    conn = get_db_connection()
    service = conn.execute("SELECT images FROM services WHERE id = ? AND manager_id = ?", (service_id, session['user_id'])).fetchone()
                           
    if service:
        conn.execute("DELETE FROM services WHERE id = ? AND manager_id = ?", (service_id, session['user_id']))
        conn.commit()
        if service['images']:
            for img in service['images'].split(','):
                if img.strip():
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img.strip())
                    if os.path.exists(img_path):
                        os.remove(img_path)
        flash("Portfolio item deleted successfully!")
    else:
        flash("Unauthorized action or item not found.")
        
    conn.close()
    return redirect(url_for('portfolio'))

@app.route('/explore')
def explore():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    conn = get_db_connection()
    all_services = conn.execute('''
        SELECT s.*, m.business_name, m.profile_pic 
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
    ''').fetchall()
    conn.close()
    return render_template('explore.html', services=all_services)

@app.route('/vendor_details/<int:service_id>')
def vendor_details(service_id):
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    conn = get_db_connection()
    service = conn.execute('''
        SELECT s.*, m.business_name, m.phone, u.full_name as manager_name 
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
        JOIN users u ON m.user_id = u.id
        WHERE s.id = ?
    ''', (service_id,)).fetchone()
    conn.close()

    if not service:
        flash("Vendor not found.")
        return redirect(url_for('explore'))

    return render_template('vendors_details.html', service=service)


@app.route('/book_vendor', methods=['POST'])
def book_vendor():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    manager_id = request.form.get('manager_id')
    service_id = request.form.get('service_id')
    event_date = request.form.get('event_date')
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO bookings (client_id, manager_id, service_id, event_date, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (session['user_id'], manager_id, service_id, event_date))
    
    conn.commit()
    conn.close()
    
    flash("Booking Request Sent Successfully!")
    return redirect(url_for('user_dashboard'))

@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)