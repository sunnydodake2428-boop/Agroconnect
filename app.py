from flask import Flask, render_template, session
from extensions import db, bcrypt
from config import Config
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    bcrypt.init_app(app)

    from routes.auth import auth
    from routes.farmer import farmer
    from routes.buyer import buyer
    from routes.admin import admin
    from routes.ml import ml
    from routes.lang import lang_bp

    app.register_blueprint(auth)
    app.register_blueprint(farmer)
    app.register_blueprint(buyer)
    app.register_blueprint(admin)
    app.register_blueprint(ml)
    app.register_blueprint(lang_bp)

    from translations import t as _t

    @app.context_processor
    def inject_translations():
        lang = session.get('lang', 'en')
        def t(key):
            return _t(key, lang)
        return dict(t=t, current_lang=lang)

    @app.context_processor
    def inject_nav_counts():
        cart_count = 0
        pending_orders_count = 0
        if session.get('user_role') == 'buyer' and session.get('user_id'):
            try:
                from models import Cart, Order
                cart_count = Cart.query.filter_by(buyer_id=session['user_id']).count()
                pending_orders_count = Order.query.filter_by(
                    buyer_id=session['user_id']
                ).filter(Order.status.in_(['confirmed','farmer_confirmed','packed','out_for_delivery'])).count()
            except: pass
        if session.get('user_role') == 'farmer' and session.get('user_id'):
            try:
                from models import Order
                pending_orders_count = Order.query.filter_by(
                    farmer_id=session['user_id'], status='confirmed'
                ).count()
            except: pass
        return dict(cart_count=cart_count, pending_orders_count=pending_orders_count)

    @app.route('/')
    def home():
        if 'lang' not in session:
            from flask import redirect, url_for
            return redirect(url_for('lang.language_select'))
        from models import Product
        featured_crops = Product.query.filter_by(status='available').limit(8).all()
        return render_template('home.html', featured_crops=featured_crops)

    @app.after_request
    def no_cache_static(response):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    return app

app = create_app()

with app.app_context():
    db.create_all()
    from sqlalchemy import text
    with db.engine.connect() as conn:
        for sql in [
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_id VARCHAR(100)",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method VARCHAR(30) DEFAULT 'cod'",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_group_id VARCHAR(20)",
            "ALTER TABLE products ADD COLUMN IF NOT EXISTS mrp FLOAT",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except: pass

if __name__ == '__main__':
    app.run(debug=False)