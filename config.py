import os

class Config:
    SECRET_KEY = 'agroconnect_secret_key_2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///agroconnect.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False