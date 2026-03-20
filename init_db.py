from app import app
from extensions import db, bcrypt
from models import User

with app.app_context():
    db.create_all()
    
    admin = User.query.filter_by(email='admin@agroconnect.com').first()
    if not admin:
        hashed = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = User(
            name='Admin',
            email='admin@agroconnect.com',
            password=hashed,
            role='admin',
            phone='9999999999',
            location='India'
        )
        db.session.add(admin)
        db.session.commit()
    
    print("Database created successfully!")
    print("Admin login: admin@agroconnect.com / admin123")