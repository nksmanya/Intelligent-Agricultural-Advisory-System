from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import requests
import random
import pickle
from datetime import datetime, timedelta
import pandas as pd
from flask import jsonify
from werkzeug.utils import secure_filename
import os
import requests

app = Flask(__name__)
app.secret_key = 'agri-secret'  # For session & flash messages

# Initialize SQLite DB for users
def init_db():
    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            location TEXT,
            soil_type TEXT,
            land_size REAL,
            water_source TEXT,
            preferred_crops TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize Crop Table
def init_crop_table():
    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS current_crops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            crop_name TEXT NOT NULL,
            seeding_date TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

# First define the functions, then call them
init_db()
init_crop_table()


# Load ML Models (only once)
soil_model = pickle.load(open('ml_models/soil_health_model.pkl', 'rb'))
revenue_model = pickle.load(open('ml_models/revenue_model.pkl', 'rb'))

# Tamil Nadu Crop Dataset
crop_df = pd.read_csv("crops_tamilnadu_fixed.csv")

# Home → Login Page
@app.route('/')
def home():
    return render_template('index.html')

# Chatbot Route for Pest & Disease Solutions
@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.form.get('message', '').lower()

    # Simple Rule-based Chatbot
    if "aphid" in user_msg:
        reply = "Solution: Use neem oil spray to control aphids. Also, introducing ladybugs can help."
    elif "powdery mildew" in user_msg:
        reply = "Solution: Apply a baking soda spray (1 tbsp baking soda + 1 tsp liquid soap + 1 liter water)."
    elif "root rot" in user_msg:
        reply = "Solution: Reduce watering, improve soil drainage, and remove affected roots."
    elif "fungus" in user_msg or "fungal" in user_msg:
        reply = "Solution: Use organic fungicides like sulfur or copper-based sprays. Ensure proper air circulation."
    elif "caterpillar" in user_msg:
        reply = "Solution: Use biological control like Bacillus thuringiensis (Bt) or neem-based pesticides."
    else:
        reply = "Sorry, I don't have a solution for that yet. Try asking about aphids, powdery mildew, root rot, fungus, or caterpillars."

    return jsonify({"reply": reply})

# Login Route
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = user[1]  # Save user's name in session
        return redirect('/dashboard')
    else:
        flash("Invalid credentials!")
        return redirect('/')

# Register Page
@app.route('/register')
def register():
    return render_template('register.html')

# Register Route
@app.route('/register-user', methods=['POST'])
def register_user():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    location = request.form['location']
    soil_type = request.form['soil_type']
    land_size = request.form['land_size']
    water_source = request.form['water_source']
    preferred_crops = request.form['preferred_crops']

    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO users (name, email, password, location, soil_type, land_size, water_source, preferred_crops)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, password, location, soil_type, land_size, water_source, preferred_crops))
        conn.commit()
        flash("Registration successful! Please login.")
        return redirect('/')
    except sqlite3.IntegrityError:
        flash("Email already exists!")
        return redirect('/register')
    finally:
        conn.close()

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        conn = sqlite3.connect('agri.db')
        cursor = conn.cursor()
        cursor.execute("SELECT soil_type, land_size FROM users WHERE name=?", (session['user'],))
        result = cursor.fetchone()
        conn.close()

        if result:
            soil_type, land_size = result
            soil_inputs = [[6.5, 30, 150, 80, 60]]  # Dummy Inputs
            soil_health = round(soil_model.predict(soil_inputs)[0], 2)
            revenue_inputs = [[land_size, 5, soil_health, 2]]
            monthly_revenue = round(revenue_model.predict(revenue_inputs)[0], 2)

            farm_stats = {
                'active_crops': 5,
                'acres': land_size,
                'soil_health': f"{soil_health}%",
                'monthly_revenue': f"₹{monthly_revenue}K"
            }

            return render_template('dashboard.html', name=session['user'], farm_stats=farm_stats)
        else:
            flash("Farm details missing!")
            return redirect('/')
    else:
        return redirect('/')

# Weather Page
@app.route('/weather')
def weather():
    if 'user' in session:
        conn = sqlite3.connect('agri.db')
        cursor = conn.cursor()
        cursor.execute("SELECT location FROM users WHERE name=?", (session['user'],))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            lat, lon = map(float, result[0].split(','))
            api_key = "63f6d64abf2532c74319740224e1fc24"
            current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
            current_weather = requests.get(current_url).json()

            past_weather = []
            if 'main' in current_weather:
                current_temp = current_weather['main']['temp']
                current_humidity = current_weather['main']['humidity']

                for i in range(5):
                    date = (datetime.now() - timedelta(days=i + 1)).strftime('%Y-%m-%d')
                    temp = round(current_temp + random.uniform(-2, 2), 2)
                    humidity = round(current_humidity + random.uniform(-5, 5), 2)
                    humidity = max(0, min(100, humidity))
                    past_weather.append({'date': date, 'temp': temp, 'humidity': humidity})

            future_weather = []
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            for month in months:
                predicted_temp = round(current_temp + random.uniform(-3, 3), 2)
                predicted_humidity = round(current_humidity + random.uniform(-10, 10), 2)
                predicted_humidity = max(0, min(100, predicted_humidity))
                future_weather.append({'Month': month, 'Predicted Temp': predicted_temp, 'Predicted Humidity': predicted_humidity})

            annual_rainfall_data = []
            annual_rainfall_total = 0
            for month in months:
                rainfall = round(random.uniform(50, 300), 2)
                annual_rainfall_total += rainfall
                annual_rainfall_data.append({'Month': month, 'Rainfall': rainfall})

            annual_rainfall_total = round(annual_rainfall_total, 2)

            return render_template('weather.html',
                                   name=session['user'],
                                   current_weather=current_weather,
                                   past_weather=past_weather,
                                   future_weather=future_weather,
                                   annual_rainfall_data=annual_rainfall_data,
                                   annual_rainfall_total=annual_rainfall_total)
        else:
            return "Farm location not found in your profile."
    else:
        return redirect('/')

# Tamil Nadu Crop Recommendation
@app.route('/tncrop', methods=['GET', 'POST'])
def tn_crop():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    cursor.execute("SELECT soil_type, location FROM users WHERE name=?", (session['user'],))
    result = cursor.fetchone()
    conn.close()

    if not result:
        flash("User profile incomplete!")
        return redirect('/dashboard')

    soil_type, location = result
    lat, lon = map(float, location.split(','))

    # Fetch current temperature
    api_key = "63f6d64abf2532c74319740224e1fc24"
    current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    current_weather = requests.get(current_url).json()
    current_temp = current_weather['main']['temp'] if 'main' in current_weather else 28.0

    # Simulate Annual Rainfall (can also re-use from weather page)
    annual_rainfall = sum([round(random.uniform(50, 300), 2) for _ in range(12)])

    crops = []
    if request.method == 'POST':
        ph = float(request.form['ph'])

        # Load your Tamil Nadu crop dataset
        import pandas as pd
        df = pd.read_csv("crops_tamilnadu_fixed.csv")

        # Filter crops
        filtered = df[
            (df['MinTemp'] <= current_temp) & (df['MaxTemp'] >= current_temp) &
            (df['MinPH'] <= ph) & (df['MaxPH'] >= ph) &
            (df['MinRainfall'] <= annual_rainfall) & (df['MaxRainfall'] >= annual_rainfall) &
            (df['SoilType'].str.lower().str.contains(soil_type.lower()))
        ]

        crops = filtered.to_dict(orient='records')

    return render_template('tncrop.html',
                           name=session['user'],
                           soil_type=soil_type,
                           temp=current_temp,
                           rainfall=annual_rainfall,
                           crops=crops)
# Pest & Disease Guide Page
@app.route('/pest')
def pest():
    return render_template('pest.html')

# Dummy Model Prediction Function (Replace with real ML model later)
def dummy_disease_detector(image_path):
    # Example Dummy Logic
    return "Powdery Mildew (Simulated Result)"

@app.route('/detect_disease', methods=['POST'])
def detect_disease():
    if 'image' not in request.files:
        flash('No image uploaded!')
        return redirect('/pest.html')

    image = request.files['image']
    if image.filename == '':
        flash('No selected image!')
        return redirect('/pest.html')

    filename = secure_filename(image.filename)
    filepath = os.path.join("uploads", filename)
    os.makedirs("uploads", exist_ok=True)
    image.save(filepath)

    # Dummy Disease Detection (Replace this with your actual ML model later)
    disease_result = dummy_disease_detector(filepath)

    # Remove image after detection (Optional)
    os.remove(filepath)

    # Render pest.html with result
    return render_template('pest.html', disease_result=disease_result)

@app.route('/tips.html')
def tips():
    return render_template('tips.html')

@app.route('/news.html')
def agri_news():
    api_key = 'df10fb765da649de9702060cfed0500f'
    url = (
        f"https://newsapi.org/v2/everything?"
        f"q=agriculture OR farming OR farmers OR agri OR irrigation OR soil&"
        f"apiKey={api_key}&"
        f"language=en&"
        f"pageSize=15&"
        f"sortBy=publishedAt"
    )

    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get('articles', [])

        if not articles:
            print("No articles fetched from API.")
        else:
            print(f"Fetched {len(articles)} articles.")
            
    except Exception as e:
        articles = []
        print("Error fetching news:", e)

    return render_template('news.html', articles=articles)
@app.route('/current_crop', methods=['GET', 'POST'])
def current_crop():
    if 'user' not in session:
        return redirect('/')

    conn = sqlite3.connect('agri.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, soil_type, location FROM users WHERE name=?", (session['user'],))
    user_data = cursor.fetchone()

    if not user_data:
        flash("User data missing!")
        return redirect('/dashboard')

    user_id, soil_type, location = user_data

    # Save crop data
    if request.method == 'POST':
        crop_name = request.form.get('crop_name')
        seeding_date = request.form.get('seeding_date')

        if crop_name and seeding_date:
            cursor.execute("INSERT INTO current_crops (user_id, crop_name, seeding_date) VALUES (?, ?, ?)",
                           (user_id, crop_name, seeding_date))
            conn.commit()
            flash("Crop added successfully!")
            return redirect(url_for('current_crop'))

    # Fetch all crops for user
    cursor.execute("SELECT crop_name, seeding_date FROM current_crops WHERE user_id=? ORDER BY seeding_date DESC", (user_id,))
    crops = cursor.fetchall()

    # Weather Info
    lat, lon = map(float, location.split(','))
    api_key = "63f6d64abf2532c74319740224e1fc24"
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    weather = requests.get(weather_url).json()

    current_temp = weather.get('main', {}).get('temp', '--')
    humidity = weather.get('main', {}).get('humidity', '--')
    weather_desc = weather.get('weather', [{}])[0].get('description', '--')

    conn.close()

    # Dummy IoT Simulation (replace later)
    iot_humidity = round(random.uniform(20, 60), 1)
    water_recommendation = "Water the crops today." if iot_humidity < 30 else "No watering needed."

    return render_template('current_crop.html',
                           name=session['user'],
                           crops=crops,
                           soil_type=soil_type,
                           current_temp=current_temp,
                           humidity=humidity,
                           weather_desc=weather_desc,
                           iot_humidity=iot_humidity,
                           water_recommendation=water_recommendation)
@app.route('/marketprice.html')
def market_price():
    csv_path = "crop_price_dataset.csv"

    try:
        df = pd.read_csv(csv_path)
        print("✅ CSV Loaded:", df.shape)
    except Exception as e:
        print("❌ Error reading CSV:", e)
        return "Error reading CSV file."

    # Check required columns
    if not {'month', 'commodity_name', 'avg_modal_price'}.issubset(df.columns):
        print("❌ Missing required columns in CSV!")
        return "CSV is missing required columns."

    df['month'] = pd.to_datetime(df['month'], errors='coerce')
    df = df.dropna(subset=['month'])

    COMMODITIES = ["Tomato", "Potato", "Onion", "Jowar(Sorghum)", "Coconut", "Groundnut",
                   "Turmeric", "Ginger (Dry)", "Barley", "Millets", "Sugarcane", "Coffee",
                   "Cotton", "Sugar", "Rice", "Wheat", "Maize"]

    results = []

    for commodity in COMMODITIES:
        commodity_data = df[df['commodity_name'] == commodity].sort_values('month')

        if commodity_data.empty:
            print(f"⚠️ No data for {commodity}")
            continue

        last_two = commodity_data.tail(2).dropna(subset=['avg_modal_price'])

        try:
            last_prices = last_two['avg_modal_price'].astype(float).values
        except Exception as e:
            print(f"⚠️ Error converting prices for {commodity}: {e}")
            continue

        if len(last_prices) < 2:
            print(f"⚠️ Not enough data for {commodity}")
            continue

        last_two_months = last_two[['month', 'avg_modal_price']].copy()
        last_two_months['month'] = last_two_months['month'].dt.strftime('%Y-%m')

        slope = last_prices[-1] - last_prices[-2]
        next_six = []
        for i in range(1, 7):
            future_month = (last_two['month'].max() + pd.DateOffset(months=i)).strftime('%Y-%m')
            predicted = max(0, last_prices[-1] + i * slope)
            next_six.append({
                'month': future_month,
                'predicted_price': round(predicted, 2)
            })

        print(f"✅ {commodity} → Predicted")

        results.append({
            'commodity': commodity,
            'last_two': last_two_months.to_dict(orient='records'),
            'next_six': next_six
        })

    print("🟢 Total commodities processed:", len(results))

    return render_template('marketprice.html', results=results)


@app.route('/soilreport', methods=['GET', 'POST'])
def soil_report():
    soil_quality = None

    if request.method == 'POST':
        if 'fetch_iot' in request.form:
            # Simulate IoT data fetch (you can replace this with real sensor fetch later)
            ph = 6.8
            nitrogen = 150
            phosphorus = 50
            potassium = 120
            moisture = 40
        else:
            # Manual input
            ph = float(request.form['ph'])
            nitrogen = float(request.form['nitrogen'])
            phosphorus = float(request.form['phosphorus'])
            potassium = float(request.form['potassium'])
            moisture = float(request.form['moisture'])

        # Simple Soil Quality Calculation (You can make this smarter later)
        score = 0
        if 6 <= ph <= 7.5:
            score += 20
        if 100 <= nitrogen <= 200:
            score += 20
        if 40 <= phosphorus <= 80:
            score += 20
        if 100 <= potassium <= 200:
            score += 20
        if 30 <= moisture <= 60:
            score += 20

        soil_quality = score  # Out of 100

    return render_template('soilreport.html', soil_quality=soil_quality)


# AI-Powered Agri Dashboard
@app.route('/ai-dashboard')
def ai_dashboard():
    return render_template('ai_dashboard.html')



# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%B %d, %Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except:
        return value


if __name__ == "__main__":
    app.run(debug=True)