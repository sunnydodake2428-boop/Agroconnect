from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    user_id    = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(100), unique=True, nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    role       = db.Column(db.String(20), nullable=False)
    phone      = db.Column(db.String(15))
    location   = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'products'
    product_id  = db.Column(db.Integer, primary_key=True)
    farmer_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    crop_name   = db.Column(db.String(100), nullable=False)
    category    = db.Column(db.String(50))
    quantity    = db.Column(db.Float)
    unit        = db.Column(db.String(20))
    price       = db.Column(db.Float)
    mrp         = db.Column(db.Float, nullable=True)   # MRP / original price
    description = db.Column(db.Text)
    image       = db.Column(db.String(200), default='default.jpg')
    status      = db.Column(db.String(20), default='available')
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    farmer      = db.relationship('User', foreign_keys=[farmer_id])

class Order(db.Model):
    __tablename__ = 'orders'
    order_id         = db.Column(db.Integer, primary_key=True)
    order_group_id   = db.Column(db.String(20))          # groups cart items in one checkout
    buyer_id         = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    farmer_id        = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    product_id       = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity         = db.Column(db.Float)
    total_price      = db.Column(db.Float)
    delivery_address = db.Column(db.Text)
    payment_method   = db.Column(db.String(30), default='cod')
    status           = db.Column(db.String(20), default='confirmed')
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    buyer   = db.relationship('User', foreign_keys=[buyer_id])
    farmer  = db.relationship('User', foreign_keys=[farmer_id])
    product = db.relationship('Product', foreign_keys=[product_id])

class Review(db.Model):
    __tablename__ = 'reviews'
    review_id  = db.Column(db.Integer, primary_key=True)
    buyer_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    farmer_id  = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    order_id   = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    rating     = db.Column(db.Integer)
    comment    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cart(db.Model):
    __tablename__ = 'cart'
    cart_id    = db.Column(db.Integer, primary_key=True)
    buyer_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.product_id'), nullable=False)
    quantity   = db.Column(db.Float)
    added_at   = db.Column(db.DateTime, default=datetime.utcnow)
    product    = db.relationship('Product', foreign_keys=[product_id])

class Address(db.Model):
    __tablename__ = 'addresses'
    id         = db.Column(db.Integer, primary_key=True)
    buyer_id   = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    full_name  = db.Column(db.String(100))
    phone      = db.Column(db.String(15))
    line1      = db.Column(db.String(200))
    line2      = db.Column(db.String(200))
    city       = db.Column(db.String(100))
    state      = db.Column(db.String(100))
    pincode    = db.Column(db.String(10))
    is_default = db.Column(db.Boolean, default=False)
    user       = db.relationship('User', foreign_keys=[buyer_id])
