import streamlit as st
import pandas as pd
import datetime
import time
import math
import sqlite3
import json

# ---------------------------------------------------------
# 0. ROBUST DATABASE CONNECTION & INITIALIZATION
# ---------------------------------------------------------
def get_db_conn():
    if 'db_conn' not in st.session_state:
        st.session_state.db_conn = sqlite3.connect('attendance_app.db', check_same_thread=False)
    return st.session_state.db_conn

def init_db():
    try:
        conn = get_db_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT,
                phone TEXT,
                password TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_configs (
                username TEXT,
                term_key TEXT,
                config_json TEXT,
                PRIMARY KEY (username, term_key)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS absent_records (
                username TEXT,
                term_key TEXT,
                record_key TEXT,
                PRIMARY KEY (username, term_key, record_key)
            )
        ''')
        conn.commit()
    except Exception as e:
        st.error(f"Database Initialization Error: {e}")

init_db()

def register_user_db(username, name, phone, password):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (clean_u, name.strip(), phone.strip(), password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def check_login_db(username, password):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("SELECT name FROM users WHERE username=? AND password=?", (clean_u, password))
    user = c.fetchone()
    return user[0] if user else None

def load_user_config_db(username, term_key):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    try:
        c.execute("SELECT config_json FROM user_configs WHERE username=? AND term_key=?", (clean_u, term_key))
        row = c.fetchone()
        
        if row:
            data = json.loads(row[0])
            data["start_date"] = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            data["end_date"] = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            
            for day in data.get("custom_timetable", {}):
                for session in data["custom_timetable"][day]:
                    session["start_time"] = datetime.datetime.strptime(session["start_time"], "%H:%M:%S").time()
                    session["end_time"] = datetime.datetime.strptime(session["end_time"], "%H:%M:%S").time()
                    
            for ext in data.get("extra_lectures", []):
                ext["start_time"] = datetime.datetime.strptime(ext["start_time"], "%H:%M:%S").time()
                ext["end_time"] = datetime.datetime.strptime(ext["end_time"], "%H:%M:%S").time()
                
            return data
    except Exception:
        pass
    return None

def save_user_config_db(username, term_key, config):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    
    # Safe serialization for dates and times
    cfg_to_save = {
        "setup_complete": config.get("setup_complete", False),
        "start_date": config["start_date"].strftime("%Y-%m-%d") if isinstance(config["start_date"], (datetime.date, datetime.datetime)) else str(config["start_date"]),
        "end_date": config["end_date"].strftime("%Y-%m-%d") if isinstance(config["end_date"], (datetime.date, datetime.datetime)) else str(config["end_date"]),
        "registered_subjects": config.get("registered_subjects", []),
        "mid_exam_dates": config.get("mid_exam_dates", []),
        "custom_timetable": {},
        "cancelled_lectures": config.get("cancelled_lectures", []),
        "extra_lectures": []
    }
    
    for day, slots in config.get("custom_timetable", {}).items():
        day_slots = []
        for s in slots:
            st_str = s["start_time"].strftime("%H:%M:%S") if isinstance(s["start_time"], datetime.time) else str(s["start_time"])
            et_str = s["end_time"].strftime("%H:%M:%S") if isinstance(s["end_time"], datetime.time) else str(s["end_time"])
            day_slots.append({
                "subject": s["subject"],
                "start_time": st_str,
                "end_time": et_str
            })
        cfg_to_save["custom_timetable"][day] = day_slots
        
    for ext in config.get("extra_lectures", []):
        st_str = ext["start_time"].strftime("%H:%M:%S") if isinstance(ext["start_time"], datetime.time) else str(ext["start_time"])
        et_str = ext["end_time"].strftime("%H:%M:%S") if isinstance(ext["end_time"], datetime.time) else str(ext["end_time"])
        cfg_to_save["extra_lectures"].append({
            "subject": ext["subject"],
            "date": ext["date"],
            "start_time": st_str,
            "end_time": et_str
        })

    c.execute("INSERT OR REPLACE INTO user_configs VALUES (?, ?, ?)", (clean_u, term_key, json.dumps(cfg_to_save)))
    conn.commit()

def load_absents_db(username, term_key):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    try:
        c.execute("SELECT record_key FROM absent_records WHERE username=? AND term_key=?", (clean_u, term_key))
        rows = c.fetchall()
        return set(r[0] for r in rows)
    except Exception:
        return set()

def save_absents_db(username, term_key, absent_set):
    init_db()
    conn = get_db_conn()
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("DELETE FROM absent_records WHERE username=? AND term_key=?", (clean_u, term_key))
    for key in absent_set:
        c.execute("INSERT INTO absent_records VALUES (?, ?, ?)", (clean_u, term_key, key))
    conn.commit()

# ---------------------------------------------------------
# MOBILE TOUCH-FRIENDLY TIME PICKER HELPER
# ---------------------------------------------------------
def mobile_time_picker(label, key_prefix, default_time=datetime.time(9, 0)):
    st.write(f"**{label}**")
    c1, c2, c3 = st.columns(3)
    
    default_h12 = default_time.hour % 12
    default_h12 = 12 if default_h12 == 0 else default_h12
    hours = [f"{i:02d}" for i in range(1, 13)]
    minutes = [f"{i:02d}" for i in range(60)]
    ampm_list = ["AM", "PM"]
    default_ampm = "PM" if default_time.hour >= 12 else "AM"
    
    try:
        h_idx = hours.index(f"{default_h12:02d}")
    except ValueError:
        h_idx = 0
    try:
        m_idx = minutes.index(f"{default_time.minute:02d}")
    except ValueError:
        m_idx = 0
    try:
        ap_idx = ampm_list.index(default_ampm)
    except ValueError:
        ap_idx = 0

    with c1:
        selected_h = st.selectbox("Hour", hours, index=h_idx, key=f"{key_prefix}_h")
    with c2:
        selected_m = st.selectbox("Min", minutes, index=m_idx, key=f"{key_prefix}_m")
    with c3:
        selected_ampm = st.selectbox("Format", ampm_list, index=ap_idx, key=f"{key_prefix}_ap")
    
    h24 = int(selected_h)
    if selected_ampm == "PM" and h24 != 12:
        h24 += 12
    elif selected_ampm == "AM" and h24 == 12:
        h24 = 0
        
    return datetime.time(h24, int(selected_m))

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Academic Portal & Multi-Semester Tracker", page_icon="🎓", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

.stApp {
    background: #0b0f19;
    background-image: 
        radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.08) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(99, 102, 241, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.06) 0px, transparent 50%);
    background-attachment: fixed;
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px) scale(0.99); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

.auth-animated-card {
    background: linear-gradient(165deg, rgba(17, 24, 39, 0.85) 0%, rgba(13, 18, 30, 0.95) 100%);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 38px 34px;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
    animation: fadeInUp 0.5s ease-out forwards;
}

.auth-header-box {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.1) 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 18px;
    padding: 24px 20px;
    text-align: center;
    margin-bottom: 26px;
}

.auth-header-title {
    font-size: 26px;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}

.auth-subtitle { color: #94a3b8; font-size: 13px; font-weight: 500; }

div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #0284c7 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.35) !important;
}

.dashboard-header {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px 30px;
    margin-bottom: 20px;
    box-shadow: 0 15px 30px rgba(0,0,0,0.4);
}

.dashboard-title {
    font-size: 28px !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 !important;
}

.term-bar-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(56, 189, 248, 0.35);
    border-radius: 18px;
    padding: 18px 24px;
    margin-bottom: 20px;
}

.insights-banner-page {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(56, 189, 248, 0.3);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
    align-items: center;
}

.insight-item-page {
    display: flex;
    align-items: center;
    gap: 14px;
    background: rgba(255, 255, 255, 0.02);
    padding: 14px 18px;
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.insight-icon-page {
    font-size: 22px;
    background: rgba(56, 189, 248, 0.12);
    padding: 10px;
    border-radius: 12px;
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.25);
}

.insight-label-page { font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 2px; }
.insight-val-page { font-size: 18px; font-weight: 800; color: #f8fafc; }

.tracker-card {
    background: linear-gradient(145deg, rgba(17, 24, 39, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
}

.lecture-item-box {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
}

.subject-card-main, .subject-card-tute {
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 18px;
}

.subject-card-main {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(99, 102, 241, 0.25);
}

.subject-card-tute {
    background: linear-gradient(145deg, rgba(30, 27, 75, 0.65) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(168, 85, 247, 0.3);
}

.card-header-flex { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.subject-title { font-size: 17px; font-weight: 700; color: #f8fafc; margin: 0; }

.badge-green { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-red { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.35); padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }

.metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 12px; margin-bottom: 12px; }
.metric-item { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); padding: 8px 12px; border-radius: 10px; }
.metric-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; font-weight: 600; }
.metric-val { font-size: 14px; font-weight: 700; color: #f1f5f9; }

.status-badge-safe { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 10px; padding: 8px 12px; margin-top: 10px; font-size: 12px; color: #6ee7b7; }
.status-badge-warning { background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.25); border-radius: 10px; padding: 8px 12px; margin-top: 10px; font-size: 12px; color: #fda4af; }

.holiday-card { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: white; padding: 16px; border-radius: 16px; margin-bottom: 16px; }
.exam-card { background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%); color: white; padding: 16px; border-radius: 16px; margin-bottom: 16px; }

.stat-box { background: rgba(30, 41, 59, 0.4); border-radius: 14px; padding: 14px; border: 1px solid rgba(255, 255, 255, 0.07); margin-bottom: 10px; }
div[data-testid="stSidebar"] { background: #080c14 !important; border-right: 1px solid rgba(255, 255, 255, 0.06); }
.user-profile-box { background: linear-gradient(135deg, #4f46e5 0%, #0284c7 100%); padding: 16px; border-radius: 16px; color: white; text-align: center; margin-bottom: 20px; }
.nav-header { font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: #64748b; margin-bottom: 10px; font-weight: 700; }
.app-footer { text-align: center; padding: 20px 0 10px 0; margin-top: 30px; border-top: 1px solid rgba(255, 255, 255, 0.08); color: #64748b; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CONSTANTS & INITIAL SESSION STATE
# ---------------------------------------------------------
HOLIDAYS_DB = {
    "2026-01-03": "Duruthu Full Moon Poya Day", "2026-01-15": "Tamil Thai Pongal Day",
    "2026-02-01": "Navam Full Moon Poya Day", "2026-02-04": "Independence Day",
    "2026-02-15": "Mahasivarathri Day", "2026-03-02": "Medin Full Moon Poya Day",
    "2026-03-21": "Id-Ul-Fitre Day", "2026-04-01": "Bak Full Moon Poya Day",
    "2026-04-03": "Good Friday", "2026-04-13": "Day prior to Sinhala & Tamil New Year",
    "2026-04-14": "Sinhala & Tamil New Year Day", "2026-05-01": "Vesak Poya Day / May Day",
    "2026-05-02": "Day following Vesak Poya Day", "2026-05-28": "Id-Ul-Allah Day",
    "2026-05-30": "Adhi Poson Poya Day", "2026-06-29": "Poson Full Moon Poya Day",
    "2026-07-29": "Esala Full Moon Poya Day", "2026-08-26": "Milad-Un-Nabi",
    "2026-08-27": "Nikini Full Moon Poya Day", "2026-09-26": "Binara Full Moon Poya Day",
    "2026-10-25": "Vap Full Moon Poya Day", "2026-11-08": "Deepawali Festival Day",
    "2026-11-24": "Ill Full Moon Poya Day", "2026-12-23": "Unduwap Full Moon Poya Day",
    "2026-12-25": "Christmas Day"
}

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
YEAR_OPTIONS = ["Year 1", "Year 2", "Year 3", "Year 4"]
SEMESTER_OPTIONS = ["Semester 1", "Semester 2"]

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = ""
if 'current_username' not in st.session_state: st.session_state['current_username'] = ""
if 'selected_year' not in st.session_state: st.session_state['selected_year'] = "Year 2"
if 'selected_semester' not in st.session_state: st.session_state['selected_semester'] = "Semester 1"
if 'nav_mode' not in st.session_state: st.session_state['nav_mode'] = "🎓 Daily Attendance"

if 'remember_user' not in st.session_state: st.session_state['remember_user'] = ""
if 'remember_pass' not in st.session_state: st.session_state['remember_pass'] = ""

# ---------------------------------------------------------
# 3. STATS CALCULATIONS & DIALOGS
# ---------------------------------------------------------
def calculate_subject_stats(subj, cfg, absent_records):
    start_d = cfg["start_date"]
    end_d = cfg["end_date"]
    today = datetime.date.today()
    
    total_lectures = 0
    past_conducted_lectures = 0
    curr_d = start_d
    
    while curr_d <= end_d:
        d_str = curr_d.strftime("%Y-%m-%d")
        d_name = curr_d.strftime("%A")
        
        is_holiday = d_str in HOLIDAYS_DB
        is_mid = d_str in cfg.get("mid_exam_dates", [])
        
        if not is_holiday and not is_mid:
            day_slots = cfg["custom_timetable"].get(d_name, [])
            for slot in day_slots:
                if slot["subject"] == subj:
                    is_cancelled = any(c["subject"] == subj and c["date"] == d_str for c in cfg.get("cancelled_lectures", []))
                    if not is_cancelled:
                        total_lectures += 1
                        if curr_d <= today:
                            past_conducted_lectures += 1
                        
            for ext in cfg.get("extra_lectures", []):
                if ext["subject"] == subj and ext["date"] == d_str:
                    total_lectures += 1
                    if curr_d <= today:
                        past_conducted_lectures += 1
                    
        curr_d += datetime.timedelta(days=1)

    absences = sum(1 for rec in absent_records if f"_{subj}_" in rec)
    attended = max(0, past_conducted_lectures - absences)
    curr_percentage = (attended / past_conducted_lectures * 100) if past_conducted_lectures > 0 else 100.0
    min_required_attendance = math.ceil(total_lectures * 0.80)
    max_allowed_absences = max(0, total_lectures - min_required_attendance)
    safe_absences_left = max_allowed_absences - absences
    remaining_sessions = max(0, total_lectures - past_conducted_lectures)

    return {
        "total": total_lectures,
        "past_conducted": past_conducted_lectures,
        "absences": absences,
        "attended": attended,
        "percentage": curr_percentage,
        "max_allowed": max_allowed_absences,
        "safe_left": safe_absences_left,
        "remaining": remaining_sessions
    }

def get_absence_details(rec_key, cfg):
    parts = rec_key.split('_')
    if len(parts) >= 3:
        date_str = parts[0]
        subj = parts[1]
        try:
            idx = int(parts[2])
        except ValueError:
            idx = 0
        
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = date_obj.strftime("%A")
        
        active_slots = []
        regular_slots = cfg["custom_timetable"].get(day_name, [])
        cancelled_today = [c["subject"] for c in cfg.get("cancelled_lectures", []) if c["date"] == date_str]
        
        for slot in regular_slots:
            if slot["subject"] not in cancelled_today:
                active_slots.append(slot)
                
        for ext in cfg.get("extra_lectures", []):
            if ext["date"] == date_str:
                active_slots.append(ext)
                
        subj_slots = [s for s in active_slots if s["subject"] == subj]
        
        if idx < len(subj_slots):
            st_t = subj_slots[idx]["start_time"]
            end_t = subj_slots[idx]["end_time"]
            return date_str, f"{st_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}"
        elif subj_slots:
            st_t = subj_slots[0]["start_time"]
            end_t = subj_slots[0]["end_time"]
            return date_str, f"{st_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}"
            
        return date_str, "Scheduled Time"
    return "Unknown Date", "Unknown Time"

@st.dialog("📅 Absent Records & Lecture History")
def open_subject_modal(subj, cfg, username, term_key):
    st.markdown(f"### 📚 Subject: **{subj}**")
    st.write("---")
    
    current_absents = st.session_state.get('absent_records', set())
    subj_absents = [r for r in current_absents if f"_{subj}_" in r]
    
    if not subj_absents:
        st.success("🎉 Perfect Attendance! No absent lectures recorded for this subject.")
    else:
        st.markdown("#### ❌ Currently Cut / Absent Lectures:")
        for abs_key in subj_absents:
            abs_d, abs_t = get_absence_details(abs_key, cfg)
            
            st.markdown('<div class="stat-box">', unsafe_allow_html=True)
            c_abs_info, c_abs_btn = st.columns([3, 2])
            with c_abs_info:
                st.markdown(f"🗓️ **Date:** `{abs_d}`  \n⏰ **Time:** `{abs_t}`")
            with c_abs_btn:
                st.write(" ")
                if st.button("Mark Present", key=f"modal_rm_{abs_key}", type="primary"):
                    st.session_state['absent_records'].discard(abs_key)
                    save_absents_db(username, term_key, st.session_state['absent_records'])
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. MAIN DASHBOARD APPLICATION LOGIC
# ---------------------------------------------------------
def main_app():
    username = st.session_state['current_username']
    user_display = st.session_state['current_user']

    with st.sidebar:
        st.markdown(f'''
            <div class="user-profile-box">
                <h2 style="margin:0; font-size:18px; font-weight:700;">🎓 {user_display}</h2>
                <p style="margin:4px 0 0 0; font-size:12px; opacity:0.85;">Student Portal</p>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown('<div class="nav-header">Navigation Menu</div>', unsafe_allow_html=True)
        
        menu_items = [
            ("🎓 Daily Attendance", "🎓 Daily Attendance"),
            ("📊 Overall Overview", "📊 Overall Overview"),
            ("🚫 Cancel / Extra Lectures", "🚫 Cancel / Extra Lectures"),
            ("⚙️ Timetable Setup", "⚙️ Timetable Setup")
        ]
        
        for label, mode in menu_items:
            is_active = st.session_state['nav_mode'] == mode
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, use_container_width=True, type=btn_type, key=f"nav_{mode}"):
                st.session_state['nav_mode'] = mode
                st.rerun()

        st.write("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['current_user'] = ""
            st.session_state['current_username'] = ""
            if 'cfg' in st.session_state: del st.session_state['cfg']
            if 'absent_records' in st.session_state: del st.session_state['absent_records']
            st.rerun()

    # ACADEMIC YEAR & SEMESTER SELECTOR TOP BAR
    st.markdown('<div class="term-bar-card">', unsafe_allow_html=True)
    c_y, c_s, c_lbl = st.columns([2, 2, 3])
    with c_y:
        sel_y = st.selectbox("🎓 Select Academic Year:", YEAR_OPTIONS, index=YEAR_OPTIONS.index(st.session_state['selected_year']))
    with c_s:
        sel_s = st.selectbox("📚 Select Semester:", SEMESTER_OPTIONS, index=SEMESTER_OPTIONS.index(st.session_state['selected_semester']))
    
    term_key = f"{sel_y}_{sel_s}".replace(" ", "_")
    
    if sel_y != st.session_state['selected_year'] or sel_s != st.session_state['selected_semester']:
        st.session_state['selected_year'] = sel_y
        st.session_state['selected_semester'] = sel_s
        if 'cfg' in st.session_state: del st.session_state['cfg']
        if 'absent_records' in st.session_state: del st.session_state['absent_records']
        st.rerun()

    with c_lbl:
        st.markdown(f'''
            <div style="text-align: right; padding-top: 10px;">
                <span style="font-size: 12px; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Active Term</span><br>
                <span style="font-size: 18px; font-weight: 800; color: #38bdf8;">{sel_y} — {sel_s}</span>
            </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # LOAD TERM-SPECIFIC DATA SAFELY
    if 'cfg' not in st.session_state:
        loaded_cfg = load_user_config_db(username, term_key)
        if loaded_cfg:
            st.session_state['cfg'] = loaded_cfg
        else:
            st.session_state['cfg'] = {
                "setup_complete": False,
                "start_date": datetime.date.today(),
                "end_date": datetime.date.today() + datetime.timedelta(days=120),
                "registered_subjects": [],
                "mid_exam_dates": [],
                "custom_timetable": {day: [] for day in DAYS_OF_WEEK},
                "cancelled_lectures": [],
                "extra_lectures": []
            }

    if 'absent_records' not in st.session_state:
        st.session_state['absent_records'] = load_absents_db(username, term_key)

    cfg = st.session_state['cfg']
    nav_mode = st.session_state['nav_mode']

    # 1. SETUP & TIMETABLE MANAGEMENT
    if not cfg["setup_complete"] or nav_mode == "⚙️ Timetable Setup":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">⚙️ Timetable Setup — {sel_y} ({sel_s})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Define subjects first, then assign weekly lecture slots for this semester.</p>
            </div>
        ''', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        start_d = c1.date_input("Semester Start Date", value=cfg["start_date"])
        end_d = c2.date_input("Semester End Date", value=cfg["end_date"])

        mid_dates = st.date_input("Select Mid-Exam Date Range", value=(start_d + datetime.timedelta(days=30), start_d + datetime.timedelta(days=36)))

        st.write("---")
        st.subheader("1️⃣ Step 1: Add Semester Subjects")
        reg_subs = cfg.get("registered_subjects", [])
        
        c_sub_in, c_sub_btn = st.columns([3, 1])
        with c_sub_in:
            new_sub_name = st.text_input("New Subject Name:", placeholder="e.g. Organization Behavior", key="input_new_sub")
        with c_sub_btn:
            st.write(" ")
            st.write(" ")
            if st.button("➕ Add Subject", type="primary", use_container_width=True):
                if new_sub_name.strip() and new_sub_name.strip() not in reg_subs:
                    reg_subs.append(new_sub_name.strip())
                    cfg["registered_subjects"] = reg_subs
                    save_user_config_db(username, term_key, cfg)
                    st.success(f"Added {new_sub_name.strip()}!")
                    st.rerun()

        if reg_subs:
            st.write("**Currently Registered Subjects:**")
            sub_cols = st.columns(3)
            for idx, s_item in enumerate(reg_subs):
                with sub_cols[idx % 3]:
                    c_s_label, c_s_del = st.columns([4, 1])
                    c_s_label.info(f"📘 **{s_item}**")
                    if c_s_del.button("❌", key=f"del_sub_{idx}"):
                        reg_subs.pop(idx)
                        cfg["registered_subjects"] = reg_subs
                        save_user_config_db(username, term_key, cfg)
                        st.rerun()

        st.write("---")
        st.subheader("2️⃣ Step 2: Configure Weekly Timetable")

        if reg_subs:
            for day in DAYS_OF_WEEK:
                with st.expander(f"📌 **{day} Sessions**", expanded=True):
                    day_list = cfg["custom_timetable"].get(day, [])
                    updated_day_list = []
                    for idx, slot in enumerate(day_list):
                        col_subj, col_s_time, col_e_time, col_del = st.columns([3, 3, 3, 1])
                        with col_subj:
                            curr_val = slot["subject"] if slot["subject"] in reg_subs else reg_subs[0]
                            s_name = st.selectbox(f"Select Subject", reg_subs, index=reg_subs.index(curr_val), key=f"s_{day}_{idx}")
                        with col_s_time:
                            s_time = mobile_time_picker("Start Time", key_prefix=f"st_{day}_{idx}", default_time=slot["start_time"])
                        with col_e_time:
                            e_time = mobile_time_picker("End Time", key_prefix=f"et_{day}_{idx}", default_time=slot["end_time"])
                        with col_del:
                            st.write(" ")
                            st.write(" ")
                            if st.button("❌", key=f"del_{day}_{idx}"):
                                day_list.pop(idx)
                                st.rerun()
                        updated_day_list.append({"subject": s_name, "start_time": s_time, "end_time": e_time})

                    cfg["custom_timetable"][day] = updated_day_list
                    if st.button(f"➕ Add Session to {day}", key=f"add_{day}"):
                        cfg["custom_timetable"][day].append({"subject": reg_subs[0], "start_time": datetime.time(9, 0), "end_time": datetime.time(11, 0)})
                        st.rerun()

        if st.button(f"🚀 Save Setup for {sel_y} ({sel_s})", use_container_width=True, type="primary"):
            cfg["start_date"] = start_d
            cfg["end_date"] = end_d
            if isinstance(mid_dates, tuple) and len(mid_dates) == 2:
                m_start, m_end = mid_dates
                curr = m_start
                dates_list = []
                while curr <= m_end:
                    dates_list.append(curr.strftime("%Y-%m-%d"))
                    curr += datetime.timedelta(days=1)
                cfg["mid_exam_dates"] = dates_list
            cfg["setup_complete"] = True
            save_user_config_db(username, term_key, cfg)
            st.success("Semester Timetable Saved Successfully!")
            time.sleep(0.5)
            st.rerun()

    # 2. OVERALL OVERVIEW
    elif nav_mode == "📊 Overall Overview":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">📊 Academic Overview — {sel_y} ({sel_s})</h1>
            </div>
        ''', unsafe_allow_html=True)

        all_subjects_calc = cfg.get("registered_subjects", [])
        total_p_conducted = 0
        total_attended_all = 0
        for s_item in all_subjects_calc:
            s_st = calculate_subject_stats(s_item, cfg, st.session_state['absent_records'])
            total_p_conducted += s_st["past_conducted"]
            total_attended_all += s_st["attended"]
        
        overall_pct = (total_attended_all / total_p_conducted * 100) if total_p_conducted > 0 else 100.0
        health_status = "Good Standing" if overall_pct >= 80.0 else "Action Required"
        health_color = "#34d399" if overall_pct >= 80.0 else "#fb7185"

        today_date = datetime.date.today()
        start_d_cfg = cfg.get("start_date", today_date)
        days_passed = (today_date - start_d_cfg).days
        curr_week = max(1, math.ceil(days_passed / 7)) if days_passed >= 0 else 1

        st.markdown(f'''
            <div class="insights-banner-page">
                <div class="insight-item-page">
                    <div class="insight-icon-page">📈</div>
                    <div>
                        <div class="insight-label-page">Overall Attendance</div>
                        <div class="insight-val-page">{overall_pct:.1f}%</div>
                    </div>
                </div>
                <div class="insight-item-page">
                    <div class="insight-icon-page">📅</div>
                    <div>
                        <div class="insight-label-page">Academic Progress</div>
                        <div class="insight-val-page">Week {curr_week}</div>
                    </div>
                </div>
                <div class="insight-item-page">
                    <div class="insight-icon-page">🛡️</div>
                    <div>
                        <div class="insight-label-page">Eligibility Status</div>
                        <div class="insight-val-page" style="color: {health_color};">{health_status}</div>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

    # 3. CANCEL / EXTRA LECTURES
    elif nav_mode == "🚫 Cancel / Extra Lectures":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">🛠️ Cancel & Extra Lectures — {sel_y} ({sel_s})</h1>
            </div>
        ''', unsafe_allow_html=True)
        
        tab_cancel, tab_extra = st.tabs(["🚫 Cancel a Scheduled Lecture", "➕ Add an Extra Lecture"])
        all_subjects = cfg.get("registered_subjects", [])

        with tab_cancel:
            c_date = st.date_input("Select Cancel Date:", min_value=cfg["start_date"], max_value=cfg["end_date"], key="c_date")
            c_day_name = c_date.strftime("%A")
            day_lectures = cfg["custom_timetable"].get(c_day_name, [])
            day_subjects = sorted(list(set(l["subject"] for l in day_lectures)))

            if day_subjects:
                c_subj = st.selectbox("Select Subject to Cancel:", options=day_subjects, key="c_subj")
                if st.button("🚫 Cancel This Lecture", type="primary"):
                    c_date_str = c_date.strftime("%Y-%m-%d")
                    if not any(c["subject"] == c_subj and c["date"] == c_date_str for c in cfg["cancelled_lectures"]):
                        cfg["cancelled_lectures"].append({"subject": c_subj, "date": c_date_str})
                        save_user_config_db(username, term_key, cfg)
                        st.success("Cancelled successfully!")
                        time.sleep(0.5)
                        st.rerun()

            st.write("### 📋 Currently Cancelled Lectures")
            if cfg["cancelled_lectures"]:
                for idx, item in enumerate(cfg["cancelled_lectures"]):
                    col_info, col_btn = st.columns([4, 1])
                    col_info.write(f"❌ **{item['subject']}** on `{item['date']}`")
                    if col_btn.button("Restore", key=f"rest_{idx}"):
                        cfg["cancelled_lectures"].pop(idx)
                        save_user_config_db(username, term_key, cfg)
                        st.rerun()

        with tab_extra:
            if all_subjects:
                e_date = st.date_input("Select Extra Lecture Date:", min_value=cfg["start_date"], max_value=cfg["end_date"], key="e_date")
                e_subj = st.selectbox("Select Subject for Extra Class:", options=all_subjects, key="e_subj")
                col_st, col_et = st.columns(2)
                with col_st: e_st = mobile_time_picker("Start Time", key_prefix="e_st", default_time=datetime.time(9, 0))
                with col_et: e_et = mobile_time_picker("End Time", key_prefix="e_et", default_time=datetime.time(11, 0))

                if st.button("➕ Schedule Extra Lecture", type="primary"):
                    cfg["extra_lectures"].append({"subject": e_subj, "date": e_date.strftime("%Y-%m-%d"), "start_time": e_st, "end_time": e_et})
                    save_user_config_db(username, term_key, cfg)
                    st.success("Extra lecture scheduled!")
                    time.sleep(0.5)
                    st.rerun()

            st.write("### 📋 Scheduled Extra Lectures")
            if cfg["extra_lectures"]:
                for idx, item in enumerate(cfg["extra_lectures"]):
                    col_info, col_btn = st.columns([4, 1])
                    col_info.write(f"➕ **{item['subject']}** on `{item['date']}`")
                    if col_btn.button("Remove", key=f"rm_ext_{idx}"):
                        cfg["extra_lectures"].pop(idx)
                        save_user_config_db(username, term_key, cfg)
                        st.rerun()

    # 4. DAILY ATTENDANCE
    elif nav_mode == "🎓 Daily Attendance":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">🎓 Attendance Tracker — {sel_y} ({sel_s})</h1>
            </div>
        ''', unsafe_allow_html=True)
        
        col_main, col_stats = st.columns([2.2, 1.4])

        with col_main:
            st.markdown('<div class="tracker-card">', unsafe_allow_html=True)
            selected_date = st.date_input("Select Attendance Date:", value=datetime.date.today() if cfg["start_date"] <= datetime.date.today() <= cfg["end_date"] else cfg["start_date"], min_value=cfg["start_date"], max_value=cfg["end_date"])
            selected_str = selected_date.strftime("%Y-%m-%d")
            day_name = selected_date.strftime("%A")

            is_holiday = selected_str in HOLIDAYS_DB
            is_mid_exam = selected_str in cfg.get("mid_exam_dates", [])

            if is_holiday:
                st.markdown(f'<div class="holiday-card"><h3>🇱🇰 Holiday: {HOLIDAYS_DB[selected_str]}</h3></div>', unsafe_allow_html=True)
            elif is_mid_exam:
                st.markdown('<div class="exam-card"><h3>🚫 Mid-Exam Period</h3></div>', unsafe_allow_html=True)

            raw_lectures = cfg["custom_timetable"].get(day_name, [])
            cancelled_today = [c["subject"] for c in cfg.get("cancelled_lectures", []) if c["date"] == selected_str]
            active_lectures = [l for l in raw_lectures if l["subject"] not in cancelled_today]

            for ext in [e for e in cfg.get("extra_lectures", []) if e["date"] == selected_str]:
                active_lectures.append({"subject": ext["subject"], "start_time": ext["start_time"], "end_time": ext["end_time"], "is_extra": True})

            if not active_lectures:
                st.info("🎉 No lectures scheduled for this date!")
            else:
                subj_counter = {}
                for lec in active_lectures:
                    subj = lec["subject"]
                    subj_counter[subj] = subj_counter.get(subj, 0)
                    subj_idx = subj_counter[subj]
                    subj_counter[subj] += 1

                    formatted_time = f"{lec['start_time'].strftime('%I:%M %p')} - {lec['end_time'].strftime('%I:%M %p')}"
                    extra_tag = " (Extra Class)" if lec.get("is_extra") else ""
                    record_key = f"{selected_str}_{subj}_{subj_idx}"
                    is_absent = record_key in st.session_state['absent_records']

                    st.markdown('<div class="lecture-item-box">', unsafe_allow_html=True)
                    c_info, c_chk = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"<span style='font-size:16px; font-weight:700; color:#f8fafc;'>📖 {subj}</span><span style='color:#38bdf8;'>{extra_tag}</span>", unsafe_allow_html=True)
                        st.markdown(f"<span style='font-size:13px; color:#94a3b8;'>⏰ {formatted_time}</span>", unsafe_allow_html=True)
                    with c_chk:
                        absent_marked = st.checkbox("Mark Absent", value=is_absent, key=f"chk_{record_key}", disabled=is_holiday or is_mid_exam)
                        if absent_marked != is_absent:
                            if absent_marked: st.session_state['absent_records'].add(record_key)
                            else: st.session_state['absent_records'].discard(record_key)
                            save_absents_db(username, term_key, st.session_state['absent_records'])
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_stats:
            st.subheader("📊 Subject Progress & Stats")
            all_subjects = cfg.get("registered_subjects", [])
            if all_subjects:
                main_subjects = [s for s in all_subjects if not ("tutorial" in s.lower() or "tute" in s.lower())]
                tutorial_subjects = [s for s in all_subjects if ("tutorial" in s.lower() or "tute" in s.lower())]

                def render_card(subj, is_tute=False):
                    stats = calculate_subject_stats(subj, cfg, st.session_state['absent_records'])
                    card_class = "subject-card-tute" if is_tute else "subject-card-main"
                    is_eligible = stats["percentage"] >= 80.0
                    badge_html = f'<span class="badge-green">Eligible ({stats["percentage"]:.1f}%)</span>' if is_eligible else f'<span class="badge-red">At Risk ({stats["percentage"]:.1f}%)</span>'
                    
                    status_badge = f'<div class="status-badge-safe">🟢 Safe to miss <strong>{stats["safe_left"]}</strong> more lecture(s).</div>' if stats["safe_left"] >= 0 else f'<div class="status-badge-warning">🚨 Must attend <strong>{abs(stats["safe_left"])}</strong> future class(es)!</div>'

                    st.markdown(f'''
                    <div class="{card_class}">
                        <div class="card-header-flex"><h3 class="subject-title">{subj}</h3>{badge_html}</div>
                        <div class="metrics-grid">
                            <div class="metric-item"><div class="metric-label">Conducted</div><div class="metric-val">{stats["attended"]} / {stats["past_conducted"]}</div></div>
                            <div class="metric-item"><div class="metric-label">Absences</div><div class="metric-val" style="color:#fb7185;">{stats["absences"]}</div></div>
                            <div class="metric-item"><div class="metric-label">Max Allowed</div><div class="metric-val">{stats["max_allowed"]}</div></div>
                            <div class="metric-item"><div class="metric-label">Total</div><div class="metric-val">{stats["total"]}</div></div>
                        </div>
                        {status_badge}
                    </div>''', unsafe_allow_html=True)
                    
                    if st.button(f"🔍 View History", key=f"btn_mod_{subj}", use_container_width=True):
                        open_subject_modal(subj, cfg, username, term_key)

                for s in main_subjects: render_card(s, False)
                for s in tutorial_subjects: render_card(s, True)

    st.markdown('<div class="app-footer">© 2026 Academic Portal & Multi-Semester Tracker. All rights reserved.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. AUTHENTICATION ENTRY POINT (WITH "REMEMBER ME")
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_center, c_right = st.columns([1, 1.8, 1])

    with c_center:
        st.markdown('''
            <div class="auth-animated-card">
                <div class="auth-header-box">
                    <div class="auth-header-title">🎓 Academic Portal</div>
                    <div class="auth-subtitle">Multi-Semester Attendance & Academic Management System</div>
                </div>
        ''', unsafe_allow_html=True)
        
        auth_choice = st.radio("Select Action:", ["Login", "Register"], horizontal=True, label_visibility="collapsed")
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        if auth_choice == "Login":
            with st.form("login_form"):
                u_input = st.text_input("Username", value=st.session_state['remember_user'], placeholder="Enter your username")
                p_input = st.text_input("Password", value=st.session_state['remember_pass'], type="password", placeholder="Enter your password")
                remember_me = st.checkbox("Remember Me", value=bool(st.session_state['remember_user']))
                submit_login = st.form_submit_button("Sign In to Portal", type="primary", use_container_width=True)

            if submit_login:
                if u_input and p_input:
                    name = check_login_db(u_input, p_input)
                    if name:
                        st.session_state['logged_in'] = True
                        st.session_state['current_user'] = name
                        st.session_state['current_username'] = u_input.strip().lower()
                        if remember_me:
                            st.session_state['remember_user'] = u_input.strip().lower()
                            st.session_state['remember_pass'] = p_input
                        else:
                            st.session_state['remember_user'] = ""
                            st.session_state['remember_pass'] = ""
                        st.success(f"Welcome back, {name}!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")
                else:
                    st.warning("Please fill in all fields.")
        else:
            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="John Doe")
                reg_phone = st.text_input("Phone Number", placeholder="+94 XX XXX XXXX")
                reg_u = st.text_input("Create Username", placeholder="Choose unique username")
                reg_p = st.text_input("Create Password", type="password", placeholder="Choose password")
                submit_reg = st.form_submit_button("Create Student Account", type="primary", use_container_width=True)

            if submit_reg:
                if reg_name and reg_phone and reg_u and reg_p:
                    success = register_user_db(reg_u, reg_name, reg_phone, reg_p)
                    if success:
                        st.success("Account created successfully! Please log in.")
                    else:
                        st.error("Username already exists.")
                else:
                    st.warning("Please complete all fields.")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    main_app()
