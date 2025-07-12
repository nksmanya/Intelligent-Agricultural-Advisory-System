import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle

df = pd.read_csv('soil_health_dataset.csv')
X = df[['pH', 'moisture', 'N', 'K', 'P']]
y = df['soil_health']

model = RandomForestRegressor()
model.fit(X, y)

with open('soil_health_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Soil Health Model Trained & Saved")
