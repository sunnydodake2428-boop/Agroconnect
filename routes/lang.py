from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify

lang_bp = Blueprint('lang', __name__)

SUPPORTED = ['en', 'hi', 'mr']

@lang_bp.route('/language-select', methods=['GET', 'POST'])
def language_select():
    if request.method == 'POST':
        chosen = request.form.get('lang', 'en')
        if chosen not in SUPPORTED:
            chosen = 'en'
        session['lang'] = chosen
        # Redirect to where they came from, or home
        next_url = request.form.get('next') or '/'
        return redirect(next_url)
    return render_template('language_select.html')


@lang_bp.route('/set-language/<lang>')
def set_language(lang):
    """Quick switcher from navbar — keeps user on same page."""
    if lang not in SUPPORTED:
        lang = 'en'
    session['lang'] = lang
    # Go back to referring page
    referrer = request.referrer or '/'
    return redirect(referrer)