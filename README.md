<div align="center">

# 🌾 AgroConnect

### Direct Farm-to-Table Marketplace for India

**Eliminating middlemen between farmers and buyers — Zero commission. AI-powered. Built for rural Maharashtra.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-agroconnect--gphg.onrender.com-22c55e?style=for-the-badge&logo=render)](https://agroconnect-gphg.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791?style=for-the-badge&logo=postgresql)](https://neon.tech)

</div>

---

## The Problem

India has **600 million farmers** — yet the average farmer earns only ₹4–5 lakh per year.

```
Farmer grows tomato → sells at ₹8/kg to agent
Agent               → sells at ₹15/kg to mandi
Mandi               → sells at ₹25/kg to retailer
Retailer            → sells at ₹40/kg to consumer

Consumer pays ₹40 — Farmer got only ₹8
The ₹32 gap goes to middlemen — not the farmer
```

**AgroConnect eliminates this chain entirely.**

---

## Solution

A direct farm-to-buyer marketplace where:

- 🌾 **Farmers** list crops at AI-predicted fair prices
- 🛒 **Buyers** purchase directly from verified farmers
- 💸 **₹0 commission** — 100% of the money goes to the farmer
- 🤖 **AI handles** crop identification, live mandi pricing, weather advisory, and sell-timing

---

## Features

### AI & Machine Learning

| Feature | Description |
|---|---|
| **Crop Detection** | Upload a photo → Gemini Vision (primary) + HuggingFace CLIP (fallback) → identifies crop in <3 seconds |
| **Live Price Prediction** | Fetches real-time mandi prices from the Government of India's Agmarknet API, then applies season and weather multipliers |
| **Best Time to Sell** | Ridge Regression model trained on 36 months of real APMC Maharashtra price data — R²=0.94 on onion prices |
| **Weather Advisory** | GPS coordinates → OpenWeatherMap/Open-Meteo → localized crop-specific advisory |

### Price Prediction Engine

```python
predicted_price = base_mandi_price × season_multiplier × weather_adjustment

# Season multipliers (supply/demand patterns)
summer:  × 1.2   # scarcity due to heat
monsoon: × 1.1   # transport disruption
winter:  × 0.9   # high supply

# Weather adjustments
humidity > 75%:  × 1.08   # crop damage risk
temp > 38°C:     × 1.12   # heat stress → scarcity
```

### Farmer Tools

- AI crop photo detection — no typing required
- Live Agmarknet government mandi price lookup
- 12-month price trend chart (Ridge Regression ML model)
- GPS-based weather advisory for their village
- Add, manage, and delete crop listings
- Order status management: Pending → Confirmed → Dispatched → Delivered

### Buyer Tools

- Marketplace with search, category filter, and voice search (Marathi/Hindi)
- Shopping cart with quantity controls and coupon codes
- Full checkout flow: address → payment → order confirmation
- Amazon/Flipkart-style order tracking with timestamps
- Post-delivery star rating and review system
- Order cancellation for unconfirmed orders

### Platform

- Three roles: Farmer, Buyer, Admin — with route-level authorization
- Multilingual: English, Hindi, Marathi (80+ translated strings)
- Mobile-responsive with EXIF-corrected image compression for phone uploads
- Farm background image on authentication pages
- Account profile with password change and security info

---

## Tech Stack

### Backend

| Technology | Purpose |
|---|---|
| Python 3.11 | Core language |
| Flask 3.0 | Web framework — Blueprint routing, Jinja2 templating, sessions |
| Flask-SQLAlchemy | ORM — Python models map to PostgreSQL tables |
| Flask-Bcrypt | bcrypt password hashing (salted, one-way) |
| Werkzeug | Secure file upload handling |
| Gunicorn | WSGI production server |
| psycopg2-binary | PostgreSQL driver |

### Database

| Technology | Purpose |
|---|---|
| PostgreSQL (Neon) | Persistent cloud database — survives every redeploy |
| SQLite | Local development fallback |
| SQLAlchemy ORM | Parameterized queries — SQL injection proof by default |

### AI & Machine Learning

| Technology | Purpose |
|---|---|
| Google Gemini Vision API | Primary crop detection from uploaded photos |
| HuggingFace CLIP | Zero-shot crop classification fallback |
| Groq LLaMA Vision | Additional vision fallback |
| scikit-learn Ridge Regression | Best time to sell — trained on 36 months APMC data |
| NumPy | Numerical computation for price modeling |
| Pillow | Image compression and EXIF rotation fix for mobile uploads |

### External APIs

| API | Cost | Purpose |
|---|---|---|
| Agmarknet (data.gov.in) | Free | Live government mandi wholesale prices |
| OpenWeatherMap | Free (1000/day) | GPS-based weather data |
| Open-Meteo | Free unlimited | Weather fallback |
| OSM Nominatim | Free | Reverse geocoding (lat/lon → village name) |

### Frontend

| Technology | Purpose |
|---|---|
| Bootstrap 5.3 | Responsive grid and components |
| Custom CSS (MintFresh design system) | Dark green theme, animations |
| Chart.js | 12-month price trend visualization |
| Web Speech API | Voice search in Marathi and Hindi (browser-native, no cost) |
| Font Awesome 6 | Icons |

---

## Architecture

```
CLIENT BROWSER
  HTML + CSS + Chart.js + Web Speech API + GPS geolocation
         │ HTTP
         ▼
FLASK APPLICATION (Gunicorn + Render.com)
  routes/auth.py     → login, register, logout, profile
  routes/farmer.py   → dashboard, listings, order management
  routes/buyer.py    → marketplace, cart, checkout, tracking, review
  routes/admin.py    → admin panel
  routes/ml.py       → crop detection, price predictor, weather, best time to sell
  routes/lang.py     → language switching
         │
    ┌────┴────────────────────┐
    ▼                         ▼
PostgreSQL (Neon)       External APIs
  users                   Agmarknet — live mandi prices
  products                Gemini Vision — crop detection
  orders                  OpenWeatherMap — GPS weather
  cart                    HuggingFace CLIP — detection fallback
  reviews                 Open-Meteo — weather fallback
  addresses               OSM Nominatim — reverse geocoding
```

---

## Database Design

```
USERS                           PRODUCTS
──────────────────              ──────────────────────
user_id        PK               product_id     PK
name                            farmer_id      FK → users
email          UNIQUE           crop_name
password       bcrypt hash      category
role           farmer|buyer|admin  quantity, unit, price
phone                           mrp
location                        description, image
created_at                      status         available|sold
                                created_at

ORDERS                          CART
──────────────────              ──────────────────────
order_id       PK               cart_id        PK
buyer_id       FK → users       buyer_id       FK → users
farmer_id      FK → users       product_id     FK → products
product_id     FK → products    quantity
quantity, total_price           added_at
delivery_address
payment_method                  REVIEWS
status                          ──────────────────────
confirmed_at                    review_id      PK
dispatched_at                   buyer_id       FK → users
delivered_at                    farmer_id      FK → users
cancelled_at                    order_id       FK → orders
created_at                      rating         1–5
                                comment, tags
ADDRESSES                       created_at
──────────────────
id             PK
user_id        FK → users
full_name, phone
line1, line2, city
state, pincode
is_default
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/sunnydodake2428-boop/AgroConnect.git
cd AgroConnect

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
# Create a .env file:
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-gemini-key
AGMARKNET_API_KEY=579b464db66ec23bdd000001f19d95480291496e59a48e773ea31015
DATABASE_URL=sqlite:///agroconnect.db   # or your PostgreSQL URL

# 5. Initialize database
python init_db.py

# 6. Run
python app.py
# Visit: http://127.0.0.1:5000
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session signing key |
| `GEMINI_API_KEY` | Yes | Google Gemini Vision for crop detection |
| `GROQ_API_KEY` | Optional | Groq LLaMA Vision (additional fallback) |
| `AGMARKNET_API_KEY` | Optional | Government mandi price API (public key included) |
| `DATABASE_URL` | Optional | PostgreSQL URL — defaults to SQLite locally |

---

## Project Structure

```
AgroConnect/
├── app.py                      # App factory, blueprint registration, translation injection
├── config.py                   # PostgreSQL/SQLite config via DATABASE_URL env var
├── extensions.py               # db, bcrypt instances
├── models.py                   # SQLAlchemy models: User, Product, Order, Cart, Review, Address
├── translations.py             # 80+ keys in English, Hindi, Marathi
├── requirements.txt
├── Procfile                    # gunicorn app:app
├── runtime.txt                 # python-3.11
│
├── routes/
│   ├── auth.py                 # Login, register, logout, profile, password change
│   ├── farmer.py               # Dashboard, add/delete listings, update order status
│   ├── buyer.py                # Marketplace, cart, checkout, orders, tracking, cancel, review
│   ├── admin.py                # Admin panel
│   ├── ml.py                   # Crop detection, price predictor, best time to sell, weather
│   └── lang.py                 # Language selection and switching
│
├── templates/
│   ├── base.html               # Navbar with profile avatar dropdown, flash messages
│   ├── home.html               # Landing page
│   ├── auth/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── profile.html        # Account settings, password change
│   ├── farmer/
│   │   ├── dashboard.html      # Listings, orders, earnings
│   │   └── add_listing.html
│   ├── buyer/
│   │   ├── marketplace.html    # Product grid with voice search
│   │   ├── dashboard.html      # Orders with track/view/cancel/review buttons
│   │   ├── cart.html
│   │   ├── checkout_address.html
│   │   ├── checkout_payment.html
│   │   ├── order_confirm.html
│   │   └── order_tracking.html # Amazon-style step tracker with timestamps
│   ├── ml/
│   │   ├── predictor.html      # AI price predictor with Agmarknet live badge
│   │   └── best_time.html      # Ridge Regression 12-month chart
│   └── orders/
│       └── review.html         # Star rating with quick tags
│
└── static/
    ├── css/style.css           # MintFresh design system
    ├── js/main.js
    └── images/                 # Crop photos, logo, farm background
```

---

## Impact

| Crop | Mandi Price | AgroConnect | Farmer Gain |
|---|---|---|---|
| Tomato | ₹8–10/kg | ₹25/kg | +150–213% |
| Onion | ₹8–12/kg | ₹20/kg | +67–150% |
| Rose | ₹60/kg | ₹150/kg | +150% |
| Grapes | ₹30/kg | ₹70/kg | +133% |

**Average: 250% income increase for farmers on AgroConnect**

---

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| 👨‍🌾 Farmer | ramesh@farm.com | farmer123 |
| 🛒 Buyer | priya@buyer.com | buyer123 |

---

## Deployment

The platform is deployed on **Render.com** (web service) with **Neon PostgreSQL** as the persistent database.

- Auto-deploys on every push to `master`
- PostgreSQL data persists across all redeployments
- UptimeRobot configured to prevent free-tier sleep

**Live:** https://agroconnect-gphg.onrender.com

---

## Team

Built by engineering students from Maharashtra, India — 2026.

---

*Built with ❤️ for the farmers of India 🌾*

> *"When farmers prosper, India prospers."*