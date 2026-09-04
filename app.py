## -------- Headers ----------- ##

import os
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, redirect, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt


## ------------ linking librabry and databse ---------##
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///complaintportal.db'
app.config['SECRET_KEY'] = 'complaintportal_secret_key'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

## --------- UserDatase ------------------##


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')

## ---------- ComplaintDatabase -------------##


class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(50), default='Pending')
    priority = db.Column(db.String(20), default='Normal')
    assigned_worker_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

## ---------- Feedback -------------##


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey(
        'complaint.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.now())

## --------- Home Page ---------##


@app.route('/')
def home():
    return render_template('home.html')

## --------- About Page ---------##


@app.route('/about')
def about():
    return "ComplaintPortal helps students report and track campus maintenance issues."

## --------- Login Page ---------##


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

    return render_template('login.html')

## --------- Register Page--------##

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # College email check
        if not email.endswith('@acem.edu.in'):
            return render_template('register.html', error='Only ACEM college email addresses (@acem.edu.in) are allowed.')

        # Password length check
        if len(password) < 8:
            return render_template('register.html', error='Password must be at least 8 characters long.')

        # Duplicate email check
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error='An account with this email already exists.')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html', error=None)

## -----------Dashboard-----------##


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    role = session.get('user_role')
    
    if role == 'admin':
        return redirect('/admin/dashboard')
    elif role == 'worker':
        return redirect('/worker/dashboard')
    else:
        return redirect('/')

## ----------- StudentDashboard ----------##


@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'student':
        return redirect('/dashboard')
    return render_template('student_dashboard.html')

## ----------- AdminDashboard ----------##


@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')

    results = db.session.query(Complaint, User.name).join(
        User, Complaint.user_id == User.id
    ).all()
    return render_template('admin_dashboard.html', complaints=results)

## ---------------- WorkerDashboard ------------------##


@app.route('/worker/dashboard')
def worker_dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'worker':
        return redirect('/dashboard')

    assigned_complaints = Complaint.query.filter_by(
        assigned_worker_id=session['user_id']
    ).all()

    return render_template('worker_dashboard.html', complaints=assigned_complaints)

## ------------ Logout ----------------##


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

## ------------ ComplaintSubmit ----------##


@app.route('/submit-complaint', methods=['GET', 'POST'])
def submit_complaint():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'student':
        return redirect('/dashboard')

    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        location = request.form['location']
        description = request.form['description']

        photo = request.files['photo']
        photo_filename = None
        if photo and photo.filename != '':
            photo_filename = photo.filename
            photo.save(os.path.join('static/uploads', photo_filename))

        new_complaint = Complaint(
            user_id=session['user_id'],
            title=title,
            category=category,
            location=location,
            description=description,
            photo=photo_filename
        )
        db.session.add(new_complaint)
        db.session.commit()

        return redirect('/my-complaints')

    return render_template('submit_complaint.html')

## -------------- StudentComplaint ------------##


@app.route('/my-complaints')
def my_complaints():
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'student':
        return redirect('/dashboard')

    complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('my_complaints.html', complaints=complaints)

## ------------- AdminComplaintRoute --------------##


@app.route('/admin/complaint/<int:complaint_id>', methods=['GET', 'POST'])
def manage_complaint(complaint_id):
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'admin':
        return redirect('/dashboard')

    complaint = Complaint.query.get_or_404(complaint_id)
    workers = User.query.filter_by(role='worker').all()

    if request.method == 'POST':
        complaint.priority = request.form['priority']
        complaint.status = request.form['status']
        worker_id = request.form['worker_id']
        if worker_id:
            complaint.assigned_worker_id = int(worker_id)
        db.session.commit()
        return redirect('/admin/dashboard')

    return render_template('manage_complaint.html', complaint=complaint, workers=workers)


## --------------- WorkeDashboardRoute ---------------##

@app.route('/worker/complaint/<int:complaint_id>', methods=['GET', 'POST'])
def worker_complaint(complaint_id):
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'worker':
        return redirect('/dashboard')

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.assigned_worker_id != session['user_id']:
        return redirect('/worker/dashboard')

    if request.method == 'POST':
        complaint.status = request.form['status']
        db.session.commit()
        return redirect('/worker/dashboard')

    return render_template('worker_complaint.html', complaint=complaint)

##----------------- FeedbackRoute ------------------##
@app.route('/feedback/<int:complaint_id>', methods=['GET', 'POST'])
def feedback(complaint_id):
    if 'user_id' not in session:
        return redirect('/login')
    if session.get('user_role') != 'student':
        return redirect('/dashboard')

    complaint = Complaint.query.get_or_404(complaint_id)

    if complaint.user_id != session['user_id']:
        return redirect('/my-complaints')

    if complaint.status != 'Resolved':
        return "This complaint is not resolved yet. <a href='/my-complaints'>Go back</a>"

    existing_feedback = Feedback.query.filter_by(
        complaint_id=complaint_id,
        user_id=session['user_id']
    ).first()

    if existing_feedback:
        return "You have already submitted feedback for this complaint. <a href='/my-complaints'>Go back</a>"

    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']

        new_feedback = Feedback(
            complaint_id=complaint_id,
            user_id=session['user_id'],
            rating=rating,
            comment=comment
        )
        db.session.add(new_feedback)

        complaint.status = 'Closed'
        db.session.commit()

        return redirect('/my-complaints')

    return render_template('feedback.html', complaint=complaint)


if __name__ == '__main__':
    app.run(debug=True)
