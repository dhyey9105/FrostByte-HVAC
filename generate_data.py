import sqlite3
import pandas as pd
import numpy as np
import time

# --- CONFIGURATION ---
DB_FILE = 'hvac_data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS hvac_logs
                 (timestamp TEXT, outside_temp REAL, occupancy INTEGER, 
                  current_ac_setting REAL, energy_consumption REAL)''')
    conn.commit()
    conn.close()

def generate_physics_data():
    print("⚙️  Starting Thermodynamic Chiller Simulation (DOE-2 Model)...")
    
    # 1. Create a Time Range (January in Surat = Winter/Mild)
    dates = pd.date_range(start='2026-01-01', periods=2000, freq='H')
    
    data = []
    
    for dt in dates:
        # --- A. SIMULATE WEATHER (Surat Winter) ---
        # Day (28°C) vs Night (15°C)
        hour = dt.hour
        base_temp = 22 - 5 * np.cos((hour - 4) * np.pi / 12) 
        outside_temp = base_temp + np.random.normal(0, 1) # Add noise
        
        # --- B. SIMULATE OCCUPANCY (Office Hours) ---
        if 9 <= hour <= 18:
            occupancy = np.random.randint(50, 200) # Full Office
        else:
            occupancy = np.random.randint(0, 10)   # Night Watchman only
            
        # --- C. AC SETPOINT DECISION ---
        # Humans set it to 22°C usually
        setpoint = np.random.choice([20, 22, 24])
        
        # --- D. THE PHYSICS ENGINE (Calculate Chiller Load) ---
        # Formula: Q = m * Cp * deltaT (Simplified for Load)
        
        # 1. Base Cooling Load (kW) from Weather
        # (Outside - Setpoint) * InsulationFactor
        delta_t = max(0, outside_temp - setpoint)
        conduction_load = delta_t * 15 # kW
        
        # 2. Internal Load from People (1 Person = ~100 Watts)
        person_load = (occupancy * 150) / 1000 # kW
        
        # 3. Total Thermal Load
        total_thermal_load = conduction_load + person_load
        
        # 4. Chiller Efficiency (COP)
        # COP is worse when it's hot outside (Carnot Efficiency)
        # Typical Chiller COP is 3.0 to 5.0
        cop = 4.5 - (outside_temp - 25) * 0.1
        cop = max(2.0, min(6.0, cop)) # Clamp COP limits
        
        # 5. Final Electrical Power (The Compressor Energy)
        # Power = Cooling_Load / COP
        if total_thermal_load > 0:
            compressor_power = total_thermal_load / cop
        else:
            compressor_power = 0 # Free cooling / Off
            
        # Add a "Base Load" (Pumps & Fans run even if Compressor is low)
        system_power = compressor_power + 5.0 
        
        # Format Timestamp
        ts = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        data.append((ts, round(outside_temp, 2), occupancy, setpoint, round(system_power, 2)))

    # --- SAVE TO DB ---
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.executemany('INSERT INTO hvac_logs VALUES (?,?,?,?,?)', data)
    conn.commit()
    conn.close()
    
    print(f"✅ Simulation Complete! Generated {len(data)} hours of physics-based Chiller data.")
    print(f"   -> Example: Temp=28°C, Occ=150ppl, Load={data[12][4]} kW")

if __name__ == "__main__":
    init_db()
    generate_physics_data()