import pandas as pd

try:
    df = pd.read_csv('real_data.csv')
    print("✅ CSV Loaded Successfully!")
    print("\n👉 HERE ARE YOUR EXACT COLUMN NAMES:")
    print(list(df.columns))
except Exception as e:
    print(f"❌ Could not read file: {e}")
    