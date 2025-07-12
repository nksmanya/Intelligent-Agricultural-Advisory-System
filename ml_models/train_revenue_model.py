import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle

df = pd.read_csv('revenue_dataset.csv')
X = df[['acres', 'active_crops', 'soil_health', 'other_feature']]
y = df['monthly_revenue']

model = RandomForestRegressor()
model.fit(X, y)

with open('revenue_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("✅ Revenue Model Trained & Saved")