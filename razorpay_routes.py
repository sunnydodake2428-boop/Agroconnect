# Add these imports at the top of routes/buyer.py:
# import hmac, hashlib
# from flask import current_app, jsonify

# Add these 2 routes at the bottom of routes/buyer.py:

@buyer.route('/checkout/create-razorpay-order', methods=['POST'])
@buyer_required
def create_razorpay_order():
    import razorpay, json
    from flask import current_app, jsonify
    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()
    if not cart_items:
        return jsonify({'error': 'Empty cart'}), 400

    subtotal        = sum(i.product.price * i.quantity for i in cart_items)
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 500 else 40
    total           = subtotal - coupon_discount + delivery
    amount_paise    = int(total * 100)  # Razorpay uses paise

    client = razorpay.Client(
        auth=(current_app.config['RAZORPAY_KEY_ID'],
              current_app.config['RAZORPAY_KEY_SECRET'])
    )
    order = client.order.create({
        'amount':   amount_paise,
        'currency': 'INR',
        'payment_capture': 1
    })
    return jsonify({'order_id': order['id'], 'amount': amount_paise})


@buyer.route('/checkout/razorpay-callback', methods=['POST'])
@buyer_required
def razorpay_callback():
    import razorpay, hmac, hashlib
    from flask import current_app

    payment_id = request.form.get('razorpay_payment_id', '')
    order_id   = request.form.get('razorpay_order_id', '')
    signature  = request.form.get('razorpay_signature', '')

    # Verify signature
    key_secret = current_app.config['RAZORPAY_KEY_SECRET'].encode()
    msg        = f'{order_id}|{payment_id}'.encode()
    expected   = hmac.new(key_secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, signature):
        flash('Payment verification failed. Please contact support.', 'danger')
        return redirect(url_for('buyer.checkout_payment'))

    # Payment verified — place the order
    buyer_id   = session['user_id']
    cart_items = Cart.query.filter_by(buyer_id=buyer_id).all()

    if not cart_items:
        flash('Cart is empty.', 'warning')
        return redirect(url_for('buyer.cart'))

    address        = Address.query.get(session.get('selected_address_id'))
    delivery_str   = f"{address.line1}, {address.line2 or ''}, {address.city}, {address.state} - {address.pincode}"
    order_group_id = 'AGC' + str(uuid.uuid4())[:8].upper()

    subtotal        = sum(i.product.price * i.quantity for i in cart_items)
    coupon          = session.get('coupon', {})
    coupon_discount = round(subtotal * coupon.get('discount_pct', 0) / 100)
    delivery        = 0 if subtotal > 500 else 40

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
            payment_id       = payment_id,
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