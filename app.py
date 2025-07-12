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

# Initialize SQLite DB
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

init_db()  # Initialize DB

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

if __name__ == "__main__":
    app.run(debug=True)