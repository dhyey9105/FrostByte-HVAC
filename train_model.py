import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
import pickle

# 1. Load Data from Database
conn = sqlite3.connect('hvac_data.db')
df = pd.read_sql_query("SELECT * FROM hvac_logs", conn)
conn.close()

# 2. Prepare Features (X) and Target (y)
# We want to predict 'energy_consumption' based on temp and occupancy
X = df[['outside_temp', 'occupancy']]
y = df['energy_consumption']

# 3. Train Model
print("Training AI Model...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=100)
model.fit(X_train, y_train)

# 4. Save the Model (So the app can load it quickly)
with open('frostbyte_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print(f"✅ Model Trained! Accuracy Score: {model.score(X_test, y_test):.2f}")
print("Saved as 'frostbyte_model.pkl'")