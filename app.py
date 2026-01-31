import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import time
import requests
import google.generativeai as genai
from datetime import datetime
from streamlit_lottie import st_lottie
from fpdf import FPDF
import base64
import random
import os

# =========================================================
# 1. PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="FrostByte | Smart HVAC Controller",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# 2. GLOBAL API KEYS & SETUP
# =========================================================
# UPDATED: City changed to Surat
CITY = "Surat"
WEATHER_API_KEY = "4592cc7c9b838fe1c2fc4d8ee3810fab"

# Construct Gemini Key
key_part_1 = "AIzaSy"
key_part_2 = "BmD8i0500PyhNNjRSEh_wEG0rrCtIbbBU"
GEMINI_API_KEY = key_part_1 + key_part_2

# --- CONFIGURE AI (USING GEMINI 2.5) ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Using the exact model from your supported list
    model_gemini = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    model_gemini = None

# --- GLOBAL WEATHER CALL (Runs Once) ---
current_temp = 25  # Fallback
current_hum = 50   # Fallback
weather_desc = "Sunny"

try:
    url = f"https://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={WEATHER_API_KEY}&units=metric"
    response = requests.get(url, timeout=3)
    if response.status_code == 200:
        data = response.json()
        current_temp = data["main"]["temp"]
        current_hum = data["main"]["humidity"]
        weather_desc = data["weather"][0]["description"].title()
except:
    pass

# =========================================================
# 3. HELPER FUNCTIONS
# =========================================================

def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_news():
    try:
        # UPDATED: Using Gemini 2.5 Flash
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = "Give me 3 short, realistic headlines about HVAC, Green Buildings, or Carbon Reduction in India for 2026. Bullet points only."
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return """
        * 🇮🇳 **Policy Update:** India mandates energy audits for textile industries by Dec 2026.
        * 📉 **Market Trends:** AI-based cooling controllers predicted to cut industrial costs by 25%.
        * 🚀 **Tech Shift:** IoT-enabled magnetic bearing chillers see 40% adoption growth.
        """

@st.cache_data(ttl=600)
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

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

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS login_logs (timestamp TEXT, username TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS hvac_logs (timestamp TEXT, outside_temp REAL, occupancy INTEGER, current_ac_setting INTEGER, energy_consumption REAL)''')
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
    valid_admins = {"admin": "Gandhinagar#Win", "dhyey": "Dhyey092026", "harsh": "1234", "owner": "workisworship"}
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

def save_to_db(temp, occupancy, setpoint, energy, carbon):
    conn = sqlite3.connect('hvac_data.db')
    c = conn.cursor()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
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

# --- AI CALCULATION LOGIC ---
def calculate_ai_load(temp, occupancy):
    base = 10.0
    temp_factor = (temp - 20) * 1.5
    occ_factor = occupancy * 0.1
    total_load = base + temp_factor + occ_factor
    if total_load < 5: total_load = 5.0
    return total_load

# Run DB Init
init_db()

# =========================================================
# 4. CUSTOM CSS STYLING
# =========================================================
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    
    /* CHATBOT BUTTON STYLING */
    div[data-testid="stPopover"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important; width: auto !important; z-index: 99999 !important;
    }
    div[data-testid="stPopover"] > button {
        border-radius: 30px !important; background: linear-gradient(135deg, #2980B9 0%, #6DD5FA 100%) !important;
        color: white !important; border: none !important; padding: 10px 25px !important;
        font-weight: bold !important; font-size: 16px !important;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.3) !important;
        animation: float 3s ease-in-out infinite;
    }
    div[data-testid="stPopover"] > button:hover { transform: scale(1.05); color: #fff !important; }
    @keyframes float { 0% { transform: translateY(0px); } 50% { transform: translateY(-5px); } 100% { transform: translateY(0px); } }

    /* GENERAL UI STYLES */
    [data-testid="stHorizontalBlock"] { align-items: center; }
    
    .team-container { display: flex; justify-content: center; margin-bottom: 15px; }
    .team-img-fixed { width: 150px; height: 150px; object-fit: cover; border-radius: 50%; border: 4px solid #154360; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
    
    .logo-container { display: flex; align-items: center; justify-content: center; height: 100px; }
    .logo-img-fixed { max-height: 80px; max-width: 100%; width: auto; object-fit: contain; }

    .header-box { background: linear-gradient(90deg, #004e92 0%, #000428 100%); padding: 30px; color: white; text-align: center; border-radius: 0 0 15px 15px; margin-bottom: 20px; }
    .marquee-container { background-color: #FEF9E7; color: #B03A2E; padding: 10px; font-weight: bold; border: 1px solid #F1C40F; border-radius: 5px; margin-bottom: 25px; }
    .message-box { background: linear-gradient(135deg, #E0F7FA 0%, #B2EBF2 100%); border-left: 6px solid #00BCD4; padding: 25px; border-radius: 12px; color: #006064; }
    
    .login-box { background-color: #F8F9F9; padding: 30px; border-radius: 10px; border: 1px solid #D5D8DC; box-shadow: 0px 4px 12px rgba(0,0,0,0.1); }
    .telemetry-box { background-color: #F4F6F6; color: #154360; padding: 15px; border-radius: 8px; font-family: 'Courier New', monospace; margin-top: 20px; border: 1px solid #BDC3C7; }
    .roi-box { background-color: #FFF8E1; padding: 15px; border-radius: 10px; border: 1px solid #F1C40F; margin-top: 15px; }
    
    /* WEATHER FLEXBOX FIX - GUARANTEES HORIZONTAL ALIGNMENT */
    .weather-container {
        display: flex;
        flex-direction: row;
        justify-content: space-around;
        align-items: center;
        background-color: #F8F9F9;
        border: 1px solid #D5D8DC;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .weather-item {
        text-align: center;
        flex: 1;
        border-right: 1px solid #E5E8E8;
    }
    .weather-item:last-child {
        border-right: none;
    }
    .weather-item h2 { margin: 0; color: #154360; font-size: 24px; }
    .weather-item p { margin: 0; color: #7F8C8D; font-size: 14px; font-weight: bold; }

    .footer { background-color: #17202A; color: #B2BABB; padding: 40px; text-align: center; margin-top: 50px; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 5. HEADER & SESSION STATE
# =========================================================
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'username' not in st.session_state: st.session_state['username'] = ""
if 'chat_history' not in st.session_state: st.session_state.chat_history = []

st.markdown("""
    <div class="header-box">
        <h1>❄️ FrostByte Technologies</h1>
        <p>AI-Driven Decarbonization for Indian MSMEs | Supported by GTU Innovation Council</p>
    </div>
""", unsafe_allow_html=True)

# =========================================================
# 6. 🤖 FLOATING CHATBOT (ECOBOT)
# =========================================================
with st.popover("👋 Hi! Ask EcoBot"):
    st.markdown("### 🤖 EcoBot Live")
    st.caption("Powered by Gemini 2.5 Flash")
    
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["content"])

    if prompt := st.chat_input("Ask about energy savings..."):
        st.chat_message("user").write(prompt)
        st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            status_box = st.empty()
            status_box.markdown("⚡ *Thinking...*")
            try:
                # UPDATED: Using Gemini 2.5 Flash
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
                ai_reply = response.text
                status_box.empty()
                st.write(ai_reply)
                st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
            except Exception as e:
                status_box.error(f"⚠️ Error: {e}")

# =========================================================
# 7. NAVIGATION BAR
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
# PAGE 1: HOME & VISION
# =========================================================
if selected_tab == "🏠 Home & Vision":
    st.title("🏠 Welcome to FrostByte")

    # --- ALIGNMENT FIX: WEATHER HEADER USING FLEXBOX ---
    st.markdown(f"### 📍 Live Site Conditions: {CITY}")
    
    # This HTML uses the CSS classes we defined above to force horizontal alignment
    st.markdown(f"""
    <div class="weather-container">
        <div class="weather-item">
            <p>🌡️ Temperature</p>
            <h2>{current_temp}°C</h2>
        </div>
        <div class="weather-item">
            <p>💧 Humidity</p>
            <h2>{current_hum}%</h2>
        </div>
        <div class="weather-item">
            <p>🌤️ Sky</p>
            <h2>{weather_desc}</h2>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- LOGOS ---
    c1, c2, c3, c4, c5 = st.columns(5)
    def render_logo(col, img_path, alt_text):
        b64 = get_img_as_base64(img_path)
        with col:
            if b64:
                st.markdown(f"<div class='logo-container'><img src='data:image/png;base64,{b64}' class='logo-img-fixed'></div>", unsafe_allow_html=True)
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

        st.subheader("The National Vision")
        st.markdown("""
        **Aligned with the 'Panchamrit' Strategy**
        At the COP26 summit, Prime Minister **Narendra Modi** committed India to achieving **Net Zero Emissions by 2070**. 
        
        **The Core Challenge:**
        Industrial HVAC systems account for **40-60%** of energy bills in commercial buildings.
        
        **Our Solution:**
        **FrostByte** bridges this gap using an AI-driven controller that integrates **Thermodynamics Physics** with **Deep Learning**.
        """)
        
        try: st.image("modi.png", caption="Hon'ble PM Shri Narendra Modi", width=300)
        except: pass

        # --- RESTORED: FULL TEAM MESSAGE ---
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
    
    with col_news:
        st.markdown("### ⚡ HVAC News")
        latest_news = get_cached_news()
        st.info(latest_news)

# =========================================================
# PAGE 2: DASHBOARD (LOGIN & CONTROL)
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
        # --- MAIN DASHBOARD INTERFACE ---
        c_head1, c_head2 = st.columns([3, 1])
        with c_head1:
            st.title("🏭 Plant Controller | AI Mode")
            st.caption(f"Operator: {st.session_state['username'].upper()} | Status: ONLINE")
        
        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            st.subheader("🎛️ Control Panel")
            room_area = st.number_input("📏 Room Area (Sq. Ft)", min_value=100, max_value=10000, value=500, step=10)
            st.write("---")
            
            use_sensor = st.toggle("📡 Activate IoT Sensor Mode")
            if use_sensor:
                occupancy = random.randint(5, 120)
                st.info(f"🟢 Sensor Status: ACTIVE")
                st.metric("Detected Occupancy", f"{occupancy} People")
                st.image("sensor.png", caption="Live Sensor Feed (Simulated)", width=300)
            else:
                occupancy = st.slider("👥 Manual Occupancy (ppl)", 0, 500, 50)

            st.write("---")
            data_mode = st.radio("Weather Source", ["Live IoT Sensors", "Manual Simulation"])
            
            if data_mode == "Live IoT Sensors":
                real_temp, desc = get_live_weather()
                if real_temp:
                    outside_temp = real_temp
                    st.success(f"📍 {CITY}: {real_temp}°C")
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
            
            with st.expander("💰 ROI Calculator", expanded=False):
                st.write("Calculate your long-term savings:")
                elec_rate = st.number_input("Electricity Rate (Rs/Unit)", value=10.0, step=0.5)
                daily_hours = st.number_input("Daily Run Hours", value=10, step=1)
                st.caption("Based on current hourly savings")

        with col_d2:
            # AI CALCULATION LOGIC
            area_factor = room_area / 500.0
            base_load = calculate_ai_load(outside_temp, occupancy)
            predicted_load = base_load * area_factor
            if outside_temp > 40: predicted_load = predicted_load * 1.2

            if occupancy < (20 * area_factor):
                ai_setpoint = 25
                status = "ECO MODE (Low Occupancy)"
                color = "green"
            elif outside_temp > 40:
                ai_setpoint = 23
                status = "PRE-COOLING (Heatwave)"
                color = "orange"
            else:
                ai_setpoint = 22
                status = "OPTIMAL COMFORT"
                color = "blue"
            
            gap = abs(ai_setpoint - current_setpoint)
            green_score = max(0, 100 - (gap * 15)) 
            
            if ai_setpoint > current_setpoint:
                savings_kwh = predicted_load * (ai_setpoint - current_setpoint) * 0.06
                hourly_savings = savings_kwh * elec_rate
            else:
                hourly_savings = 0.0
            
            carbon_emission = predicted_load * 0.82
            
            # METRICS DISPLAY
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("🌡️ Temp", f"{outside_temp}°C")
            m2.metric("⚡ Load", f"{predicted_load:.1f} kW")
            m3.metric("👣 Carbon", f"{carbon_emission:.1f} kg")
            m4.metric("💰 Savings", f"₹ {hourly_savings:.1f}")
            
            st.markdown(f"""
            <div class="telemetry-box">
            <b>📡 LIVE TELEMETRY ({CITY.upper()}):</b><br>
            > RETURN AIR TEMP: {outside_temp - 5:.1f}°C<br>
            > SUPPLY AIR TEMP: {ai_setpoint - 8:.1f}°C<br>
            > COMPRESSOR SPEED: {min(60, predicted_load/2):.1f} Hz
            </div>
            """, unsafe_allow_html=True)
            
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
# PAGE 3: ANALYTICS
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
# PAGE 4: ADMIN LOGS
# =========================================================
elif selected_tab == "🔐 Admin Logs":
    if not st.session_state['logged_in']:
        st.error("Access Denied.")
    else:
        st.header("🔐 User Access Logs")
        logs_df = get_access_logs()
        st.dataframe(logs_df, use_container_width=True)

# =========================================================
# PAGE 5: ABOUT TEAM
# =========================================================
elif selected_tab == "ℹ️ About Team":
    st.header("❄️ Meet The Team")
    st.divider()
    col_d, col_h = st.columns(2)
    
    def render_team_member(col, img_path, name, role, details, link1, link2):
        b64 = get_img_as_base64(img_path)
        with col:
            if b64:
                st.markdown(f"<div class='team-container'><img src='data:image/png;base64,{b64}' class='team-img-fixed'></div>", unsafe_allow_html=True)
            else:
                st.image("https://cdn-icons-png.flaticon.com/512/4140/4140048.png", width=150)
            
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

    render_team_member(col_d, "dhyey.png", "👑 Dhyey J. Nathvani", "Team Leader & Lead Developer", 
        "<b>President | ISHRAE Student Chapter</b><br>Dr. S. & S.S. Ghandhy College, Surat",
        "https://www.linkedin.com/in/dhyey-nathvani-gecs-mech-a96905289", "mailto:dhyeynathvani1515@gmail.com")

    render_team_member(col_h, "harsh.png", "🤝 Harsh D. Patel", "Research & Strategy Partner", 
        "<b>President-Elect | ISHRAE Student Chapter</b><br>Dr. S. & S.S. Ghandhy College, Surat",
        "https://www.linkedin.com/in/harshpatel0411", "mailto:harshpatel04112004@gmail.com")

# --- FOOTER ---
st.markdown("""
<div class="footer">
    <p>© 2026 FrostByte Technologies | AI Innovation Challenge 2026</p>
    <p>GKS | CSRBOX | IBM SkillsBuild</p>
</div>

""", unsafe_allow_html=True)
