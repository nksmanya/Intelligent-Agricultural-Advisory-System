from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pandas as pd
from datetime import datetime
import logging

# Initialize FastAPI app
app = FastAPI()

# Mount templates and static folders
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable logging
logging.basicConfig(level=logging.INFO)

# Load dataset
csv_path = "crop_price_dataset.csv"
df = pd.read_csv(csv_path)

# Ensure proper date parsing
df['month'] = pd.to_datetime(df['month'], errors='coerce')
df = df.dropna(subset=['month'])

# List of commodities
COMMODITIES = [
    "Tomato", "Potato", "Onion",
    "Jowar(Sorghum)", "Coconut", "Groundnut",
    "Turmeric", "Ginger (Dry)", "Barley",
    "Millets", "Sugarcane", "Coffee",
    "Cotton", "Sugar", "Rice", "Wheat", "Maize"
]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    results = []

    for commodity in COMMODITIES:
        commodity_data = df[df['commodity_name'] == commodity].sort_values('month')

        if commodity_data.empty:
            logging.info(f"No data for {commodity}")
            continue

        # Try to get June & July 2025
        target_months = [
            pd.Timestamp('2025-06-01'),
            pd.Timestamp('2025-07-01')
        ]
        last_two = commodity_data[commodity_data['month'].isin(target_months)].sort_values('month')

        # Fallback: use last 2 rows if needed
        if len(last_two) < 2:
            last_two = commodity_data.tail(2)

        if len(last_two) < 2:
            logging.info(f"Not enough rows for {commodity}")
            continue

        # Remove rows with missing price
        last_two = last_two.dropna(subset=['avg_modal_price'])

        try:
            last_prices = last_two['avg_modal_price'].astype(float).values
        except Exception as e:
            logging.error(f"Error converting prices for {commodity}: {e}")
            continue

        if len(last_prices) < 2:
            logging.info(f"Invalid last prices for {commodity}")
            continue

        # Format for display
        last_two_months = last_two[['month', 'avg_modal_price']].copy()
        last_two_months['month'] = last_two_months['month'].dt.strftime('%Y-%m')

        # Predict next 6 months
        slope = last_prices[-1] - last_prices[-2]
        next_six = []
        for i in range(1, 7):
            future_month = (last_two['month'].max() + pd.DateOffset(months=i)).strftime('%Y-%m')
            predicted = max(0, last_prices[-1] + i * slope)
            next_six.append({
                'month': future_month,
                'predicted_price': round(predicted, 2)
            })

        results.append({
            'commodity': commodity,
            'last_two': last_two_months.to_dict(orient='records'),
            'next_six': next_six
        })

    return templates.TemplateResponse("index.html", {
        "request": request,
        "results": results
    })
