from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import timedelta  # 🟢 NEW: Required for setting login duration

# UPDATED: Flask now points to your custom folder structure
app = Flask(__name__, 
            template_folder='frontend/templates', 
            static_folder='frontend/static')

app.secret_key = 'evenzo_secret_key_123'  # Required for sessions
app.config['UPLOAD_FOLDER'] = 'uploads'

# 🟢 NEW: Keep users logged in for 30 days (even if they close the browser)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) 

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

# --- MAIN PAGE ---
@app.route('/')
def index():
    return render_template('index.html')

# --- SERVICE PAGES ---
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

# --- REGISTRATION LOGIC ---
@app.route('/register', methods=['POST'])
def register():
    role = request.form.get('regUserRole')
    full_name = request.form.get('regFullName')
    email = request.form.get('regEmail')
    password = request.form.get('regPass')

    conn = get_db_connection()
    try:
        # 1. Insert into Users table
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (full_name, email, password, role, is_approved) VALUES (?, ?, ?, ?, ?)",
            (full_name, email, password, role, 1 if role == 'user' else 0)
        )
        user_id = cursor.lastrowid

        # 2. If Event Manager, handle extra fields and license
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

# --- LOGIN LOGIC ---
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
        # 🟢 NEW: This tells Flask to apply the 30-day lifetime to this session
        session.permanent = True 
        
        session['user_id'] = user['id']
        session['user_name'] = user['full_name']
        session['role'] = user['role']

        # REDIRECT BASED ON ROLE
        if user['role'] == 'eventmanager':
            return redirect(url_for('dashboard'))
        elif user['role'] == 'user':
            return redirect(url_for('user_dashboard')) # Redirects Clients to user dashboard
        return redirect(url_for('index'))
    else:
        flash("Invalid Credentials or Role.")
        return redirect(url_for('index'))


# --- USER (CLIENT) DASHBOARD ROUTE ---
@app.route('/user_dashboard')
def user_dashboard():
    # Security: Ensure only logged-in users can access this page
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    conn = get_db_connection()
    
    # Fetch User details
    user_info = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    # Fetch User's bookings & join with the manager profiles to get business names
    my_bookings = conn.execute('''
        SELECT b.*, m.business_name, s.service_name 
        FROM bookings b 
        JOIN manager_profiles m ON b.manager_id = m.user_id 
        LEFT JOIN services s ON b.service_id = s.id
        WHERE b.client_id = ?
    ''', (session['user_id'],)).fetchall()
    
    conn.close()

    return render_template('user_dashboard.html', user=user_info, bookings=my_bookings)

# --- SPECIFIC DASHBOARD LOGIC ---
# --- DYNAMIC DASHBOARD ROUTE ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

    conn = get_db_connection()
    
    # Fetch specific Manager Profile
    profile = conn.execute(
        "SELECT * FROM manager_profiles WHERE user_id = ?", 
        (session['user_id'],)
    ).fetchone()
    
    # Fetch specific Bookings for this manager
    # We join with the users table to get the Client's Name
    bookings = conn.execute('''
        SELECT b.*, u.full_name as client_name 
        FROM bookings b 
        JOIN users u ON b.client_id = u.id 
        WHERE b.manager_id = ?
    ''', (session['user_id'],)).fetchall()
    
    # Calculate Dynamic Stats
    total_bookings = len(bookings)
    pending_count = sum(1 for b in bookings if b['status'] == 'pending')
    total_revenue = sum(b['total_amount'] for b in bookings if b['payment_status'] == 'paid')

    conn.close()

    return render_template('dashboard.html', 
                           profile=profile, 
                           bookings=bookings, 
                           total_bookings=total_bookings,
                           pending_count=pending_count,
                           total_revenue=total_revenue)

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

# Helper to serve uploaded files (images/licenses)
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

        # Update Users table (email is not editable here)
        conn.execute("UPDATE users SET full_name = ? WHERE id = ?",
                     (full_name, session['user_id']))
        
        # Handle Profile Pic Upload
        if file and file.filename != '':
            filename = secure_filename(f"pp_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            conn.execute("UPDATE manager_profiles SET business_name = ?, profile_pic = ? WHERE user_id = ?",
                         (business_name, filename, session['user_id']))
        else:
            conn.execute("UPDATE manager_profiles SET business_name = ? WHERE user_id = ?",
                         (business_name, session['user_id']))
            
        conn.commit()
        session['user_name'] = full_name # Update displayed name in session
        flash("Profile updated successfully!")
        return redirect(url_for('edit_profile'))

    # GET logic: Fetch existing data
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
        # 🟢 UPDATED: Grabs multiple categories and joins them with a comma
        category = ", ".join(request.form.getlist('category'))
        
        service_name = request.form.get('service_name')
        service_location = request.form.get('service_location')
        services_offered = request.form.get('services_offered')
        experience_years = request.form.get('experience_years')
        description = request.form.get('description')
        
        # --- COMBINE AMOUNT AND UNIT ---
        pricing_amount = request.form.get('pricing_amount')
        pricing_unit = request.form.get('pricing_unit')
        combined_pricing = f"{pricing_amount} {pricing_unit}"
        
        # Handle multiple event images
        uploaded_images = request.files.getlist('event_images')
        image_filenames = []
        
        for file in uploaded_images:
            if file and file.filename != '':
                filename = secure_filename(f"port_{session['user_id']}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_filenames.append(filename)
                
        # Join filenames with a comma to save in a single database column
        images_str = ",".join(image_filenames)
        
        conn.execute('''
            INSERT INTO services (
                manager_id, category, service_name, service_location, 
                services_offered, experience_years, pricing, images, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session['user_id'], category, service_name, service_location, 
              services_offered, experience_years, combined_pricing, images_str, description))
        
        conn.commit()
        flash("Portfolio item added successfully!")
        return redirect(url_for('portfolio'))

    my_services = conn.execute(
        "SELECT * FROM services WHERE manager_id = ?",
        (session['user_id'],)
    ).fetchall()
    
    conn.close()
    return render_template('portfolio.html', services=my_services)

@app.route('/edit_portfolio/<int:service_id>', methods=['POST'])
def edit_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

    conn = get_db_connection()
    service = conn.execute("SELECT * FROM services WHERE id = ? AND manager_id = ?", 
                           (service_id, session['user_id'])).fetchone()
                           
    if not service:
        flash("Unauthorized action.")
        return redirect(url_for('portfolio'))

    # Get standard text fields
    # 🟢 UPDATED: Grabs multiple categories and joins them with a comma
    category = ", ".join(request.form.getlist('category'))
    
    service_name = request.form.get('service_name')
    service_location = request.form.get('service_location')
    services_offered = request.form.get('services_offered')
    experience_years = request.form.get('experience_years')
    description = request.form.get('description')
    
    # --- COMBINE AMOUNT AND UNIT ---
    pricing_amount = request.form.get('pricing_amount')
    pricing_unit = request.form.get('pricing_unit')
    combined_pricing = f"{pricing_amount} {pricing_unit}"
    
    # --- IMAGE HANDLING LOGIC ---
    # 1. Get current images
    current_images = service['images'].split(',') if service['images'] else []
    
    # 2. Get list of images the user checked to delete
    images_to_delete = request.form.getlist('delete_images')
    
    # 3. Filter out the deleted images
    updated_images = [img for img in current_images if img not in images_to_delete]
    
    # 4. Handle NEW image uploads and add them to the list
    uploaded_images = request.files.getlist('event_images')
    for file in uploaded_images:
        if file and file.filename != '':
            filename = secure_filename(f"port_{session['user_id']}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            updated_images.append(filename)
            
    # Join the final list back into a string
    images_str = ",".join(updated_images)
    
    # Update the database
    conn.execute('''
        UPDATE services SET category=?, service_name=?, service_location=?, 
        services_offered=?, experience_years=?, pricing=?, description=?, images=?
        WHERE id=? AND manager_id=?
    ''', (category, service_name, service_location, services_offered, experience_years, 
          combined_pricing, description, images_str, service_id, session['user_id']))

    conn.commit()
    conn.close()
    flash("Portfolio item updated successfully!")
    return redirect(url_for('portfolio'))

# --- DELETE PORTFOLIO ROUTE ---
@app.route('/delete_portfolio/<int:service_id>', methods=['POST'])
def delete_portfolio(service_id):
    if 'user_id' not in session or session['role'] != 'eventmanager':
        return redirect(url_for('index'))

    conn = get_db_connection()
    
    # Fetch the service to get the image filenames before deleting
    service = conn.execute("SELECT images FROM services WHERE id = ? AND manager_id = ?", 
                           (service_id, session['user_id'])).fetchone()
                           
    if service:
        # Delete the record from the database
        conn.execute("DELETE FROM services WHERE id = ? AND manager_id = ?", 
                     (service_id, session['user_id']))
        conn.commit()
        
        # Clean up the images from the uploads folder
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


# --- EXPLORE / FIND VENDORS PAGE ---
@app.route('/explore')
def explore():
    # Ensure only users (clients) can access the explore page
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    conn = get_db_connection()
    
    # Fetch ALL dynamic services combined with the Event Manager's Business Name
    all_services = conn.execute('''
        SELECT s.*, m.business_name, m.profile_pic 
        FROM services s
        JOIN manager_profiles m ON s.manager_id = m.user_id
    ''').fetchall()
    
    conn.close()
    
    return render_template('explore.html', services=all_services)

# --- BOOK VENDOR LOGIC ---
@app.route('/book_vendor', methods=['POST'])
def book_vendor():
    if 'user_id' not in session or session['role'] != 'user':
        return redirect(url_for('index'))

    manager_id = request.form.get('manager_id')
    service_id = request.form.get('service_id')
    event_date = request.form.get('event_date')
    
    conn = get_db_connection()
    
    # Insert a new pending booking into the database
    conn.execute('''
        INSERT INTO bookings (client_id, manager_id, service_id, event_date, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (session['user_id'], manager_id, service_id, event_date))
    
    conn.commit()
    conn.close()
    
    flash("Booking Request Sent Successfully!")
    return redirect(url_for('user_dashboard'))

# --- LOGOUT ---
@app.route('/logout')
def logout():
    session.clear() # This explicitly destroys the permanent session!
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)