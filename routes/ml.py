from flask import Blueprint, render_template, request, session
import numpy as np
import requests
import datetime
import os
from PIL import Image, ImageOps
import io

ml = Blueprint('ml', __name__)

# ============================================================
#  CONFIGURATION
# ============================================================
WEATHER_API_KEY       = 'ac2393b20e59d2176ba0938bc79029e3'
AGMARKNET_API_KEY     = '579b464db66ec23bdd000001f19d95480291496e59a48e773ea31015'
AGMARKNET_RESOURCE_ID = '9ef84268-d588-465a-a308-a864a43d0070'

# GEMINI KEY — reads from env, falls back to hardcoded for demo
GEMINI_API_KEY = (
    os.environ.get("GEMINI_API_KEY") or "AIzaSyDF-tC_ciLlh_Zlm_6IVNpXSZGqCI4xSY0"
    os.environ.get("GOOGLE_API_KEY") or
    ""   # ← PASTE YOUR KEY HERE AS FALLBACK: "AIzaSy..."
)


# ============================================================
#  MOBILE IMAGE COMPRESSION
# ============================================================
def compress_image(image_bytes, max_size_kb=800):
    try:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)

        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        max_dimension = 1024
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        quality = 85
        output  = io.BytesIO()
        while quality >= 20:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            if output.tell() <= max_size_kb * 1024:
                break
            quality -= 10

        compressed = output.getvalue()
        print(f'[COMPRESS] {len(image_bytes)//1024}KB -> {len(compressed)//1024}KB (q={quality})')
        return compressed, 'image/jpeg'

    except Exception as e:
        print(f'[COMPRESS ERROR] {e}')
        return image_bytes, 'image/jpeg'


# ============================================================
#  CROP MAPPINGS & PRICES
# ============================================================
CROP_TO_AGMARKNET = {
    'tomato':'Tomato','potato':'Potato','onion':'Onion','wheat':'Wheat',
    'rice':'Rice','corn':'Maize','carrot':'Carrot','spinach':'Spinach',
    'mango':'Mango','banana':'Banana','apple':'Apple','grapes':'Grapes',
    'cauliflower':'Cauliflower','cabbage':'Cabbage','brinjal':'Brinjal',
    'okra':'Bhindi(Ladies Finger)','peas':'Peas','garlic':'Garlic',
    'ginger':'Ginger','orange':'Orange','papaya':'Papaya',
    'watermelon':'Water Melon','chilli':'Green Chilli','cucumber':'Cucumber',
    'pumpkin':'Pumpkin','radish':'Radish','beetroot':'Beetroot',
    'capsicum':'Capsicum','sweetcorn':'Sweet Corn',
    'rose':'Rose(Local)','marigold':'Marigold(Calcutta)','jasmine':'Jasmine',
}

FALLBACK_BASE_PRICES = {
    'tomato':25,'potato':15,'onion':20,'wheat':22,'rice':35,'corn':18,
    'carrot':30,'spinach':40,'mango':60,'banana':25,'apple':80,'grapes':70,
    'cauliflower':35,'cabbage':20,'brinjal':28,'okra':32,'peas':45,
    'garlic':90,'ginger':80,'orange':55,'papaya':30,'watermelon':18,
    'chilli':120,'cucumber':22,'pumpkin':15,'radish':18,'beetroot':25,
    'capsicum':60,'sweetcorn':20,'sugarcane':5,'cotton':65,'soybean':45,
    'groundnut':55,'rose':150,'marigold':40,'jasmine':200,'lotus':180,
    'sunflower':80,'tuberose':120,'chrysanthemum':90,'gerbera':100,
    'lily':160,'mogra':250,'crossandra':60,'aster':70,
}

SEASON_MULTIPLIER = {'summer':1.2,'winter':0.9,'monsoon':1.1,'spring':1.0}

MAHARASHTRA_CITY_TO_MARKET = {
    'kolhapur':['Kolhapur','Ichalkaranji'],
    'pune':['Pune','Pimpri','Chinchwad','Hadapsar'],
    'nashik':['Nashik','Lasalgaon','Pimpalgaon'],
    'mumbai':['Mumbai','Vashi','Dadar'],
    'aurangabad':['Aurangabad','Chhatrapati Sambhajinagar'],
    'nagpur':['Nagpur','Kamptee'],
    'solapur':['Solapur','Pandharpur'],
    'sangli':['Sangli','Miraj','Tasgaon'],
    'satara':['Satara','Phaltan','Karad'],
    'ahmednagar':['Ahmednagar','Shrirampur','Rahuri'],
    'latur':['Latur','Udgir'],
    'nanded':['Nanded','Mukhed'],
    'jalgaon':['Jalgaon','Bhusawal','Yawal'],
    'akola':['Akola','Washim'],
    'amravati':['Amravati','Achalpur'],
    'thane':['Thane','Bhiwandi','Kalyan'],
    'raigad':['Alibag','Pen','Panvel'],
    'ratnagiri':['Ratnagiri','Chiplun','Khed'],
    'sindhudurg':['Kudal','Sawantwadi'],
    'dhule':['Dhule','Shirpur'],
    'nandurbar':['Nandurbar','Shahada'],
    'osmanabad':['Osmanabad','Tuljapur'],
    'beed':['Beed','Ambejogai'],
    'hingoli':['Hingoli','Kalamnuri'],
    'parbhani':['Parbhani','Gangakhed'],
    'yavatmal':['Yavatmal','Wani'],
    'wardha':['Wardha','Hinganghat'],
    'chandrapur':['Chandrapur','Ballarpur'],
    'gadchiroli':['Gadchiroli'],
    'gondia':['Gondia','Tirora'],
    'bhandara':['Bhandara','Tumsar'],
    'washim':['Washim','Malegaon'],
    'buldhana':['Buldhana','Malkapur'],
}

SUPPORTED_CROPS = [
    'tomato','potato','onion','wheat','rice','corn','carrot','spinach',
    'mango','banana','apple','grapes','cauliflower','cabbage','brinjal',
    'okra','peas','garlic','ginger','orange','papaya','watermelon',
    'chilli','capsicum','cucumber','pumpkin','radish','beetroot',
    'sweetcorn','rose','marigold','jasmine','sunflower','lotus',
    'sugarcane','cotton','soybean','groundnut',
]

SYNONYMS = {
    'eggplant':'brinjal','aubergine':'brinjal','baingan':'brinjal','baigan':'brinjal',
    'bhindi':'okra','ladyfinger':'okra',"lady's finger":'okra','vendakkai':'okra',
    'shimla mirch':'capsicum','bell pepper':'capsicum','green pepper':'capsicum','red pepper':'capsicum',
    'mirchi':'chilli','chili':'chilli','chilly':'chilli','green chilli':'chilli','red chilli':'chilli',
    'maize':'corn','makka':'corn','makkai':'corn','sweet corn':'sweetcorn',
    'aloo':'potato','alu':'potato','sweet potato':'potato',
    'tamatar':'tomato','tamaatar':'tomato',
    'pyaz':'onion','kanda':'onion','dungri':'onion',
    'lehsun':'garlic','lasun':'garlic',
    'adrak':'ginger','adrakh':'ginger','ginger root':'ginger',
    'palak':'spinach',
    'gobhi':'cauliflower','gobi':'cauliflower','phool gobhi':'cauliflower',
    'band gobhi':'cabbage','bandgobhi':'cabbage','patta gobhi':'cabbage',
    'gajar':'carrot','mooli':'radish','muli':'radish','aam':'mango',
    'kela':'banana','angoor':'grapes','grape':'grapes','santra':'orange',
    'narangi':'orange','papita':'papaya','gehun':'wheat','gehu':'wheat',
    'chawal':'rice','dhan':'rice','kaddu':'pumpkin','lauki':'pumpkin',
    'tarbuj':'watermelon',
}

GEMINI_MODELS = [
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-1.5-flash-latest',
]

GEMINI_PROMPT = """You are an expert Indian agricultural crop identifier.

TASK: Look at the image and identify the ONE crop shown.

Reply with ONLY one word from this exact list (nothing else):
""" + ', '.join(SUPPORTED_CROPS)


# ============================================================
#  AGMARKNET LIVE PRICE
# ============================================================
def fetch_agmarknet_price(crop_name, user_city=None, state='Maharashtra'):
    if not AGMARKNET_API_KEY:
        return None
    commodity = CROP_TO_AGMARKNET.get(crop_name.lower(), crop_name.title())
    base_url  = 'https://api.data.gov.in/resource/' + AGMARKNET_RESOURCE_ID
    filter_attempts = []

    if user_city:
        city_lower = user_city.lower()
        for city_key, markets in MAHARASHTRA_CITY_TO_MARKET.items():
            if city_key in city_lower or city_lower in city_key:
                for market in markets[:2]:
                    filter_attempts.append({
                        'api-key': AGMARKNET_API_KEY, 'format': 'json', 'limit': 10,
                        'filters[state.keyword]': 'Maharashtra',
                        'filters[commodity]': commodity,
                        'filters[market]': market,
                    })
                break

    filter_attempts += [
        {'api-key': AGMARKNET_API_KEY, 'format': 'json', 'limit': 100,
         'filters[state.keyword]': 'Maharashtra', 'filters[commodity]': commodity},
        {'api-key': AGMARKNET_API_KEY, 'format': 'json', 'limit': 100,
         'filters[state]': 'Maharashtra', 'filters[commodity]': commodity},
    ]

    for i, params in enumerate(filter_attempts):
        try:
            resp    = requests.get(base_url, params=params, timeout=10)
            if resp.status_code != 200: continue
            records = resp.json().get('records', [])
            if not records: continue
            maha_records = [r for r in records if 'maharashtra' in str(r.get('state','')).lower()]
            if not maha_records: continue

            local_records = []
            if user_city:
                city_lower = user_city.lower()
                for city_key, markets in MAHARASHTRA_CITY_TO_MARKET.items():
                    if city_key in city_lower or city_lower in city_key:
                        mkt_lower = [m.lower() for m in markets]
                        local_records = [
                            r for r in maha_records
                            if any(m in str(r.get('market','')).lower() for m in mkt_lower)
                        ]
                        break

            final_records = local_records if local_records else maha_records
            prices = sorted([(float(r.get('modal_price',0) or 0), r) for r in final_records], key=lambda x: x[0])
            valid  = [(p, r) for p, r in prices if p > 0]
            if not valid: continue
            rec     = valid[len(valid) // 2][1]
            modal_q = float(rec.get('modal_price', 0) or 0)
            if modal_q == 0: continue

            return {
                'modal_price': round(modal_q / 100, 2),
                'min_price':   round(float(rec.get('min_price', 0) or 0) / 100, 2),
                'max_price':   round(float(rec.get('max_price', 0) or 0) / 100, 2),
                'market':      f"{rec.get('market','')}, {rec.get('district','')}".strip(', ') or 'Maharashtra Mandi',
                'date':        rec.get('arrival_date', str(datetime.date.today())),
                'source':      'agmarknet',
                'state':       rec.get('state', 'Maharashtra'),
            }
        except Exception as e:
            print(f'[AGMARKNET] Attempt {i+1} error: {e}')
    return None


def get_smart_price(crop_name, season, weather=None, user_city=None):
    live = fetch_agmarknet_price(crop_name, user_city=user_city)
    if live:
        base_price = live['modal_price']
        source     = 'agmarknet'
        market     = live['market']
        mandi_date = live['date']
        raw_min    = live['min_price']
        raw_max    = live['max_price']
    else:
        base_price = FALLBACK_BASE_PRICES.get(crop_name.lower(), 28)
        source     = 'local'
        market     = 'APMC Maharashtra Historical Average'
        mandi_date = str(datetime.date.today())
        raw_min    = round(base_price * 0.88, 2)
        raw_max    = round(base_price * 1.15, 2)

    multiplier   = SEASON_MULTIPLIER.get(season.lower(), 1.0)
    weather_adj  = 1.0
    weather_note = None
    if weather:
        if weather.get('humidity', 0) > 75:
            weather_adj  = 1.08
            weather_note = f"High humidity ({weather['humidity']}%) -- price up 8%"
        if weather.get('temp', 0) > 38:
            weather_adj  = 1.12
            weather_note = f"Extreme heat ({weather['temp']}C) -- price up 12%"

    return {
        'price':        round(base_price * multiplier * weather_adj, 2),
        'min_price':    round(raw_min    * multiplier * weather_adj, 2),
        'max_price':    round(raw_max    * multiplier * weather_adj, 2),
        'base_price':   base_price,
        'source':       source,
        'market':       market,
        'mandi_date':   mandi_date,
        'season_mult':  multiplier,
        'weather_adj':  weather_adj,
        'weather_note': weather_note,
    }


# ============================================================
#  CROP DETECTION
# ============================================================
def detect_crop_from_image(image_bytes, media_type, filename=''):
    result = _detect_with_gemini(image_bytes, media_type)
    if result:
        print(f'[DETECT] Gemini succeeded: {result}')
        return result
    print('[DETECT] Gemini failed, trying CLIP...')
    result = _detect_with_clip(image_bytes)
    if result:
        print(f'[DETECT] CLIP succeeded: {result}')
        return result
    if filename:
        result = _detect_from_filename(filename)
        if result:
            print(f'[DETECT] Filename match: {result}')
            return result
    print('[DETECT] All methods failed')
    return None


def _detect_from_filename(filename):
    import re
    name = re.sub(r'\.(jpg|jpeg|png|webp|gif|heic|heif)$', '', filename.lower())
    name = re.sub(r'[_\-]', ' ', name)
    for crop in SUPPORTED_CROPS:
        if crop in name: return crop
    for syn, crop in SYNONYMS.items():
        if syn in name: return crop
    return None


def _normalize_crop_name(text):
    text = text.strip().lower()
    if text in SUPPORTED_CROPS: return text
    if text in SYNONYMS: return SYNONYMS[text]
    for crop in SUPPORTED_CROPS:
        if crop in text or text in crop: return crop
    for syn, crop in SYNONYMS.items():
        if syn in text: return crop
    return text


def _parse_gemini_response(raw_text):
    import re
    raw = re.sub(r'[^a-z \']', '', raw_text.strip().lower()).strip()
    for syn, crop in SYNONYMS.items():
        if syn in raw: return crop
    first = raw.split()[0] if raw.split() else ''
    if first in SUPPORTED_CROPS: return first
    if first in SYNONYMS: return SYNONYMS[first]
    for crop in SUPPORTED_CROPS:
        if crop in raw: return crop
    return first if len(first) > 2 else None


def _detect_with_gemini(image_bytes, media_type):
    import base64
    if not media_type:
        media_type = 'image/jpeg'

    if not GEMINI_API_KEY:
        print('[GEMINI] ❌ No API key found! Set GEMINI_API_KEY env variable.')
        return None

    print(f'[GEMINI] Key present: {GEMINI_API_KEY[:8]}... image={len(image_bytes)//1024}KB type={media_type}')
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')

    for model in GEMINI_MODELS:
        try:
            url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}'
            payload = {
                'contents': [{'parts': [
                    {'inline_data': {'mime_type': media_type, 'data': image_b64}},
                    {'text': GEMINI_PROMPT}
                ]}],
                'generationConfig': {'maxOutputTokens': 20, 'temperature': 0.0}
            }
            resp = requests.post(url, json=payload, timeout=30)
            print(f'[GEMINI] {model} status={resp.status_code}')

            if resp.status_code == 400:
                err = resp.json().get('error', {})
                print(f'[GEMINI] 400 error: {err.get("message","")[:200]}')
                # 400 usually means bad image format — try next model
                continue
            if resp.status_code == 401:
                print(f'[GEMINI] 401 INVALID KEY — update GEMINI_API_KEY')
                return None
            if resp.status_code == 403:
                print(f'[GEMINI] 403 KEY BLOCKED/QUOTA — get new key at aistudio.google.com')
                return None
            if resp.status_code == 429:
                print(f'[GEMINI] 429 rate limit')
                continue
            if resp.status_code == 404:
                print(f'[GEMINI] {model} not found, trying next')
                continue
            if resp.status_code != 200:
                print(f'[GEMINI] {resp.status_code}: {resp.text[:200]}')
                continue

            data       = resp.json()
            candidates = data.get('candidates', [])
            if not candidates:
                print(f'[GEMINI] No candidates in response')
                continue
            if candidates[0].get('finishReason') == 'SAFETY':
                print(f'[GEMINI] Safety filter triggered')
                continue

            raw_text = candidates[0]['content']['parts'][0]['text']
            print(f'[GEMINI] Raw response: "{raw_text}"')
            result = _parse_gemini_response(raw_text)
            print(f'[GEMINI] Parsed crop: {result}')
            if result and result in SUPPORTED_CROPS:
                return result

        except requests.exceptions.Timeout:
            print(f'[GEMINI] {model} timeout')
            continue
        except Exception as e:
            print(f'[GEMINI ERROR] {model}: {e}')
            continue

    return None


def _detect_with_clip(image_bytes):
    import base64
    CROP_LABELS = [
        'tomato vegetable','potato vegetable','onion vegetable','garlic bulb','ginger root',
        'brinjal eggplant','green capsicum','red chilli pepper','cauliflower','cabbage',
        'spinach leaves','carrot vegetable','radish','beetroot','okra ladyfinger',
        'green peas','cucumber','pumpkin','watermelon','mango fruit','banana fruit',
        'apple fruit','grapes','orange fruit','papaya','wheat grain','rice grain',
        'corn maize','rose flower','marigold flower','jasmine flower','sunflower',
    ]
    LABEL_TO_CROP = {
        'tomato vegetable':'tomato','potato vegetable':'potato','onion vegetable':'onion',
        'garlic bulb':'garlic','ginger root':'ginger','brinjal eggplant':'brinjal',
        'green capsicum':'capsicum','red chilli pepper':'chilli','cauliflower':'cauliflower',
        'cabbage':'cabbage','spinach leaves':'spinach','carrot vegetable':'carrot',
        'radish':'radish','beetroot':'beetroot','okra ladyfinger':'okra','green peas':'peas',
        'cucumber':'cucumber','pumpkin':'pumpkin','watermelon':'watermelon','mango fruit':'mango',
        'banana fruit':'banana','apple fruit':'apple','grapes':'grapes','orange fruit':'orange',
        'papaya':'papaya','wheat grain':'wheat','rice grain':'rice','corn maize':'corn',
        'rose flower':'rose','marigold flower':'marigold','jasmine flower':'jasmine','sunflower':'sunflower',
    }
    try:
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        resp = requests.post(
            'https://api-inference.huggingface.co/models/openai/clip-vit-base-patch32',
            headers={'Content-Type': 'application/json'},
            json={'inputs': image_b64, 'parameters': {'candidate_labels': CROP_LABELS}},
            timeout=25
        )
        if resp.status_code == 503:
            import time; time.sleep(15)
            resp = requests.post(
                'https://api-inference.huggingface.co/models/openai/clip-vit-base-patch32',
                headers={'Content-Type': 'application/json'},
                json={'inputs': image_b64, 'parameters': {'candidate_labels': CROP_LABELS}},
                timeout=30
            )
        if resp.status_code != 200:
            print(f'[CLIP] status={resp.status_code}')
            return None
        results   = resp.json()
        if not isinstance(results, list) or not results: return None
        best_label = results[0].get('label', '').lower().strip()
        best_score = results[0].get('score', 0)
        print(f'[CLIP] best={best_label} score={best_score:.3f}')
        if best_score < 0.10: return None
        return LABEL_TO_CROP.get(best_label, best_label.split()[0])
    except Exception as e:
        print(f'[CLIP ERROR] {e}')
        return None


# ============================================================
#  WEATHER
# ============================================================
def get_weather(city):
    try:
        resp = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric',
            timeout=5
        )
        data = resp.json()
        if resp.status_code == 200:
            w = {
                'city': city, 'temp': round(data['main']['temp']),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind': data['wind']['speed'],
                'feels_like': round(data['main']['feels_like']),
            }
            w['advisory'] = _generate_advisory(w)
            return w
    except Exception as e:
        print(f'[WEATHER ERROR] {e}')
    return None


# ============================================================
#  MAIN PREDICTOR ROUTE
# ============================================================
@ml.route('/price-predictor', methods=['GET', 'POST'])
def price_predictor():
    prediction    = None
    weather       = None
    detected_crop = None
    error_message = None
    ai_failed     = False

    if request.method == 'POST':
        season    = request.form.get('season', '').lower()
        quantity  = float(request.form.get('quantity', 1))
        crop_name = None

        user_city = request.form.get('user_city', '').strip()
        if not user_city:
            user_city = session.get('user_city', '')
        if user_city:
            session['user_city'] = user_city

        manual_crop = request.form.get('manual_crop', '').strip().lower()

        if 'crop_image' in request.files:
            file = request.files['crop_image']
            if file and file.filename != '':
                fname       = file.filename or 'upload.jpg'
                image_bytes = file.read()
                print(f'[UPLOAD] fname={fname} raw_size={len(image_bytes)} bytes')

                if len(image_bytes) == 0:
                    file.stream.seek(0)
                    image_bytes = file.stream.read()
                    print(f'[UPLOAD] Stream fallback size={len(image_bytes)} bytes')

                if len(image_bytes) == 0:
                    ai_failed     = True
                    error_message = 'Image upload failed — please try again or type the crop name below.'
                else:
                    image_bytes, media_type = compress_image(image_bytes)
                    detected = detect_crop_from_image(image_bytes, media_type, fname)

                    if detected:
                        detected_crop = detected
                        crop_name     = detected
                    elif manual_crop:
                        crop_name     = _normalize_crop_name(manual_crop)
                        detected_crop = crop_name
                    else:
                        ai_failed = True
                        error_message = 'Could not detect crop from image. Please type the crop name below.'

        if not crop_name and manual_crop:
            crop_name     = _normalize_crop_name(manual_crop)
            detected_crop = crop_name

        if crop_name and season:
            price_data = get_smart_price(crop_name, season, weather, user_city=user_city)
            prediction = {
                'crop':             crop_name.title(),
                'season':           season.title(),
                'price':            price_data['price'],
                'total':            round(price_data['price'] * quantity, 2),
                'quantity':         quantity,
                'min_price':        price_data['min_price'],
                'max_price':        price_data['max_price'],
                'base_price':       price_data['base_price'],
                'source':           price_data['source'],
                'market':           price_data['market'],
                'mandi_date':       price_data['mandi_date'],
                'season_mult':      price_data['season_mult'],
                'weather_adj':      price_data['weather_adj'],
                'weather_note':     price_data['weather_note'],
                'weather_adjusted': weather is not None,
                'ai_detected':      detected_crop is not None,
            }
        elif not crop_name and not error_message and not ai_failed:
            error_message = 'Please upload a crop photo or type the crop name.'

    return render_template('ml/predictor.html',
                           prediction=prediction, weather=weather,
                           detected_crop=detected_crop,
                           error_message=error_message,
                           ai_failed=ai_failed)


# ============================================================
#  DEBUG ROUTE — visit /debug-vision on your phone to check
# ============================================================
@ml.route('/debug-vision')
def debug_vision():
    from flask import jsonify
    key = GEMINI_API_KEY
    key_status = 'MISSING' if not key else f'Present ({key[:8]}...{key[-4:]})'

    # Quick API test
    api_test = 'not tested'
    if key:
        try:
            resp = requests.get(
                f'https://generativelanguage.googleapis.com/v1beta/models?key={key}',
                timeout=8
            )
            if resp.status_code == 200:
                api_test = '✅ KEY VALID'
            elif resp.status_code == 400:
                api_test = '❌ BAD REQUEST'
            elif resp.status_code == 401:
                api_test = '❌ INVALID KEY'
            elif resp.status_code == 403:
                api_test = '❌ KEY BLOCKED OR QUOTA EXCEEDED'
            else:
                api_test = f'❌ HTTP {resp.status_code}'
        except Exception as e:
            api_test = f'❌ Connection error: {e}'

    return jsonify({
        'gemini_key': key_status,
        'api_test': api_test,
        'env_vars': {k: '***' for k in os.environ if 'KEY' in k or 'API' in k},
    })


# ============================================================
#  ML ENGINE - BEST TIME TO SELL
# ============================================================
HISTORICAL_APMC_DATA = {
    'tomato': [38,32,24,19,21,29,34,38,32,27,30,35,36,28,20,17,19,27,31,36,29,24,27,32,37,31,23,18,20,28,33,37,31,25,29,34],
    'onion':  [28,22,19,24,32,38,44,40,33,25,22,25,24,18,17,21,29,34,40,37,30,22,19,22,26,20,18,23,31,36,42,39,31,23,21,24],
    'potato': [20,17,13,15,20,22,24,22,17,15,16,18,17,14,11,13,17,19,21,19,15,13,14,16,19,16,12,14,19,21,23,21,16,14,15,17],
    'wheat':  [23,21,19,26,29,27,25,23,21,22,23,24,22,20,18,25,28,26,24,22,20,21,22,23,24,22,20,27,30,28,26,24,22,23,24,25],
    'mango':  [85,78,62,46,42,57,72,82,88,93,97,90,80,74,58,44,40,54,68,78,84,89,93,86,83,77,61,45,41,56,70,81,87,92,96,89],
    'rice':   [40,38,35,36,39,42,40,37,32,29,33,38,37,35,32,33,36,39,37,34,29,27,30,35,39,37,34,35,38,41,39,36,31,28,32,37],
    'rose':   [190,210,165,145,135,125,135,145,155,165,185,205,175,195,155,138,128,118,128,138,148,158,178,198,185,205,160,142,132,122,132,142,152,162,182,202],
    'marigold':[52,47,36,31,29,31,36,42,52,84,105,92,48,43,33,29,27,29,33,38,48,78,98,86,51,46,35,30,28,30,35,41,51,82,103,90],
    'jasmine': [185,163,153,143,163,205,225,214,193,183,204,224,176,155,145,136,155,195,215,205,184,174,194,213,182,160,150,140,160,201,221,211,190,180,200,220],
}

MONTH_NAMES = {1:'January',2:'February',3:'March',4:'April',5:'May',6:'June',7:'July',8:'August',9:'September',10:'October',11:'November',12:'December'}


def _train_model(crop):
    try:
        from sklearn.linear_model import Ridge
        data = HISTORICAL_APMC_DATA.get(crop.lower())
        if not data: return None, None
        n = len(data)
        months_of_year = np.array([(i % 12) + 1 for i in range(n)], dtype=float)
        year_index     = np.array([i // 12 for i in range(n)], dtype=float)
        sin_m = np.sin(2 * np.pi * months_of_year / 12)
        cos_m = np.cos(2 * np.pi * months_of_year / 12)
        X = np.column_stack([months_of_year, months_of_year**2, months_of_year**3, sin_m, cos_m, year_index])
        y = np.array(data, dtype=float)
        model = Ridge(alpha=1.0)
        model.fit(X, y)
        return model, None
    except ImportError:
        return None, None
    except Exception as e:
        print(f'[ML] Training error for {crop}: {e}')
        return None, None


def _predict_monthly_prices_ml(crop, target_year_index=3):
    model, _ = _train_model(crop)
    if model is not None:
        predictions = {}
        for m in range(1, 13):
            sin_m = np.sin(2 * np.pi * m / 12)
            cos_m = np.cos(2 * np.pi * m / 12)
            x = np.array([[m, m**2, m**3, sin_m, cos_m, target_year_index]])
            pred = float(model.predict(x)[0])
            predictions[m] = round(max(pred, 5.0), 2)
        return predictions, 'ml'
    data = HISTORICAL_APMC_DATA.get(crop.lower())
    if not data: return None, None
    predictions = {}
    for m in range(1, 13):
        month_values = [data[(year * 12) + (m - 1)] for year in range(len(data) // 12)]
        predictions[m] = round(float(np.mean(month_values)), 2)
    return predictions, 'average'


@ml.route('/best-time-to-sell', methods=['GET', 'POST'])
def best_time_to_sell():
    result          = None
    crops_available = list(HISTORICAL_APMC_DATA.keys())

    if request.method == 'POST':
        crop     = request.form.get('crop', '').lower()
        quantity = float(request.form.get('quantity', 100))

        if crop in HISTORICAL_APMC_DATA:
            prices, method = _predict_monthly_prices_ml(crop)
            if prices:
                current_month = datetime.datetime.now().month
                best_month    = max(prices, key=prices.get)
                worst_month   = min(prices, key=prices.get)
                future = {}
                for i in range(6):
                    m = ((current_month - 1 + i) % 12) + 1
                    future[MONTH_NAMES[m]] = prices[m]
                best_upcoming = max(future, key=future.get)
                trend_data    = [{'month': MONTH_NAMES[m], 'price': prices[m]} for m in range(1, 13)]
                confidence    = 'ML Model' if method == 'ml' else '3-Year APMC Historical Average'
                result = {
                    'crop': crop.title(), 'quantity': quantity,
                    'best_month': MONTH_NAMES[best_month], 'best_price': prices[best_month],
                    'worst_month': MONTH_NAMES[worst_month], 'worst_price': prices[worst_month],
                    'current_month': MONTH_NAMES[current_month], 'current_price': prices[current_month],
                    'best_upcoming': best_upcoming, 'best_upcoming_price': future[best_upcoming],
                    'trend_data': trend_data,
                    'best_earning': round(prices[best_month] * quantity, 2),
                    'current_earning': round(prices[current_month] * quantity, 2),
                    'extra_earning': round((prices[best_month] - prices[current_month]) * quantity, 2),
                    'method': method, 'confidence': confidence, 'data_years': 3,
                    'data_points': len(HISTORICAL_APMC_DATA[crop]),
                }

    return render_template('ml/best_time.html', result=result, crops_available=crops_available)


# ============================================================
#  WEATHER BY GPS COORDS
# ============================================================
@ml.route('/get-weather-by-coords')
def get_weather_by_coords():
    from flask import jsonify
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if not lat or not lon:
        return jsonify({'success': False, 'error': 'No coordinates'})

    weather   = None
    city_name = None

    try:
        resp = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric',
            timeout=6
        )
        data = resp.json()
        if resp.status_code == 200:
            city_name = _reverse_geocode(lat, lon) or data.get('name', 'Your Location')
            weather   = {
                'city': city_name, 'lat': round(lat,4), 'lon': round(lon,4),
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'wind': round(data['wind']['speed'], 1),
                'pressure': data['main']['pressure'],
                'source': 'OpenWeatherMap',
            }
    except Exception as e:
        print(f'[WEATHER ERROR] {e}')

    if not weather:
        try:
            weather = _get_weather_open_meteo(lat, lon)
            if weather:
                city_name = weather.get('city', '')
        except Exception as e:
            print(f'[OPEN-METEO ERROR] {e}')

    if not weather:
        return jsonify({'success': False, 'error': 'Weather unavailable'})

    weather['advisory'] = _generate_advisory(weather)
    if city_name:
        city_short = city_name.split(',')[0].strip()
        weather['city_short'] = city_short
        session['user_city'] = city_short
    else:
        weather['city_short'] = ''

    return jsonify({'success': True, 'weather': weather})


def _reverse_geocode(lat, lon):
    try:
        resp = requests.get(
            f'https://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={WEATHER_API_KEY}',
            timeout=5
        )
        res = resp.json()
        if res:
            parts = [p for p in [res[0].get('name'), res[0].get('state')] if p]
            return ', '.join(parts) or None
    except: pass
    return None


def _get_weather_open_meteo(lat, lon):
    resp = requests.get(
        f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}'
        f'&current=temperature_2m,relative_humidity_2m,apparent_temperature,'
        f'weather_code,wind_speed_10m,surface_pressure&wind_speed_unit=ms&timezone=Asia%2FKolkata',
        timeout=8
    )
    data = resp.json()
    c    = data.get('current', {})
    code = c.get('weather_code', 0)
    city = _reverse_geocode_nominatim(lat, lon) or f'{round(lat,2)}N, {round(lon,2)}E'
    return {
        'city': city, 'lat': round(lat,4), 'lon': round(lon,4),
        'temp': round(c.get('temperature_2m', 0)),
        'feels_like': round(c.get('apparent_temperature', 0)),
        'humidity': c.get('relative_humidity_2m', 0),
        'description': _wmo_desc(code), 'icon': _wmo_icon(code),
        'wind': round(c.get('wind_speed_10m', 0), 1),
        'pressure': round(c.get('surface_pressure', 1013)),
        'source': 'Open-Meteo',
    }


def _reverse_geocode_nominatim(lat, lon):
    try:
        resp = requests.get(
            f'https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&zoom=10',
            timeout=5, headers={'User-Agent': 'AgroConnect/1.0'}
        )
        addr  = resp.json().get('address', {})
        parts = []
        for k in ['village','suburb','town','city','state_district','state']:
            if addr.get(k):
                parts.append(addr[k])
                if len(parts) == 2: break
        return ', '.join(parts) or None
    except: return None


def _wmo_desc(code):
    WMO = {0:'Clear Sky',1:'Mainly Clear',2:'Partly Cloudy',3:'Overcast',45:'Fog',51:'Light Drizzle',61:'Slight Rain',63:'Moderate Rain',65:'Heavy Rain',80:'Rain Showers',95:'Thunderstorm'}
    return WMO.get(code, 'Variable Conditions')


def _wmo_icon(code):
    if code == 0: return '01d'
    if code in (1,2): return '02d'
    if code == 3: return '04d'
    if code in (45,48): return '50d'
    if code in (51,53,55,61,63,65): return '10d'
    if code in (80,81,82): return '09d'
    if code in (95,96,99): return '11d'
    return '03d'


def _generate_advisory(weather):
    advisories = []
    temp = weather.get('temp', 25)
    hum  = weather.get('humidity', 50)
    desc = weather.get('description', '').lower()
    if 'rain' in desc or 'drizzle' in desc: advisories.append('Rain detected -- harvest moisture-sensitive crops immediately.')
    if 'thunder' in desc: advisories.append('Thunderstorm -- avoid open fields.')
    if temp >= 40: advisories.append(f'Extreme heat ({temp}C) -- water crops in early morning only.')
    elif temp >= 35: advisories.append(f'High temp ({temp}C) -- increase irrigation.')
    elif temp <= 10: advisories.append(f'Cold ({temp}C) -- protect frost-sensitive crops.')
    if hum >= 80: advisories.append(f'High humidity ({hum}%) -- watch for fungal diseases.')
    if hum <= 25: advisories.append(f'Dry air ({hum}%) -- ideal for grain storage.')
    if 'clear' in desc: advisories.append('Clear sky -- excellent harvesting conditions.')
    if not advisories: advisories.append('Normal conditions -- continue regular farming activities.')
    return advisories


@ml.route('/test-vision')
def test_vision():
    return 'AgroConnect Detection: Gemini Vision (primary) + HuggingFace CLIP (fallback)'