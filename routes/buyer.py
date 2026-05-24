from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from extensions import db
from functools import wraps
from models import Order, Cart, Product, Address, Review
import uuid, hmac, hashlib
from datetime import datetime

buyer = Blueprint('buyer', __name__)

# ─── AUTH GUARD ──────────────────────────────────────────────────────────────
def buyer_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('user_role') != 'buyer':
            flash('Please login as buyer.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@buyer.route('/buyer/dashboard')
@buyer_required
def dashboard():
    buyer_id = session['user_id']
    orders = Order.query.filter_by(buyer_id=buyer_id).order_by(Order.created_at.desc()).all()
    total_spent = sum(o.total_price for o in orders) or 0
    return render_template('buyer/dashboard.html', orders=orders, total_spent=total_spent)


# ─── MARKETPLACE ─────────────────────────────────────────────────────────────
@buyer.route('/marketplace')
def marketplace():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    query = Product.query.filter_by(status='available')
    if search:
        query = query.filter(Product.crop_name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)
    products = query.order_by(Product.created_at.desc()).all()
    return render_template('buyer/marketplace.html', products=products, search=search)


# ─── ADD TO CART ─────────────────────────────────────────────────────────────
@buyer.route('/add-to-cart/<int:product_id>', methods=['POST'])
@buyer_required
def add_to_cart(product_id):
    quantity = float(request.form.get('quantity', 1))
    buyer_id = session['user_id']
    existing = Cart.query.filter_by(buyer_id=buyer_id, product_id=product_id).first()
    if existing:
        existing.quantity += quantity
    else:
        cart_item = Cart(buyer_id=buyer_id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
    db.session.commit()
    flash('Added to cart!', 'success')
    return redirect(url_for('buyer.marketplace'))


# ─── CART ────────────────────────────────────────────────────────────────────
@buyer.route('/cart')
@buyer_required
def cart():
    buyer_id = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    subtotal  = sum(item.product.price * item.quantity for item in cart_items) if cart_items else 0
    mrp_total = sum((item.product.mrp or item.product.price) * item.quantity for item in cart_items) if cart_items else 0
    discount  = mrp_total - subtotal
    delivery  = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))
    coupon    = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    total     = subtotal - coupon_discount + delivery
    return render_template('buyer/cart.html',
        cart_items=cart_items, subtotal=subtotal, mrp_total=mrp_total,
        discount=discount, delivery=delivery, coupon=coupon,
        coupon_discount=coupon_discount, total=total)


# ─── UPDATE CART ─────────────────────────────────────────────────────────────
@buyer.route('/cart/update/<int:item_id>', methods=['POST'])
@buyer_required
def update_cart(item_id):
    item = Cart.query.filter_by(cart_id=item_id, buyer_id=session['user_id']).first_or_404()
    action = request.form.get('action')
    if action == 'increase':
        item.quantity += 1
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
        else:
            db.session.delete(item)
    elif action == 'remove':
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('buyer.cart'))


# ─── COUPON ──────────────────────────────────────────────────────────────────
@buyer.route('/cart/apply-coupon', methods=['POST'])
@buyer_required
def apply_coupon():
    code = request.form.get('coupon', '').strip().upper()
    VALID_COUPONS = {'AGRO10': 10, 'FRESH15': 15, 'KISAN20': 20}
    if code in VALID_COUPONS:
        session['coupon'] = {'code': code, 'discount_pct': VALID_COUPONS[code]}
        flash(f'Coupon {code} applied! {VALID_COUPONS[code]}% off', 'success')
    else:
        flash('Invalid coupon code.', 'danger')
    return redirect(url_for('buyer.cart'))


@buyer.route('/cart/remove-coupon')
@buyer_required
def remove_coupon():
    session.pop('coupon', None)
    flash('Coupon removed.', 'info')
    return redirect(url_for('buyer.cart'))


# ─── CHECKOUT: ADDRESS ───────────────────────────────────────────────────────
@buyer.route('/checkout/address')
@buyer_required
def checkout_address():
    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.cart'))
    addresses = Address.query.filter_by(buyer_id=buyer_id).all()
    return render_template('buyer/checkout_address.html', addresses=addresses)


@buyer.route('/checkout/address/add', methods=['POST'])
@buyer_required
def add_address():
    buyer_id = session['user_id']
    is_first = Address.query.filter_by(buyer_id=buyer_id).count() == 0
    addr = Address(
        buyer_id=buyer_id,
        full_name=request.form['full_name'],
        phone=request.form['phone'],
        line1=request.form['line1'],
        line2=request.form.get('line2', ''),
        city=request.form['city'],
        state=request.form['state'],
        pincode=request.form['pincode'],
        is_default=is_first
    )
    db.session.add(addr)
    db.session.commit()
    flash('Address saved!', 'success')
    return redirect(url_for('buyer.checkout_address'))


@buyer.route('/checkout/address/select/<int:addr_id>')
@buyer_required
def select_address(addr_id):
    addr = Address.query.filter_by(id=addr_id, buyer_id=session['user_id']).first_or_404()
    session['selected_address_id'] = addr_id
    return redirect(url_for('buyer.checkout_payment'))


# ─── CHECKOUT: PAYMENT ───────────────────────────────────────────────────────
@buyer.route('/checkout/payment')
@buyer_required
def checkout_payment():
    if 'selected_address_id' not in session:
        flash('Please select a delivery address first.', 'warning')
        return redirect(url_for('buyer.checkout_address'))

    buyer_id   = session['user_id']
    address    = Address.query.get(session['selected_address_id'])
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()

    subtotal        = sum(i.product.price * i.quantity for i in cart_items) if cart_items else 0
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))
    total           = subtotal - coupon_discount + delivery

    return render_template('buyer/checkout_payment.html',
        address=address,
        cart_items=cart_items,
        subtotal=subtotal,
        coupon=coupon,
        coupon_discount=coupon_discount,
        delivery=delivery,
        total=total,
        razorpay_key_id=current_app.config['RAZORPAY_KEY_ID']
    )


# ─── RAZORPAY: CREATE ORDER ───────────────────────────────────────────────────
@buyer.route('/checkout/create-razorpay-order', methods=['POST'])
@buyer_required
def create_razorpay_order():
    import razorpay
    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    if not cart_items:
        return jsonify({'error': 'Empty cart'}), 400

    subtotal        = sum(i.product.price * i.quantity for i in cart_items)
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))
    total           = subtotal - coupon_discount + delivery
    amount_paise    = int(total * 100)

    client = razorpay.Client(
        auth=(current_app.config['RAZORPAY_KEY_ID'],
              current_app.config['RAZORPAY_KEY_SECRET'])
    )
    order = client.order.create({'amount': amount_paise, 'currency': 'INR', 'payment_capture': 1})
    return jsonify({'order_id': order['id'], 'amount': amount_paise})


# ─── RAZORPAY: CALLBACK ───────────────────────────────────────────────────────
@buyer.route('/checkout/razorpay-callback', methods=['POST'])
@buyer_required
def razorpay_callback():
    payment_id = request.form.get('razorpay_payment_id', '')
    order_id   = request.form.get('razorpay_order_id', '')
    signature  = request.form.get('razorpay_signature', '')

    key_secret = current_app.config['RAZORPAY_KEY_SECRET'].encode()
    msg        = f'{order_id}|{payment_id}'.encode()
    expected   = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        flash('Payment verification failed. Please contact support.', 'danger')
        return redirect(url_for('buyer.checkout_payment'))

    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    if not cart_items:
        flash('Cart is empty.', 'warning')
        return redirect(url_for('buyer.cart'))

    address        = Address.query.get(session.get('selected_address_id'))
    delivery_str   = f"{address.line1}, {address.line2 or ''}, {address.city}, {address.state} - {address.pincode}"
    order_group_id = 'AGC' + str(uuid.uuid4())[:8].upper()

    for item in cart_items:
        order = Order(
            order_group_id   = order_group_id,
            buyer_id         = buyer_id,
            farmer_id        = item.product.farmer_id,
            product_id       = item.product_id,
            quantity         = item.quantity,
            total_price      = item.product.price * item.quantity,
            delivery_address = delivery_str,
            payment_method   = 'razorpay',
            status           = 'confirmed',
            created_at       = datetime.utcnow()
        )
        db.session.add(order)
        db.session.delete(item)

    session.pop('coupon', None)
    session.pop('selected_address_id', None)
    db.session.commit()

    flash('Payment successful! Order placed 🎉', 'success')
    return redirect(url_for('buyer.order_confirm', order_group_id=order_group_id))


 # ─── UPI/QR PAYMENT ──────────────────────────────────────────────────────────
@buyer.route('/checkout/upi-payment')
@buyer_required  
def upi_payment():
    if 'selected_address_id' not in session:
        flash('Please select a delivery address first.', 'warning')
        return redirect(url_for('buyer.checkout_address'))

    buyer_id   = session['user_id']
    address    = Address.query.get(session['selected_address_id'])
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()

    subtotal        = sum(i.product.price * i.quantity for i in cart_items) if cart_items else 0
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))
    total           = subtotal - coupon_discount + delivery

    # Get farmer UPI IDs from cart items
    from models import User
    farmer_upi = None
    if cart_items:
        farmer = User.query.get(cart_items[0].product.farmer_id)
        if farmer and farmer.upi_id:
            farmer_upi = farmer.upi_id

    return render_template('buyer/upi_payment.html',
        address=address, cart_items=cart_items,
        subtotal=subtotal, coupon=coupon,
        coupon_discount=coupon_discount, delivery=delivery,
        total=total, farmer_upi=farmer_upi)


@buyer.route('/checkout/upi-confirm', methods=['POST'])
@buyer_required
def upi_confirm():
    """User confirms they have paid via UPI/QR"""
    buyer_id       = session['user_id']
    cart_items     = Cart.query.filter_by(buyer_id=buyer_id).all()
    upi_ref        = request.form.get('upi_ref', '').strip()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.cart'))

    address        = Address.query.get(session.get('selected_address_id'))
    delivery_str   = f"{address.line1}, {address.line2 or ''}, {address.city}, {address.state} - {address.pincode}"
    order_group_id = 'AGC' + str(uuid.uuid4())[:8].upper()

    subtotal        = sum(i.product.price * i.quantity for i in cart_items)
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))

    for item in cart_items:
        order = Order(
            order_group_id   = order_group_id,
            buyer_id         = buyer_id,
            farmer_id        = item.product.farmer_id,
            product_id       = item.product_id,
            quantity         = item.quantity,
            total_price      = item.product.price * item.quantity,
            delivery_address = delivery_str,
            payment_method   = 'upi',
            payment_id       = upi_ref or 'UPI-PENDING',
            status           = 'confirmed',
            created_at       = datetime.utcnow()
        )
        db.session.add(order)
        db.session.delete(item)

    session.pop('coupon', None)
    session.pop('selected_address_id', None)
    db.session.commit()

    flash('Payment confirmed! Order placed 🎉', 'success')
    return redirect(url_for('buyer.order_confirm', order_group_id=order_group_id))



# ─── PLACE ORDER (COD) ────────────────────────────────────────────────────────
@buyer.route('/checkout/place-order', methods=['POST'])
@buyer_required
def place_order():
    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('buyer.cart'))
    if 'selected_address_id' not in session:
        flash('Please select a delivery address.', 'warning')
        return redirect(url_for('buyer.checkout_address'))

    address        = Address.query.get(session['selected_address_id'])
    payment_method = request.form.get('payment_method', 'cod')
    subtotal        = sum(i.product.price * i.quantity for i in cart_items)
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 300 else (7 if subtotal > 200 else (9 if subtotal > 100 else 11))
    order_group_id = 'AGC' + str(uuid.uuid4())[:8].upper()
    delivery_str   = f"{address.line1}, {address.line2 or ''}, {address.city}, {address.state} - {address.pincode}"

    for item in cart_items:
        order = Order(
            order_group_id   = order_group_id,
            buyer_id         = buyer_id,
            farmer_id        = item.product.farmer_id,
            product_id       = item.product_id,
            quantity         = item.quantity,
            total_price      = item.product.price * item.quantity,
            delivery_address = delivery_str,
            payment_method   = payment_method,
            status           = 'confirmed',
            created_at       = datetime.utcnow()
        )
        db.session.add(order)
        db.session.delete(item)

    session.pop('coupon', None)
    session.pop('selected_address_id', None)
    db.session.commit()

    flash('Order placed successfully! 🎉', 'success')
    return redirect(url_for('buyer.order_confirm', order_group_id=order_group_id))


# ─── ORDER CONFIRMATION ───────────────────────────────────────────────────────
@buyer.route('/order/confirm/<order_group_id>')
@buyer_required
def order_confirm(order_group_id):
    buyer_id = session['user_id']
    orders   = Order.query.filter_by(order_group_id=order_group_id, buyer_id=buyer_id).all()
    if not orders:
        flash('Order not found.', 'danger')
        return redirect(url_for('buyer.dashboard'))
    total = sum(o.total_price for o in orders)
    return render_template('buyer/order_confirm.html',
        orders=orders, order_group_id=order_group_id, total=total)


# ─── ORDER TRACKING ───────────────────────────────────────────────────────────
@buyer.route('/order/track/<int:order_id>')
@buyer_required
def order_track(order_id):
    order = Order.query.filter_by(order_id=order_id, buyer_id=session['user_id']).first_or_404()
    status_steps = [
        ('confirmed',        'Order Placed',       '📋'),
        ('farmer_confirmed', 'Farmer Confirmed',   '🧑‍🌾'),
        ('packed',           'Harvested & Packed', '📦'),
        ('out_for_delivery', 'Out for Delivery',   '🚚'),
        ('delivered',        'Delivered',          '✅'),
    ]
    current_step = next(
        (i for i, (key, _, _) in enumerate(status_steps) if key == order.status), 0
    )
    return render_template('buyer/order_tracking.html',
        order=order, status_steps=status_steps, current_step=current_step)


# ─── MY ORDERS ────────────────────────────────────────────────────────────────
@buyer.route('/my-orders')
@buyer_required
def my_orders():
    buyer_id = session['user_id']
    orders   = Order.query.filter_by(buyer_id=buyer_id).order_by(Order.created_at.desc()).all()
    return render_template('buyer/my_orders.html', orders=orders)


# ─── CANCEL ORDER ────────────────────────────────────────────────────────────
@buyer.route('/order/cancel/<int:order_id>', methods=['POST'])
@buyer_required
def cancel_order(order_id):
    order = Order.query.filter_by(order_id=order_id, buyer_id=session['user_id']).first_or_404()
    if order.status != 'confirmed':
        flash('Order cannot be cancelled at this stage.', 'warning')
        return redirect(url_for('buyer.my_orders'))
    order.status = 'cancelled'
    db.session.commit()
    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('buyer.my_orders'))


# ─── REVIEW ──────────────────────────────────────────────────────────────────
@buyer.route('/review/<int:order_id>', methods=['GET', 'POST'])
@buyer_required
def review(order_id):
    order = Order.query.filter_by(order_id=order_id, buyer_id=session['user_id']).first_or_404()
    if request.method == 'POST':
        rev = Review(
            buyer_id  = session['user_id'],
            farmer_id = order.farmer_id,
            order_id  = order_id,
            rating    = int(request.form['rating']),
            comment   = request.form['comment']
        )
        db.session.add(rev)
        db.session.commit()
        flash('Review submitted! Thank you 🙏', 'success')
        return redirect(url_for('buyer.dashboard'))
    return render_template('buyer/review.html', order=order)