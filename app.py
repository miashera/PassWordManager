from flask import Flask, render_template, request, flash, redirect, url_for, session , make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
import zxcvbn
from cryptography.fernet import Fernet
import secrets
import string
from flask import jsonify
from twilio.rest import Client
from flask_migrate import Migrate
from datetime import datetime
from database import User,db
import random
from report_generator import generate_files_report, generate_users_report


app = Flask(__name__)

app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///password_manager.db'

db.init_app(app)


# Initialize Fernet encryption
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Password strength checker (using zxcvbn for more robust strength checking)
def check_password_strength(password):
    result = zxcvbn(password)
    return result['score'], result['feedback']

# Password generator
def generate_password():
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for i in range(12))
    return password

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        role = request.form.get('role')
        regno = request.form.get('regno')

        # Check if a user with the given username or registration number already exists
        existing_user = User.query.filter((User.username == username) | (User.REGNO == regno)).first()

        if existing_user:
            flash('Username or Registration Number already exists. Please choose a different one.', 'danger')
            return render_template('register.html')

        # Create a new user and add to the database
        new_user = User(username=username, password=hashed_password, role=role, REGNO=regno, created_at=datetime.today(),is_approved="False")

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for(("login")))
            flash('Your account has been created!', 'success')
        except IntegrityError:
            # Handle integrity errors (e.g., unique constraint violation)
            db.session.rollback()
            flash('Error creating account. Please try again.', 'danger')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        regno = request.form.get('regno')
        password = request.form.get('password')
        user = User.query.filter(User.REGNO == regno).first()
    
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # <SecureCookieSession {'user_id': 20}>
            if user.role == 'faculty':
                #print(f'Fucking Shit: {user.role}')
                return redirect(url_for('faculty_dashboard'))
            elif user.role == 'student':
                print(f'Fucking Shit: {user.role}')
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))
                print(f'Fucking Shit: {user.role}')
                session.pop('_flashes', None)
        else:
            flash(f'Login failed.', 'danger')

    return render_template('login.html')

@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user.role == 'faculty':
            return render_template('faculty_dashboard.html')
    
    flash('Unauthorized access', 'danger')
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' in session:
        user = session.get('user_id')
        if user:
            return render_template('admin_dashboard.html')
    flash('Unauthorized access', 'danger')
    return redirect(url_for('login'))

@app.route('/everyone')
def admin_users():
    return render_template('everyone.html')


@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' in session:
        user = session.get('user_id')
        if user:
            return render_template('student_dashboard.html')
    
    flash('Unauthorized access', 'danger')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.pop('user_id', None)
        flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for("login"))

@app.route('/about')
def about():
    return render_template('about.html')

# REST API Endpoints
@app.route('/generate_password', methods=['POST'])
def gen_pass():
    generated_password = generate_password()
    return jsonify({'generated_password': generated_password})

@app.route('/check_password_strength', methods=['POST'])
def check_password_strength_api():
    password = request.form.get('password_strength')
    result = zxcvbn.zxcvbn(password)
    strength = result['score']  # Password strength score from 0 to 4
    feedback = result['feedback']['suggestions']  # Suggestions for password improvement

    strength_labels = ["Very Weak", "Weak", "Moderate", "Strong", "Very Strong"]
    strength_label = strength_labels[strength]

    return jsonify({'strength': strength_label, 'feedback': feedback})

@app.route('/encrypt_password', methods=['POST'])
def encrypt_password():
    password = request.form.get('password')
    encrypted_password = cipher_suite.encrypt(password.encode())
    return jsonify({'encrypted_password': encrypted_password.decode()})

@app.route('/pending_users', methods=['GET'])
def pending_users():
    pending_users = User.query.filter_by(is_approved="False").all()
    pending_users_details = []
    for user in pending_users:
        user_detail = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'Reg No': user.REGNO,
        }

        pending_users_details.append(user_detail)
        print(f"Fucking pending user details: {pending_users_details}")
    return jsonify(pending_users_details)

@app.route('/approveUser/<int:id>', methods=['POST'])
def approveUser(id):
    if request.method == 'POST':
        user = User.query.get(id)
        if user:
            user.is_approved = "True"
            db.session.commit()
            return jsonify({'message': 'User has been approved.'}), 200

        else:
            return jsonify({'error': 'User not found'}), 404
            
    return jsonify({'error': 'Invalid request method!'}), 405


@app.route('/decrypt_password', methods=['POST'])
def decrypt_password():
    encrypted_password = request.form.get('encrypted_password')
    decrypted_password = cipher_suite.decrypt(encrypted_password.encode()).decode()
    return jsonify({'decrypted_password': decrypted_password})

@app.route("/report", methods=["GET","POST"])
def generate_report():
    if request.method == "POST":
        if request.form.get("selected_type") == "users":
            everyone = User.query.all()
            pdf_data = generate_users_report(everyone)
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=users_report.pdf'        
            return response

        elif request.form.get("selected_type") == "students":
            students = User.query.filter_by(role="student").all()
            pdf_data = generate_users_report(students)
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=users_report.pdf'        
            return response

        elif request.form.get("selected_type") == "created_at":
            created_at = User.query.all()
            pdf_data = generate_users_report(created_at)
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=users_report.pdf'        
            return response
        else:
            faculty = User.query.filter_by(role="faculty").all()
            pdf_data = generate_users_report(faculty)
            response = make_response(pdf_data)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename=users_report.pdf'        
            return response
    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
        
