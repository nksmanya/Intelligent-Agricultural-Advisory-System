import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import pickle

# Load your dataset
data = pd.read_csv('Crop_recommendation.csv')

# Features and target (adjust according to your dataset columns)
X = data.drop('label', axis=1)  # Replace 'label' if your target column has a different name
y = data['label']               # Target column name (crop name)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# Save the trained model
with open('crop_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model trained and saved successfully.")
