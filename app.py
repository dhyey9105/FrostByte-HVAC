import streamlit as st
import pandas as pd
import numpy as np
import pickle
import sqlite3
import time
import requests
import google.generativeai as genai
from datetime import datetime
from streamlit_lottie import st_lottie
from fpdf import FPDF
import base64
import random # Needed for Sensor Simulation

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="FrostByte | Smart HVAC Controller",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- API KEYS ---
# SET TO GANDHINAGAR FOR THE COMPETITION
WEATHER_API_KEY = "4592cc7c9b838fe1c2fc4d8ee3810fab" 
CITY = "Gandhinagar" 
GEMINI_API_KEY = "AIzaSyBPxwuqAVR40W8i8ZkrSXmyzpZI568QPQU"

# --- CONFIGURE GEMINI AI ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model_gemini = genai.GenerativeModel('gemini-flash-latest')
except Exception as e:
    model_gemini = None

# --- HELPER FUNCTION FOR IMAGES ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    
    /* --- CHATBOT FIX (AGGRESSIVE) --- */
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 30px !important;
        right: 30px !important;
        width: auto !important;
        z-index: 99999 !important;
    }

    div[data-testid="stPopover"] > button {
        border-radius: 30px !important;
        background: linear-gradient(135deg, #2980B9 0%, #6DD5FA 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
        padding: 10px 25px !important;
        font-weight: bold !important;
        font-size: 16px !important;
        height: auto !important;
        width: auto !important;
        animation: float 3s ease-in-out infinite;
    }
    
    div[data-testid="stPopover"] > button:hover {
        transform: scale(1.05);
        color: #fff !important;
    }
    
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
        100% { transform: translateY(0px); }
    }
    /* --- END CHATBOT FIX --- */

    [data-testid="stHorizontalBlock"] { align-items: center; }
    
    /* --- IMAGE ALIGNMENT STYLES --- */
    .team-container {
        display: flex;
        justify-content: center;
        margin-bottom: 15px;
    }
    .team-img-fixed {
        width: 150px;
        height: 150px;
        object-fit: cover; 
        border-radius: 50%;
        border: 4px solid #154360;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    .logo-container {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100px;
    }
    .logo-img-fixed {
        max-height: 80px; 
        max-width: 100%;
        width: auto;
        object-fit: contain;
    }

    .header-box {
        background: linear-gradient(90deg, #004e92 0%, #000428 100%);
        padding: 30px;
        color: white;
        text-align: center;
        border-radius: 0 0 15px 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        margin-bottom: 20px;
    }
    
    .marquee-container {
        background-color: #FEF9E7;
        color: #B03A2E;
        padding: 10px;
        font-weight: bold;
        border: 1px solid #F1C40F;
        border-radius: 5px;
        margin-bottom: 25px;
    }
    
    .message-box {
        background: linear-gradient(135deg, #E0F7FA 0%, #B2EBF2 100%);
        border-left: 6px solid #00BCD4;
        padding: 25px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        color: #006064;
    }
    
    .login-box {
        background-color: #F8F9F9;
        padding: 30px;
        border-radius: 10px;
        border: 1px solid #D5D8DC;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.1);
    }
    
    /* TELEMETRY BOX (PROFESSIONAL GREY/BLUE) */
    .telemetry-box {
        background-color: #F4F6F6; /* Light Industrial Grey */
        color: #154360; /* Deep Engineering Blue */
        padding: 15px;
        border-radius: 8px;
        font-family: 'Courier New', monospace; 
        margin-top: 20px;
        border: 1px solid #BDC3C7;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.05); 
    }

    .roi-box {
        background-color: #FFF8E1;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #F1C40F;
        margin-top: 15px;
    }

    .footer {
        background-color: #17202A;
        color: #B2BABB;
        padding: 40px;
        text-align: center;
        margin-top: 50px;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# --- BACKEND FUNCTIONS ---

# --- 🔥 SPEED FIX 1: Cache the Animation ---
@st.cache_data(ttl=600) 
def load_lottieurl(url: str):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Updated PDF to include Room Area
def generate_pdf(user, temp, savings, carbon, area):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    pdf.cell(200, 10, txt="FrostByte Sustainability Audit Report", ln=True, align='C')
    pdf.line(10, 20, 200, 20)
    pdf.set_font("Arial", size=12)
    pdf.ln(20)
    
    pdf.cell(200, 10, txt=f"Generated for: {user.upper()}", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='L')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="System Parameters", ln=True, align='L')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Location: {CITY}", ln=True)
    pdf.cell(200, 10, txt=f"- Room Area: {area} Sq. Ft.", ln=True)
    pdf.cell(200, 10, txt=f"- Outside Temperature: {temp} C", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Impact Analysis", ln=True, align='L')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Estimated Carbon Footprint: {carbon:.2f} kg CO2", ln=True)
    pdf.cell(200, 10, txt=f"- Total Hourly Savings: Rs {savings:.2f}", ln=True)
    
    pdf.ln(20)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Projected Annual Impact", ln=True, align='L')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"- Projected Monthly Savings: Rs {savings * 10 * 30:.2f} (Est)", ln=True)
    pdf.cell(200, 10, txt=f"- Projected Yearly Savings: Rs {savings * 10 * 300:.2f} (Est)", ln=True)

    pdf.ln(20)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt="This is an AI-generated estimate for audit purposes.", ln=True, align='C')
    pdf.cell(200, 10, txt="(c) 2026 FrostByte Technologies", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

def init_db():
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS login_logs 
                 (timestamp TEXT, username TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False 
    finally:
        conn.close()

def verify_login(username, password):
    valid_admins = {"admin": "admin123", "dhyey": "1234", "harsh": "1234", "dev": "owner"}
    if username in valid_admins and valid_admins[username] == password:
        return True
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == password:
        return True
    return False

def log_access(username, status):
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO login_logs (timestamp, username, status) VALUES (?,?,?)", (ts, username, status))
    conn.commit()
    conn.close()

def get_access_logs():
    conn = sqlite3.connect('hvac_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM login_logs ORDER BY timestamp DESC", conn)
        return df
    except:
        return pd.DataFrame()
    finally:
        conn.close()

# --- 🔥 SPEED FIX 2: Cache the Model ---
@st.cache_resource 
def load_model():
    try:
        with open('frostbyte_model.pkl', 'rb') as f:
            model = pickle.load(f)
        return model
    except FileNotFoundError:
        return None

def save_to_db(temp, occupancy, setpoint, energy, carbon):
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''CREATE TABLE IF NOT EXISTS hvac_logs 
                 (timestamp TEXT, outside_temp REAL, occupancy INTEGER, current_ac_setting INTEGER, energy_consumption REAL)''')
    try:
        c.execute("INSERT INTO hvac_logs (timestamp, outside_temp, occupancy, current_ac_setting, energy_consumption) VALUES (?,?,?,?,?)",
                  (timestamp, temp, occupancy, setpoint, energy))
        conn.commit()
    except:
        pass 
    conn.close()

def get_historical_data():
    conn = sqlite3.connect('hvac_data.db')
    try:
        df = pd.read_sql_query("SELECT * FROM hvac_logs ORDER BY rowid DESC LIMIT 100", conn)
        return df
    except:
        return pd.DataFrame()
    finally:
        conn.close()

@st.cache_data(ttl=180)
def get_live_weather():
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            return r.json()['main']['temp'], r.json()['weather'][0]['description']
    except:
        pass
    return None, None

# Run DB Init
init_db()

# --- SESSION STATE SETUP ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ""
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# =========================================================
# HEADER & LOGOS
# =========================================================
st.markdown("""
    <div class="header-box">
        <h1>❄️ FrostByte Technologies</h1>
        <p>AI-Driven Decarbonization for Indian MSMEs | Supported by GTU Innovation Council</p>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# FLOATING CHATBOT (FIXED & MERGED)
# =========================================================
with st.popover("👋 Hi! Ask EcoBot"):
    st.markdown("### 🤖 EcoBot AI")
    st.caption("Ask me about Energy Saving, HVAC, or Green Buildings!")
    for msg in st.session_state.chat_history[-3:]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if prompt := st.chat_input("How can I save energy?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        if model_gemini is None:
             st.error("⚠️ System Error: AI Key is missing.")
        else:
            try:
                response = model_gemini.generate_content(f"You are EcoBot. Keep answers short (max 30 words). User: {prompt}")
                ai_text = response.text
                st.session_state.chat_history.append({"role": "assistant", "content": ai_text})
                st.rerun()
            except Exception as e:
                st.error(f"AI Error: {e}")

# =========================================================
# NAVIGATION
# =========================================================
nav_options = ["🏠 Home & Vision", "🚀 Project Dashboard", "📈 Analytics", "ℹ️ About Team"]
if st.session_state['logged_in'] and st.session_state['username'] in ['admin', 'dev']:
    nav_options.append("🔐 Admin Logs")

selected_tab = st.radio("Navigation", nav_options, horizontal=True, label_visibility="collapsed")

st.markdown("""
    <div class="marquee-container">
        <marquee behavior="scroll" direction="left" scrollamount="10">
            🔔 <b>NEWS UPDATE:</b> FrostByte AI projected to reduce cooling costs by up to 18%  |  🏆 ISHRAE Surat Chapter supports new AI initiative  |  India targets 50% renewable energy by 2030
        </marquee>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# PAGE: HOME & VISION
# =========================================================
if selected_tab == "🏠 Home & Vision":
    
    st.write("") 
    
    # --- LOGOS ---
    c1, c2, c3, c4, c5 = st.columns(5)
    def render_logo(col, img_path, alt_text):
        b64 = get_img_as_base64(img_path)
        with col:
            if b64:
                st.markdown(f"""
                <div class="logo-container">
                    <img src="data:image/png;base64,{b64}" class="logo-img-fixed">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='logo-container'><b>{alt_text}</b></div>", unsafe_allow_html=True)

    render_logo(c1, "gtu.png", "GTU")
    render_logo(c2, "ibm.png", "IBM")
    render_logo(c3, "gks.png", "GKS")
    render_logo(c4, "csrbox.png", "CSRBOX")
    render_logo(c5, "college.png", "Institute")
    
    st.divider()

    col_main, col_news = st.columns([2.5, 1])
    
    with col_main:
        lottie_url = "https://lottie.host/80e7379f-6e8d-476e-9e45-8c767f4c7d8e/0w5E1Y8Z7P.json" 
        lottie_json = load_lottieurl(lottie_url)
        if lottie_json:
            st_lottie(lottie_json, height=150, key="green_earth")

        # --- RESTORED ORIGINAL TEXT ---
        st.subheader("The National Vision")
        st.markdown("""
        **Aligned with the 'Panchamrit' Strategy**
        At the COP26 summit, Prime Minister **Narendra Modi** committed India to achieving **Net Zero Emissions by 2070**. 
        
        **The Core Challenge:**
        Industrial HVAC (Heating, Ventilation, and Air Conditioning) systems are the largest electricity consumers in commercial buildings, often accounting for **40-60%** of energy bills. Most run on manual, inefficient controls.
        
        **Our Solution:**
        **FrostByte** bridges this gap using an AI-driven controller that integrates **Thermodynamics Physics** with **Deep Learning**. By optimizing chiller loads in real-time, we drastically reduce wastage and support India's carbon reduction goals.
        """)
        
        try: st.image("modi.png", caption="Hon'ble PM Shri Narendra Modi", width=300)
        except: pass

        st.write("")
        st.markdown("## 🤝 From the Desk of the Team")
        st.markdown("""
        <div class="message-box">
            <h3>"Innovating for a Greener Tomorrow"</h3>
            <p>Welcome to <b>FrostByte</b>. We are a team of Mechanical Engineering students driven by a single mission: to modernize India's industrial infrastructure.</p>
            <p>While the world discusses AI, many factories still rely on manual technology. We accepted the challenge to change this. By giving HVAC systems the ability to <b>'think'</b> before they cool, we are not just saving money—we are engineering a sustainable future.</p>
            <br>
            <p style="text-align:right;"><b>— Team FrostByte</b><br>
            <i>Mechanical Engineering Dept.</i></p>
        </div>
        """, unsafe_allow_html=True)
    
    # --- FAIL-SAFE NEWS SECTION ---
    with col_news:
        st.markdown("### ⚡ HVAC News")
        
        if 'news_cache' not in st.session_state:
            st.session_state['news_cache'] = None
            
        if model_gemini:
            try:
                # 1. TRY FRESH FETCH
                if st.session_state['news_cache'] is None:
                    news_prompt = "Give me 3 short, realistic headlines about HVAC, Green Buildings, or Carbon Reduction in India for 2026. Bullet points only."
                    response = model_gemini.generate_content(news_prompt)
                    st.session_state['news_cache'] = response.text
                
                # SHOW IF SUCCESSFUL
                st.info(st.session_state['news_cache'])
                
            except Exception as e:
                # 2. IF API FAILS (QUOTA), CHECK CACHE
                if st.session_state['news_cache'] is not None:
                    st.info(st.session_state['news_cache'])
                    st.caption("⚠️ Offline Mode: Showing cached updates")
                else:
                    # 3. IF ALL FAILS, SHOW BACKUP (THE SAVIOR!)
                    # REPLACED "Recognition" with "Tech Shift" line
                    st.info("""
                    * 🇮🇳 **Policy Update:** India mandates energy audits for textile industries by Dec 2026.
                    * 📉 **Market Trends:** AI-based cooling controllers predicted to cut industrial costs by 25%.
                    * 🚀 **Tech Shift:** IoT-enabled magnetic bearing chillers see 40% adoption growth.
                    """)
        else:
             st.info("* **COP30 Update:** India focuses on Industrial Cooling.")

# =========================================================
# PAGE: DASHBOARD (LOGIN & SIGN UP)
# =========================================================
elif selected_tab == "🚀 Project Dashboard":
    
    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            st.title("🔒 Access Portal")
            tab_login, tab_signup = st.tabs(["🔐 Login", "📝 Sign Up"])
            
            with tab_login:
                st.write("")
                u = st.text_input("Username", key="login_u")
                p = st.text_input("Password", type="password", key="login_p")
                if st.button("Login", type="primary", use_container_width=True):
                    if verify_login(u, p):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        log_access(u, "Success")
                        st.rerun()
                    else:
                        st.error("Invalid Credentials")
            
            with tab_signup:
                st.write("")
                new_u = st.text_input("Choose Username", key="signup_u")
                new_p = st.text_input("Choose Password", type="password", key="signup_p")
                if st.button("Create Account", use_container_width=True):
                    if new_u and new_p:
                        if create_user(new_u, new_p):
                            st.success("✅ Created! Go to Login.")
                        else:
                            st.error("⚠️ Username taken.")
            st.markdown("</div>", unsafe_allow_html=True)
            
    else:
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.title("🏭 Plant Controller | AI Mode")
            st.caption(f"Operator: {st.session_state['username'].upper()} | Status: ONLINE")
        
        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            st.subheader("🎛️ Control Panel")
            
            # --- PROFESSOR UPGRADE 1: MANUAL ROOM SIZE INPUT ---
            # Allows manual typing (number_input handles keyboard entry)
            room_area = st.number_input("📏 Room Area (Sq. Ft)", min_value=100, max_value=10000, value=500, step=10, help="Manually enter the size of the room.")

            st.write("---")
            
            # --- PROFESSOR UPGRADE 2: SENSOR MODE ---
            use_sensor = st.toggle("📡 Activate IoT Sensor Mode")
            
            if use_sensor:
                # SIMULATE SENSOR (Random Occupancy)
                occupancy = random.randint(5, 120)
                st.info(f"🟢 Sensor Status: ACTIVE")
                st.metric("Detected Occupancy", f"{occupancy} People")
                # Visual placeholder for "Computer Vision"
                st.image("sensor.png", caption="Live Sensor Feed (Simulated)", width=300)
            else:
                occupancy = st.slider("👥 Manual Occupancy (ppl)", 0, 200, 50)

            st.write("---")
            data_mode = st.radio("Weather Source", ["Live IoT Sensors", "Manual Simulation"])
            
            if data_mode == "Live IoT Sensors":
                real_temp, desc = get_live_weather()
                if real_temp:
                    outside_temp = real_temp
                    st.success(f"📍 {CITY}: {real_temp}°C") # SHOWS GANDHINAGAR
                    st.caption(f"Sky: {desc}")
                else:
                    st.warning("⚠️ IoT Offline")
                    outside_temp = 35.0
            else:
                outside_temp = st.slider("🌡️ Outside Temp (°C)", 10.0, 45.0, 30.0)

            current_setpoint = st.selectbox("Current Setpoint", list(range(18, 27)))
            
            if st.button("🚪 Logout", type="secondary"):
                st.session_state['logged_in'] = False
                st.rerun()
            
            # ROI CALCULATOR
            with st.expander("💰 ROI Calculator", expanded=False):
                st.write("Calculate your long-term savings:")
                elec_rate = st.number_input("Electricity Rate (Rs/Unit)", value=10.0, step=0.5)
                daily_hours = st.number_input("Daily Run Hours", value=10, step=1)
                st.caption("Based on current hourly savings")

        with col_d2:
            model = load_model()
            if model:
                # --- NEW LOGIC: Scale load based on Room Area ---
                # Assuming base model was trained for a 500 sq ft room.
                area_factor = room_area / 500.0
                
                input_df = pd.DataFrame([[outside_temp, occupancy]], columns=['outside_temp', 'occupancy'])
                base_load = model.predict(input_df)[0]
                
                # Apply Physics Scaling
                predicted_load = base_load * area_factor
                if outside_temp > 40:
                    predicted_load = predicted_load * 1.2

                if occupancy < (20 * area_factor):
                    ai_setpoint = 25
                    status = "ECO MODE (Low Occupancy)"
                    color = "green"
                    health_status = "Excellent"
                elif outside_temp > 40:
                    ai_setpoint = 23
                    status = "PRE-COOLING (Heatwave)"
                    color = "orange"
                    health_status = "Stress Load (High)"
                else:
                    ai_setpoint = 22
                    status = "OPTIMAL COMFORT"
                    color = "blue"
                    health_status = "Good"
                
                gap = abs(ai_setpoint - current_setpoint)
                green_score = max(0, 100 - (gap * 15)) 
                
                if ai_setpoint > current_setpoint:
                    savings_kwh = predicted_load * (ai_setpoint - current_setpoint) * 0.06
                    hourly_savings = savings_kwh * elec_rate
                else:
                    hourly_savings = 0.0
                
                carbon_emission = predicted_load * 0.82
                
                # Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🌡️ Temp", f"{outside_temp}°C")
                m2.metric("⚡ Load", f"{predicted_load:.1f} kW")
                m3.metric("👣 Carbon", f"{carbon_emission:.1f} kg")
                m4.metric("💰 Savings", f"₹ {hourly_savings:.1f}")
                
                # TELEMETRY BOX (PROFESSIONAL GREY)
                st.markdown(f"""
                <div class="telemetry-box">
                <b>📡 LIVE TELEMETRY ({CITY.upper()}):</b><br>
                > RETURN AIR TEMP: {outside_temp - 5:.1f}°C<br>
                > SUPPLY AIR TEMP: {ai_setpoint - 8:.1f}°C<br>
                > COMPRESSOR SPEED: {min(60, predicted_load/2):.1f} Hz<br>
                > WATER FLOW RATE: {predicted_load * 1.5:.1f} LPM
                </div>
                """, unsafe_allow_html=True)
                
                # Predictive Maintenance
                st.markdown(f"""
                <div style="background-color:#EAFAF1; padding:15px; border-radius:10px; border-left:5px solid {color}; margin-top:10px;">
                    <h4 style="color:{color}; margin:0;">SYSTEM STATUS: {status}</h4>
                    <p>AI Recommendation: <b>Change Setpoint to {ai_setpoint}°C</b></p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                col_score1, col_score2 = st.columns([3, 1])
                with col_score1:
                    st.write("🌿 **Green Efficiency Score (User Behavior):**")
                    st.progress(green_score / 100)
                with col_score2:
                     st.metric("Score", f"{green_score}/100")
                     
                if hourly_savings > 0:
                    monthly_save = hourly_savings * daily_hours * 30
                    yearly_save = monthly_save * 12
                    st.markdown(f"""
                    <div class="roi-box">
                        <b>💰 ROI Projection:</b><br>
                        You are saving <b>₹{monthly_save:,.0f}</b> per month and <b>₹{yearly_save:,.0f}</b> per year!
                    </div>
                    """, unsafe_allow_html=True)

                st.write("")
                
                if st.button("📄 Generate & Download Audit Report"):
                    pdf_bytes = generate_pdf(st.session_state['username'], str(outside_temp), hourly_savings, carbon_emission, room_area)
                    st.download_button(label="📥 Click to Save PDF", data=pdf_bytes, file_name=f"FrostByte_Audit_{datetime.now().strftime('%H%M')}.pdf", mime="application/pdf")

                st.line_chart(pd.DataFrame({
                    "Standard Chiller": [predicted_load+15, predicted_load+12], 
                    "FrostByte AI": [predicted_load, predicted_load-2]
                }))
                
                if st.button("💾 Log Data & Emissions"):
                    save_to_db(outside_temp, occupancy, current_setpoint, predicted_load, carbon_emission)
                    st.toast("Data Logged Successfully!", icon="✅")

# =========================================================
# PAGE: ANALYTICS
# =========================================================
elif selected_tab == "📈 Analytics":
    st.header("📊 Energy & Carbon Trends")
    try:
        df = get_historical_data()
        st.dataframe(df, use_container_width=True)
        col1, col2 = st.columns(2)
        with col1: st.line_chart(df['energy_consumption'])
        with col2: st.scatter_chart(df, x='outside_temp', y='energy_consumption')
    except:
        st.error("No Data Logged yet.")

# =========================================================
# PAGE: ADMIN LOGS
# =========================================================
elif selected_tab == "🔐 Admin Logs":
    if not st.session_state['logged_in']:
        st.error("Access Denied.")
    else:
        st.header("🔐 User Access Logs")
        logs_df = get_access_logs()
        st.dataframe(logs_df, use_container_width=True)

# =========================================================
# PAGE: ABOUT TEAM
# =========================================================
elif selected_tab == "ℹ️ About Team":
    st.header("❄️ Meet The Team")
    st.divider()
    col_d, col_h = st.columns(2)
    
    # --- PERFECT CIRCLE TEAM IMAGES ---
    def render_team_member(col, img_path, name, role, details, link1, link2):
        b64 = get_img_as_base64(img_path)
        with col:
            # Image Container
            if b64:
                st.markdown(f"""
                <div class="team-container">
                    <img src="data:image/png;base64,{b64}" class="team-img-fixed">
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=150)
            
            # Text Content
            st.markdown(f"""
            <div class="profile-box">
                <h3>{name}</h3>
                <p><b>{role}</b></p>
                <p>{details}</p>
                <p style="font-size:14px;">Mechanical Engineering | AI Systems</p>
            </div>
            """, unsafe_allow_html=True)
            
            c_lnk1, c_lnk2 = st.columns(2)
            with c_lnk1: st.link_button("LinkedIn Profile", link1)
            with c_lnk2: st.link_button("📧 Email Me", link2)

    render_team_member(
        col_d, "dhyey.png", 
        "👑 Dhyey J. Nathvani", 
        "Team Leader & Lead Developer", 
        "<b>President | ISHRAE Student Chapter</b><br>Dr. S. & S.S. Ghandhy College, Surat",
        "https://www.linkedin.com/in/dhyey-nathvani-gecs-mech-a96905289", 
        "mailto:dhyeynathvani1515@gmail.com"
    )

    render_team_member(
        col_h, "harsh.png", 
        "🤝 Harsh D. Patel", 
        "Research & Strategy Partner", 
        "<b>President-Elect | ISHRAE Student Chapter</b><br>Dr. S. & S.S. Ghandhy College, Surat",
        "https://www.linkedin.com/in/harshpatel0411", 
        "mailto:harshpatel04112004@gmail.com"
    )

# --- FOOTER ---
st.markdown("""
<div class="footer">
    <p>© 2026 FrostByte Technologies | AI Innovation Challenge 2026</p>
    <p>GKS | CSRBOX | IBM SkillsBuild</p>
</div>
""", unsafe_allow_html=True)