import os

class Config:
    SECRET_KEY = 'agroconnect_secret_key_2024'

    # Use PostgreSQL on Railway if available, otherwise SQLite locally
    _db_url = os.environ.get('DATABASE_URL', 'sqlite:///agroconnect.db')
    # Fix old postgres:// URLs (Railway uses postgresql://)
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _db_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False