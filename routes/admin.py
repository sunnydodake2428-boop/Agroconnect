from flask import Blueprint, render_template, session, redirect, url_for, flash
from models import User, Order, Product

admin = Blueprint('admin', __name__)

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'admin':
            flash('Admin access only.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


@admin.route('/admin/dashboard')
@admin_required
def dashboard():
    farmers = User.query.filter_by(role='farmer').count()
    buyers = User.query.filter_by(role='buyer').count()
    total_orders = Order.query.count()
    delivered = Order.query.filter_by(status='delivered').all()
    revenue = sum(o.total_price for o in delivered) or 0
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                         farmers=farmers,
                         buyers=buyers,
                         total_orders=total_orders,
                         revenue=revenue,
                         recent_users=recent_users,
                         recent_orders=recent_orders)