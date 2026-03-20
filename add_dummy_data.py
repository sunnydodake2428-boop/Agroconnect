from app import app
from extensions import db, bcrypt
from models import User, Product, Order, Review

with app.app_context():

    # CREATE FARMERS
    farmers_data = [
        {'name': 'Ramesh Patil', 'email': 'ramesh@farm.com', 'location': 'Nashik, Maharashtra', 'phone': '9876543201'},
        {'name': 'Suresh Jadhav', 'email': 'suresh@farm.com', 'location': 'Pune, Maharashtra', 'phone': '9876543202'},
        {'name': 'Ganesh Shinde', 'email': 'ganesh@farm.com', 'location': 'Nagpur, Maharashtra', 'phone': '9876543203'},
    ]

    farmers = []
    for f in farmers_data:
        existing = User.query.filter_by(email=f['email']).first()
        if not existing:
            hashed = bcrypt.generate_password_hash('farmer123').decode('utf-8')
            user = User(name=f['name'], email=f['email'], password=hashed,
                       role='farmer', phone=f['phone'], location=f['location'])
            db.session.add(user)
            db.session.flush()
            farmers.append(user)
        else:
            farmers.append(existing)

    db.session.commit()

    # CREATE PRODUCTS
    products_data = [
        {'crop': 'Tomato', 'category': 'vegetables', 'qty': 500, 'unit': 'kg', 'price': 25, 'desc': 'Fresh red tomatoes harvested this week.'},
        {'crop': 'Onion', 'category': 'vegetables', 'qty': 1000, 'unit': 'kg', 'price': 20, 'desc': 'Premium quality onions from Nashik.'},
        {'crop': 'Potato', 'category': 'vegetables', 'qty': 800, 'unit': 'kg', 'price': 15, 'desc': 'Fresh potatoes directly from farm.'},
        {'crop': 'Mango', 'category': 'fruits', 'qty': 300, 'unit': 'kg', 'price': 60, 'desc': 'Alphonso mangoes from Ratnagiri.'},
        {'crop': 'Wheat', 'category': 'grains', 'qty': 2000, 'unit': 'kg', 'price': 22, 'desc': 'High quality wheat grain this season.'},
        {'crop': 'Spinach', 'category': 'vegetables', 'qty': 200, 'unit': 'kg', 'price': 40, 'desc': 'Fresh organic spinach harvested daily.'},
        {'crop': 'Banana', 'category': 'fruits', 'qty': 400, 'unit': 'dozen', 'price': 25, 'desc': 'Fresh bananas natural ripening.'},
        {'crop': 'Rice', 'category': 'grains', 'qty': 1500, 'unit': 'kg', 'price': 35, 'desc': 'Basmati rice long grain aromatic.'},
        {'crop': 'Chilli', 'category': 'vegetables', 'qty': 150, 'unit': 'kg', 'price': 120, 'desc': 'Hot red chillies dried in sunlight.'},
        {'crop': 'Grapes', 'category': 'fruits', 'qty': 250, 'unit': 'kg', 'price': 70, 'desc': 'Seedless grapes from Sangli.'},
        {'crop': 'Cauliflower', 'category': 'vegetables', 'qty': 300, 'unit': 'kg', 'price': 35, 'desc': 'White cauliflower freshly harvested.'},
        {'crop': 'Carrot', 'category': 'vegetables', 'qty': 400, 'unit': 'kg', 'price': 30, 'desc': 'Fresh orange carrots high nutrition.'},
    ]

    for i, p in enumerate(products_data):
        farmer = farmers[i % len(farmers)]
        product = Product(
            farmer_id=farmer.user_id,
            crop_name=p['crop'],
            category=p['category'],
            quantity=p['qty'],
            unit=p['unit'],
            price=p['price'],
            description=p['desc'],
            image='default.jpg',
            status='available'
        )
        db.session.add(product)
        print(f"Added: {p['crop']}")

    db.session.commit()
    print("\nDone! All crops added.")
    print("\nFarmer logins:")
    for f in farmers_data:
        print(f"  {f['email']} / farmer123")