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

@auth.route('/account')
def account():
    if 'user_id' not in session:
        flash('Please login first.', 'danger')
        return redirect(url_for('auth.login'))
    from models import User
    user = User.query.get(session['user_id'])
    return render_template('auth/profile.html', user=user)


@auth.route('/account/update-profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from models import User
    user = User.query.get(session['user_id'])
    user.name     = request.form.get('name', user.name).strip()
    user.email    = request.form.get('email', user.email).strip()
    user.phone    = request.form.get('phone', '').strip()
    user.location = request.form.get('location', '').strip()
    db.session.commit()
    session['user_name'] = user.name
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('auth.account'))


@auth.route('/account/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from models import User
    user = User.query.get(session['user_id'])
    current_pw  = request.form.get('current_password', '')
    new_pw      = request.form.get('new_password', '')
    confirm_pw  = request.form.get('confirm_password', '')

    if not bcrypt.check_password_hash(user.password, current_pw):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('auth.account') + '#password')
    if len(new_pw) < 6:
        flash('New password must be at least 6 characters.', 'danger')
        return redirect(url_for('auth.account') + '#password')
    if new_pw != confirm_pw:
        flash('New passwords do not match.', 'danger')
        return redirect(url_for('auth.account') + '#password')

    user.password = bcrypt.generate_password_hash(new_pw).decode('utf-8')
    db.session.commit()
    flash('Password changed successfully!', 'success')
    return redirect(url_for('auth.account'))