from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from extensions import db, bcrypt
from models import User

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        phone = request.form['phone']
        location = request.form['location']

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email already exists. Try another.', 'danger')
            return render_template('auth/register.html')

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            name=name,
            email=email,
            password=hashed_pw,
            role=role,
            phone=phone,
            location=location
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['user_id'] = user.user_id
            session['user_name'] = user.name
            session['user_role'] = user.role

            if user.role == 'farmer':
                return redirect(url_for('farmer.dashboard'))
            elif user.role == 'buyer':
                return redirect(url_for('buyer.dashboard'))
            else:
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('auth/login.html')


@auth.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))