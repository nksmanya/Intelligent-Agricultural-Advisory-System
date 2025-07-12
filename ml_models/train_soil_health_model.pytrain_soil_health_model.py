import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import pickle

# Load dataset
data = pd.read_csv('soil_health_dataset.csv')

X = data[['ph', 'moisture', 'nitrogen', 'potassium', 'phosphorus']]
y = data['soil_health']

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Save Model
with open('soil_health_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Soil Health Model Trained & Saved as soil_health_model.pkl")
