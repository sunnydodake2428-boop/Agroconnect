from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from extensions import db
from models import Product, Order
import os
from werkzeug.utils import secure_filename

farmer = Blueprint('farmer', __name__)

def farmer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'farmer':
            flash('Please login as farmer.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@farmer.route('/farmer/dashboard')
@farmer_required
def dashboard():
    farmer_id = session['user_id']
    listings = Product.query.filter_by(farmer_id=farmer_id).all()
    orders = Order.query.filter_by(farmer_id=farmer_id).order_by(Order.created_at.desc()).all()
    total_earnings = sum(o.total_price for o in orders if o.status == 'delivered') or 0
    return render_template('farmer/dashboard.html',
                         listings=listings,
                         orders=orders,
                         total_earnings=total_earnings)


@farmer.route('/farmer/add-listing', methods=['GET', 'POST'])
@farmer_required
def add_listing():
    if request.method == 'POST':
        image = 'default.jpg'
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                upload_path = os.path.join(current_app.root_path, 'static', 'images')
                os.makedirs(upload_path, exist_ok=True)
                file.save(os.path.join(upload_path, filename))
                image = filename

        product = Product(
            farmer_id=session['user_id'],
            crop_name=request.form['crop_name'],
            category=request.form['category'],
            quantity=float(request.form['quantity']),
            unit=request.form['unit'],
            price=float(request.form['price']),
            description=request.form['description'],
            image=image
        )
        db.session.add(product)
        db.session.commit()
        flash('Crop listed successfully!', 'success')
        return redirect(url_for('farmer.dashboard'))

    return render_template('farmer/add_listing.html')


@farmer.route('/farmer/update-order/<int:order_id>/<status>')
@farmer_required
def update_order(order_id, status):
    order = Order.query.get(order_id)
    if order:
        order.status = status
        db.session.commit()
        flash(f'Order updated to {status}!', 'success')
    return redirect(url_for('farmer.dashboard'))