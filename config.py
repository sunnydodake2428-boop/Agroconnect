import os

class Config:
    SECRET_KEY = 'agroconnect_secret_key_2024'
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///agroconnect.db')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Razorpay
    RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID',     'rzp_test_SsgiU47seL6deY')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '79PvIrLoJqk25iMv76Q8W6b2')