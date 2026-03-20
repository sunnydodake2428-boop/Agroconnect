from app import app
from extensions import db, bcrypt
from models import User, Product

with app.app_context():
    # Create one farmer
    existing = User.query.filter_by(email='ramesh@farm.com').first()
    if not existing:
        hashed = bcrypt.generate_password_hash('farmer123').decode('utf-8')
        farmer = User(
            name='Ramesh Patil',
            email='ramesh@farm.com',
            password=hashed,
            role='farmer',
            phone='9876543201',
            location='Nashik, Maharashtra'
        )
        db.session.add(farmer)
        db.session.flush()
    else:
        farmer = existing

    # Add products
    crops = [
        # Vegetables
        ('Tomato', 'vegetables', 500, 'kg', 25),
        ('Onion', 'vegetables', 1000, 'kg', 20),
        ('Potato', 'vegetables', 800, 'kg', 15),
        ('Chilli', 'vegetables', 150, 'kg', 120),
        ('Spinach', 'vegetables', 200, 'kg', 40),
        ('Carrot', 'vegetables', 400, 'kg', 30),
        ('Cauliflower', 'vegetables', 300, 'kg', 35),
        # Fruits
        ('Mango', 'fruits', 300, 'kg', 60),
        ('Banana', 'fruits', 400, 'dozen', 25),
        ('Grapes', 'fruits', 250, 'kg', 70),
        # Grains
        ('Wheat', 'grains', 2000, 'kg', 22),
        ('Rice', 'grains', 1500, 'kg', 35),
        # Flowers
        ('Rose', 'flowers', 500, 'kg', 150),
        ('Marigold', 'flowers', 1000, 'kg', 40),
        ('Jasmine', 'flowers', 200, 'kg', 200),
        ('Tuberose', 'flowers', 300, 'kg', 120),
        ('Gerbera', 'flowers', 400, 'kg', 100),
        ('Mogra', 'flowers', 150, 'kg', 250),
        # Spices
        ('Garlic', 'spices', 300, 'kg', 90),
        ('Ginger', 'spices', 250, 'kg', 80),
        ('Turmeric', 'spices', 200, 'kg', 110),
    ]

    for crop, cat, qty, unit, price in crops:
        # Skip if already exists
        existing_product = Product.query.filter_by(
            crop_name=crop,
            farmer_id=farmer.user_id
        ).first()
        if not existing_product:
            p = Product(
                farmer_id=farmer.user_id,
                crop_name=crop,
                category=cat,
                quantity=qty,
                unit=unit,
                price=price,
                description=f'Fresh {crop} directly from farm. Best quality available.',
                image='default.jpg',
                status='available'
            )
            db.session.add(p)
            print(f'Added: {crop} ({cat})')
        else:
            print(f'Skipped: {crop} already exists')

    db.session.commit()
    print('\nAll products added successfully!')
    print('Farmer login: ramesh@farm.com / farmer123')