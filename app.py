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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
