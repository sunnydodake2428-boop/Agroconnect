import os

class Config:
    SECRET_KEY = 'agroconnect_secret_key_2024'
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///agroconnect.db')
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False