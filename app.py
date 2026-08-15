import streamlit as st
import pandas as pd
import datetime
import time
import math
import sqlite3
import json

# ---------------------------------------------------------
# 0. DATABASE INITIALIZATION & HELPER FUNCTIONS
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('attendance_app.db')
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
            username TEXT PRIMARY KEY,
            config_json TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS absent_records (
            username TEXT,
            record_key TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def register_user_db(username, name, phone, password):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    try:
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (clean_u, name.strip(), phone.strip(), password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def check_login_db(username, password):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("SELECT name FROM users WHERE username=? AND password=?", (clean_u, password))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None

def load_user_config_db(username):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("SELECT config_json FROM user_configs WHERE username=?", (clean_u,))
    row = c.fetchone()
    conn.close()
    
    default_timetable = {day: [] for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
    default_sem_structure = {
        "start_date": datetime.date.today(),
        "end_date": datetime.date.today() + datetime.timedelta(days=120),
        "mid_exam_dates": [],
        "subjects": [],
        "timetable": default_timetable
    }
    
    default_config = {
        "setup_complete": False,
        "selected_year": "Year 1",
        "selected_semester": "Semester 1",
        "custom_timetables": {
            "Year 1": {"Semester 1": dict(default_sem_structure), "Semester 2": dict(default_sem_structure)},
            "Year 2": {"Semester 1": dict(default_sem_structure), "Semester 2": dict(default_sem_structure)},
            "Year 3": {"Semester 1": dict(default_sem_structure), "Semester 2": dict(default_sem_structure)},
            "Year 4": {"Semester 1": dict(default_sem_structure), "Semester 2": dict(default_sem_structure)}
        },
        "cancelled_lectures": [],
        "extra_lectures": []
    }

    if row:
        try:
            data = json.loads(row[0])
        except Exception:
            data = {}
            
        if "custom_timetables" not in data:
            old_timetable = data.get("custom_timetable", default_timetable)
            old_subjects = data.get("subjects_pool", sorted(list(set(l["subject"] for day in old_timetable for l in old_timetable[day]))))
            data["custom_timetables"] = {
                "Year 1": {"Semester 1": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": old_subjects, "timetable": old_timetable},
                           "Semester 2": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)}},
                "Year 2": {"Semester 1": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)},
                           "Semester 2": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)}},
                "Year 3": {"Semester 1": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)},
                           "Semester 2": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)}},
                "Year 4": {"Semester 1": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)},
                           "Semester 2": {"start_date": data.get("start_date", datetime.date.today()), "end_date": data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), "subjects": [], "timetable": dict(default_timetable)}}
            }
        
        for yr in ["Year 1", "Year 2", "Year 3", "Year 4"]:
            if yr not in data["custom_timetables"]:
                data["custom_timetables"][yr] = {"Semester 1": dict(default_sem_structure), "Semester 2": dict(default_sem_structure)}
            for sem in ["Semester 1", "Semester 2"]:
                if sem not in data["custom_timetables"][yr]:
                    data["custom_timetables"][yr][sem] = dict(default_sem_structure)
                else:
                    for k_sec, v_sec in default_sem_structure.items():
                        if k_sec not in data["custom_timetables"][yr][sem]:
                            data["custom_timetables"][yr][sem][k_sec] = v_sec

        if "selected_year" not in data or data["selected_year"] not in data["custom_timetables"]:
            data["selected_year"] = "Year 1"
        if "selected_semester" not in data or data["selected_semester"] not in data["custom_timetables"][data["selected_year"]]:
            data["selected_semester"] = "Semester 1"

        for yr in data["custom_timetables"]:
            for sem in data["custom_timetables"][yr]:
                sem_data = data["custom_timetables"][yr][sem]
                if isinstance(sem_data.get("start_date"), str):
                    try:
                        sem_data["start_date"] = datetime.datetime.strptime(sem_data["start_date"], "%Y-%m-%d").date()
                    except:
                        sem_data["start_date"] = datetime.date.today()
                if isinstance(sem_data.get("end_date"), str):
                    try:
                        sem_data["end_date"] = datetime.datetime.strptime(sem_data["end_date"], "%Y-%m-%d").date()
                    except:
                        sem_data["end_date"] = datetime.date.today() + datetime.timedelta(days=120)
                
                for day in sem_data.get("timetable", {}):
                    for session in sem_data["timetable"][day]:
                        if isinstance(session.get("start_time"), str):
                            try:
                                session["start_time"] = datetime.datetime.strptime(session["start_time"], "%H:%M:%S").time()
                            except:
                                session["start_time"] = datetime.time(9, 0)
                        if isinstance(session.get("end_time"), str):
                            try:
                                session["end_time"] = datetime.datetime.strptime(session["end_time"], "%H:%M:%S").time()
                            except:
                                session["end_time"] = datetime.time(11, 0)
                
        for ext in data.get("extra_lectures", []):
            if isinstance(ext.get("start_time"), str):
                try:
                    ext["start_time"] = datetime.datetime.strptime(ext["start_time"], "%H:%M:%S").time()
                except:
                    ext["start_time"] = datetime.time(9, 0)
            if isinstance(ext.get("end_time"), str):
                try:
                    ext["end_time"] = datetime.datetime.strptime(ext["end_time"], "%H:%M:%S").time()
                except:
                    ext["end_time"] = datetime.time(11, 0)
                
        return data
    return default_config

def save_user_config_db(username, config):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    cfg_copy = json.loads(json.dumps(config, default=str))
    c.execute("INSERT OR REPLACE INTO user_configs VALUES (?, ?)", (clean_u, json.dumps(cfg_copy)))
    conn.commit()
    conn.close()

def load_absents_db(username):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("SELECT record_key FROM absent_records WHERE username=?", (clean_u,))
    rows = c.fetchall()
    conn.close()
    return set(r[0] for r in rows)

def save_absents_db(username, absent_set):
    conn = sqlite3.connect('attendance_app.db')
    c = conn.cursor()
    clean_u = username.strip().lower()
    c.execute("DELETE FROM absent_records WHERE username=?", (clean_u,))
    for key in absent_set:
        c.execute("INSERT INTO absent_records VALUES (?, ?)", (clean_u, key))
    conn.commit()
    conn.close()

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
    
    with c1:
        selected_h = st.selectbox("Hour", hours, index=hours.index(f"{default_h12:02d}"), key=f"{key_prefix}_h")
    with c2:
        selected_m = st.selectbox("Min", minutes, index=minutes.index(f"{default_time.minute:02d}"), key=f"{key_prefix}_m")
    with c3:
        selected_ampm = st.selectbox("Format", ampm_list, index=ampm_list.index(default_ampm), key=f"{key_prefix}_ap")
    
    h24 = int(selected_h)
    if selected_ampm == "PM" and h24 != 12:
        h24 += 12
    elif selected_ampm == "AM" and h24 == 12:
        h24 = 0
        
    return datetime.time(h24, int(selected_m))

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & FULLY RESPONSIVE UI STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Academic Portal & Attendance Tracker", page_icon="🎓", layout="wide")

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
    from {
        opacity: 0;
        transform: translateY(16px) scale(0.99);
    }
    to {
        opacity: 1;
        transform: translateY(0) scale(1);
    }
}

.auth-container {
    max-width: 650px;
    margin: 40px auto;
    animation: fadeInUp 0.5s ease-out forwards;
}

.auth-hero-banner {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.9) 0%, rgba(11, 15, 25, 0.95) 100%);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 20px;
    padding: 30px 20px;
    text-align: center;
    margin-bottom: 25px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(20px);
}

.auth-hero-title {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.auth-hero-subtitle {
    color: #94a3b8;
    font-size: 13px;
    font-weight: 500;
}

.auth-form-card {
    background: linear-gradient(145deg, rgba(17, 24, 39, 0.85) 0%, rgba(11, 15, 25, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 32px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(20px);
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #fb4b52 0%, #f43f5e 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    height: 48px !important;
    box-shadow: 0 4px 14px rgba(244, 63, 94, 0.35) !important;
    transition: all 0.2s ease-in-out !important;
}

div.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(244, 63, 94, 0.5) !important;
}

.dashboard-header {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.8) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 26px 32px;
    margin-bottom: 18px;
    box-shadow: 0 15px 30px rgba(0,0,0,0.4);
    backdrop-filter: blur(20px);
    animation: fadeInUp 0.4s ease-out;
}

.dashboard-title {
    font-size: 30px !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 !important;
    letter-spacing: -0.5px;
}

.tracker-card {
    background: linear-gradient(145deg, rgba(17, 24, 39, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 24px;
    backdrop-filter: blur(16px);
    animation: fadeInUp 0.4s ease-out;
}

.subject-card-main, .subject-card-tute {
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(14px);
    animation: fadeInUp 0.5s ease-out;
}

.subject-card-main {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(99, 102, 241, 0.25);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
}

.subject-card-tute {
    background: linear-gradient(145deg, rgba(30, 27, 75, 0.65) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(168, 85, 247, 0.3);
    box-shadow: 0 10px 25px -5px rgba(88, 28, 135, 0.25);
}

.card-header-flex {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
}

.subject-title {
    font-size: 18px;
    font-weight: 700;
    color: #f8fafc;
    margin: 0;
}

.badge-green {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.35);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}

.badge-red {
    background: rgba(244, 63, 94, 0.15);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.35);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
}

.holiday-card {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
    color: white;
    padding: 18px;
    border-radius: 16px;
    border-left: 5px solid #38bdf8;
    margin-bottom: 18px;
    animation: fadeInUp 0.4s ease-out;
}

.exam-card {
    background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%);
    color: white;
    padding: 18px;
    border-radius: 16px;
    border-left: 5px solid #818cf8;
    margin-bottom: 18px;
    animation: fadeInUp 0.4s ease-out;
}

.stat-box {
    background: rgba(30, 41, 59, 0.4);
    border-radius: 14px;
    padding: 16px;
    border: 1px solid rgba(255, 255, 255, 0.07);
    margin-bottom: 12px;
}

div[data-testid="stSidebar"] {
    background: #080c14 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.user-profile-box {
    background: linear-gradient(135deg, #4f46e5 0%, #0284c7 100%);
    padding: 18px;
    border-radius: 16px;
    color: white;
    text-align: center;
    margin-bottom: 22px;
    box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3);
}

.nav-header {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #64748b;
    margin-bottom: 12px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CONSTANTS & SESSION STATE INITIALIZATION
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

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = ""
if 'current_username' not in st.session_state:
    st.session_state['current_username'] = ""
if 'auth_mode' not in st.session_state:
    st.session_state['auth_mode'] = "Login"
if 'nav_mode' not in st.session_state:
    st.session_state['nav_mode'] = "📊 Subject Progress & Stats"

# ---------------------------------------------------------
# 3. ACCURATE STATS CALCULATION & DIALOGS
# ---------------------------------------------------------
def get_active_semester_data(cfg):
    yr = cfg.get("selected_year", "Year 1")
    sem = cfg.get("selected_semester", "Semester 1")
    if yr not in cfg.get("custom_timetables", {}):
        cfg["custom_timetables"][yr] = {}
    if sem not in cfg["custom_timetables"][yr]:
        default_timetable = {day: [] for day in DAYS_OF_WEEK}
        cfg["custom_timetables"][yr][sem] = {
            "start_date": datetime.date.today(),
            "end_date": datetime.date.today() + datetime.timedelta(days=120),
            "mid_exam_dates": [],
            "subjects": [],
            "timetable": default_timetable
        }
    return cfg["custom_timetables"][yr][sem]

def is_tutorial_subject(subj):
    s_low = subj.lower()
    return "tute" in s_low or "tutorial" in s_low or "practical" in s_low or "lab" in s_low

def calculate_subject_stats(subj, cfg, absent_records):
    sem_data = get_active_semester_data(cfg)
    start_d = sem_data["start_date"]
    end_d = sem_data["end_date"]
    today = datetime.date.today()
    
    total_lectures = 0
    past_conducted_lectures = 0
    curr_d = start_d
    
    while curr_d <= end_d:
        d_str = curr_d.strftime("%Y-%m-%d")
        d_name = curr_d.strftime("%A")
        
        is_holiday = d_str in HOLIDAYS_DB
        is_mid = d_str in sem_data.get("mid_exam_dates", [])
        
        if not is_holiday and not is_mid:
            day_slots = sem_data["timetable"].get(d_name, [])
            for slot in day_slots:
                if slot["subject"] == subj:
                    is_cancelled = any(c["subject"] == subj and c["date"] == d_str for c in cfg.get("cancelled_lectures", []))
                    if not is_cancelled:
                        total_lectures += 1
                        if curr_d <= today:
                            past_conducted_lectures += 1
                        
            for ext in cfg.get("extra_lectures", []):
                if ext.get("year") == cfg.get("selected_year") and ext.get("semester") == cfg.get("selected_semester"):
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
        idx = int(parts[2])
        
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = date_obj.strftime("%A")
        
        sem_data = get_active_semester_data(cfg)
        active_slots = []
        regular_slots = sem_data["timetable"].get(day_name, [])
        cancelled_today = [c["subject"] for c in cfg.get("cancelled_lectures", []) if c["date"] == date_str]
        
        for slot in regular_slots:
            if slot["subject"] not in cancelled_today:
                active_slots.append(slot)
                
        for ext in cfg.get("extra_lectures", []):
            if ext.get("year") == cfg.get("selected_year") and ext.get("semester") == cfg.get("selected_semester"):
                if ext["date"] == date_str:
                    active_slots.append(ext)
                
        subj_slots = [s for s in active_slots if s["subject"] == subj]
        
        if idx < len(subj_slots):
            st_t = subj_slots[idx]["start_time"]
            end_t = subj_slots[idx]["end_time"]
            time_str = f"{st_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}"
            return date_str, time_str
        elif subj_slots:
            st_t = subj_slots[0]["start_time"]
            end_t = subj_slots[0]["end_time"]
            return date_str, f"{st_t.strftime('%I:%M %p')} - {end_t.strftime('%I:%M %p')}"
            
        return date_str, "Scheduled Time"
    return "Unknown Date", "Unknown Time"

@st.dialog("📅 Absent Records & Lecture History")
def open_subject_modal(subj, cfg, username):
    st.markdown(f"### 📚 Subject: **{subj}**")
    st.write("---")
    
    current_absents = st.session_state.get('absent_records', set())
    subj_absents = [r for r in current_absents if f"_{subj}_" in r]
    
    if not subj_absents:
        st.success("🎉 Perfect Attendance! No absent lectures recorded for this subject.")
    else:
        st.markdown("#### ❌ Currently Cut / Absent Lectures (Date & Time):")
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
                    save_absents_db(username, st.session_state['absent_records'])
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. MAIN DASHBOARD & APPLICATION LOGIC
# ---------------------------------------------------------
def main_app():
    username = st.session_state['current_username']
    user_display = st.session_state['current_user']

    if 'cfg' not in st.session_state:
        st.session_state['cfg'] = load_user_config_db(username)

    if 'absent_records' not in st.session_state:
        st.session_state['absent_records'] = load_absents_db(username)

    cfg = st.session_state['cfg']

    with st.sidebar:
        st.markdown(f'''
            <div class="user-profile-box">
                <h2 style="margin:0; font-size:18px; font-weight:700;">🎓 {user_display}</h2>
                <p style="margin:4px 0 0 0; font-size:12px; opacity:0.85;">Student Portal</p>
            </div>
        ''', unsafe_allow_html=True)
        
        st.markdown('<div class="nav-header">Active Academic Session</div>', unsafe_allow_html=True)
        sel_yr = st.selectbox("Select Year", ["Year 1", "Year 2", "Year 3", "Year 4"], index=["Year 1", "Year 2", "Year 3", "Year 4"].index(cfg.get("selected_year", "Year 1")), key="global_sel_yr")
        sel_sem = st.selectbox("Select Semester", ["Semester 1", "Semester 2"], index=["Semester 1", "Semester 2"].index(cfg.get("selected_semester", "Semester 1")), key="global_sel_sem")
        
        if sel_yr != cfg.get("selected_year") or sel_sem != cfg.get("selected_semester"):
            cfg["selected_year"] = sel_yr
            cfg["selected_semester"] = sel_sem
            save_user_config_db(username, cfg)
            st.rerun()

        st.markdown('<div class="nav-header">Navigation Menu</div>', unsafe_allow_html=True)
        
        menu_items = [
            ("📊 Subject Progress & Stats", "📊 Subject Progress & Stats"),
            ("🎓 Daily Attendance", "🎓 Daily Attendance"),
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

    nav_mode = st.session_state['nav_mode']
    sem_data = get_active_semester_data(cfg)

    if not cfg.get("setup_complete", False) or nav_mode == "⚙️ Timetable Setup":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">⚙️ Timetable Setup ({cfg["selected_year"]} - {cfg["selected_semester"]})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Configure your academic semester timeline, subject pool, and weekly lecture schedules for the selected year and semester.</p>
            </div>
        ''', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        start_d = c1.date_input("Semester Start Date", value=sem_data.get("start_date", datetime.date.today()), key=f"setup_start_{cfg['selected_year']}_{cfg['selected_semester']}")
        end_d = c2.date_input("Semester End Date", value=sem_data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), key=f"setup_end_{cfg['selected_year']}_{cfg['selected_semester']}")

        mid_dates = st.date_input("Select Mid-Exam Date Range", value=(start_d + datetime.timedelta(days=30), start_d + datetime.timedelta(days=36)), key=f"setup_mid_{cfg['selected_year']}_{cfg['selected_semester']}")

        st.write("---")
        st.subheader("📚 Subject Pool Registration")
        st.caption("💡 *Add all subjects for this semester first before building your weekly timetable below.*")
        
        current_subjects = sem_data.get("subjects", [])
        new_subj_input = st.text_input("Add New Subject Name", key=f"new_subj_input_{cfg['selected_year']}_{cfg['selected_semester']}")
        if st.button("➕ Add Subject to Pool", key=f"btn_add_subj_{cfg['selected_year']}_{cfg['selected_semester']}"):
            if new_subj_input.strip() and new_subj_input.strip() not in current_subjects:
                current_subjects.append(new_subj_input.strip())
                sem_data["subjects"] = current_subjects
                save_user_config_db(username, cfg)
                st.success(f"Added '{new_subj_input.strip()}' to subjects pool!")
                st.rerun()

        if current_subjects:
            st.write("**Registered Subjects in this Semester:**")
            for idx_s, s_item in enumerate(current_subjects):
                col_s_name, col_s_del = st.columns([4, 1])
                with col_s_name:
                    st.markdown(f"- `{s_item}`")
                with col_s_del:
                    if st.button("🗑️ Remove", key=f"del_subj_{cfg['selected_year']}_{cfg['selected_semester']}_{idx_s}"):
                        current_subjects.pop(idx_s)
                        sem_data["subjects"] = current_subjects
                        save_user_config_db(username, cfg)
                        st.rerun()
        else:
            st.info("No subjects added yet for this semester. Add subjects above first.")

        st.write("---")
        st.subheader("🗓️ Weekly Timetable")
        st.caption("💡 *Note: Select subjects from your registered subject pool dropdown menu.*")

        for day in DAYS_OF_WEEK:
            with st.expander(f"📌 **{day} Sessions**", expanded=True):
                day_list = sem_data["timetable"].get(day, [])
                updated_day_list = []
                for idx, slot in enumerate(day_list):
                    col_subj, col_s_time, col_e_time, col_del = st.columns([3, 3, 3, 1])
                    with col_subj:
                        sub_options = sem_data.get("subjects", [])
                        current_sub = slot.get("subject", "")
                        if current_sub not in sub_options and current_sub != "":
                            sub_options = [current_sub] + sub_options
                        if not sub_options:
                            sub_options = ["Please Add Subjects First"]
                        
                        default_idx = sub_options.index(current_sub) if current_sub in sub_options else 0
                        s_name = st.selectbox(f"Subject Name", options=sub_options, index=default_idx, key=f"s_{day}_{idx}_{cfg['selected_year']}_{cfg['selected_semester']}")
                    with col_s_time:
                        s_time = mobile_time_picker("Start Time", key_prefix=f"st_{day}_{idx}_{cfg['selected_year']}_{cfg['selected_semester']}", default_time=slot.get("start_time", datetime.time(9,0)))
                    with col_e_time:
                        e_time = mobile_time_picker("End Time", key_prefix=f"et_{day}_{idx}_{cfg['selected_year']}_{cfg['selected_semester']}", default_time=slot.get("end_time", datetime.time(11,0)))
                    with col_del:
                        st.write(" ")
                        st.write(" ")
                        if st.button("❌", key=f"del_{day}_{idx}_{cfg['selected_year']}_{cfg['selected_semester']}"):
                            day_list.pop(idx)
                            st.rerun()
                    if s_name.strip() and s_name != "Please Add Subjects First":
                        updated_day_list.append({"subject": s_name.strip(), "start_time": s_time, "end_time": e_time})

                sem_data["timetable"][day] = updated_day_list
                if st.button(f"➕ Add Session to {day}", key=f"add_{day}_{cfg['selected_year']}_{cfg['selected_semester']}"):
                    sem_data["timetable"][day].append({"subject": sem_data["subjects"][0] if sem_data["subjects"] else "New Subject", "start_time": datetime.time(9, 0), "end_time": datetime.time(11, 0)})
                    st.rerun()

        if st.button("🚀 Save Setup & Launch Dashboard", use_container_width=True, type="primary"):
            sem_data["start_date"] = start_d
            sem_data["end_date"] = end_d
            if isinstance(mid_dates, tuple) and len(mid_dates) == 2:
                m_start, m_end = mid_dates
                curr = m_start
                dates_list = []
                while curr <= m_end:
                    dates_list.append(curr.strftime("%Y-%m-%d"))
                    curr += datetime.timedelta(days=1)
                sem_data["mid_exam_dates"] = dates_list
            cfg["setup_complete"] = True
            
            save_user_config_db(username, cfg)
            st.success("Setup Saved Permanently!")
            time.sleep(0.5)
            st.rerun()

    elif nav_mode == "📊 Subject Progress & Stats":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">📊 Subject Progress & Stats ({cfg["selected_year"]} - {cfg["selected_semester"]})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Detailed progress, cuts/absences, and safe attendance margins for every subject.</p>
            </div>
        ''', unsafe_allow_html=True)

        all_subjects_calc = sorted(list(set(l["subject"] for day in sem_data.get("timetable", {}) for l in sem_data["timetable"][day])))
        
        if not all_subjects_calc:
            st.info("No subjects found in the timetable for this semester. Please configure your timetable in the setup section.")
        else:
            for subj in all_subjects_calc:
                s_stat = calculate_subject_stats(subj, cfg, st.session_state['absent_records'])
                
                pct = s_stat['percentage']
                is_at_risk = pct < 80.0
                status_badge = f'<div style="background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.35); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">At Risk ({pct:.1f}%)</div>' if is_at_risk else f'<div style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700;">Good ({pct:.1f}%)</div>'

                st.markdown(f'''
                    <div class="tracker-card">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px;">
                            <h2 style="margin: 0; font-size: 22px; color: #f8fafc; font-weight: 700;">{subj}</h2>
                            {status_badge}
                        </div>
                ''', unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Conducted</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["past_conducted"]} / {s_stat["total"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Cuts / Absences</div>
                            <div style="font-size: 22px; font-weight: 800; color: #fb7185;">{s_stat["absences"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)

                col3, col4 = st.columns(2)
                with col3:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Max Allowed Cuts</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["max_allowed"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'''
                        <div class="stat-box">
                            <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Total Semester</div>
                            <div style="font-size: 22px; font-weight: 800; color: #f8fafc;">{s_stat["total"]}</div>
                        </div>
                    ''', unsafe_allow_html=True)

                safe_left_val = s_stat["safe_left"]
                st.markdown(f'''
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 14px; padding: 14px 18px; margin-bottom: 16px; color: #34d399; font-weight: 600; font-size: 14px;">
                        🟢 Safe to miss {safe_left_val} more lecture(s).
                    </div>
                ''', unsafe_allow_html=True)

                if st.button(f"🔍 View History / Manage Absences", key=f"btn_hist_{subj}", use_container_width=True):
                    open_subject_modal(subj, cfg, username)

                st.markdown('</div>', unsafe_allow_html=True)

    elif nav_mode == "🚫 Cancel / Extra Lectures":
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">🛠️ Manage Cancelled & Extra Lectures ({cfg["selected_year"]} - {cfg["selected_semester"]})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Adjust scheduled lectures or add special make-up classes.</p>
            </div>
        ''', unsafe_allow_html=True)
        
        tab_cancel, tab_extra = st.tabs(["🚫 Cancel a Scheduled Lecture", "➕ Add an Extra Lecture"])
        all_subjects = sorted(list(set(l["subject"] for day in sem_data.get("timetable", {}) for l in sem_data["timetable"][day])))

        with tab_cancel:
            st.subheader("Cancel a Lecture for a Specific Date")
            if not all_subjects:
                st.warning("Please setup your timetable first in Timetable Setup!")
            else:
                c_date = st.date_input("Select Cancel Date:", min_value=sem_data.get("start_date", datetime.date.today()), max_value=sem_data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), key="c_date")
                c_day_name = c_date.strftime("%A")
                
                day_lectures = sem_data["timetable"].get(c_day_name, [])
                day_subjects = sorted(list(set(l["subject"] for l in day_lectures)))

                if not day_subjects:
                    st.info(f"No regular lectures scheduled on {c_day_name}s.")
                else:
                    c_subj = st.selectbox("Select Subject to Cancel:", options=day_subjects, key="c_subj")
                    
                    if st.button("🚫 Cancel This Lecture", type="primary"):
                        c_date_str = c_date.strftime("%Y-%m-%d")
                        if not any(c["subject"] == c_subj and c["date"] == c_date_str for c in cfg.get("cancelled_lectures", [])):
                            cfg.setdefault("cancelled_lectures", []).append({"subject": c_subj, "date": c_date_str})
                            save_user_config_db(username, cfg)
                            st.success(f"Successfully cancelled {c_subj} on {c_date_str}!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.warning("This lecture is already cancelled.")

        with tab_extra:
            st.subheader("Add an Extra Lecture / Make-up Class")
            if not all_subjects:
                st.warning("Please setup your timetable first in Timetable Setup!")
            else:
                e_subj = st.selectbox("Select Subject:", options=all_subjects, key="e_subj")
                e_date = st.date_input("Select Date:", min_value=sem_data.get("start_date", datetime.date.today()), max_value=sem_data.get("end_date", datetime.date.today() + datetime.timedelta(days=120)), key="e_date")
                e_st = mobile_time_picker("Start Time", key_prefix="e_st", default_time=datetime.time(9, 0))
                e_et = mobile_time_picker("End Time", key_prefix="e_et", default_time=datetime.time(11, 0))

                if st.button("➕ Add Extra Lecture", type="primary"):
                    e_date_str = e_date.strftime("%Y-%m-%d")
                    cfg.setdefault("extra_lectures", []).append({
                        "year": cfg["selected_year"],
                        "semester": cfg["selected_semester"],
                        "subject": e_subj,
                        "date": e_date_str,
                        "start_time": e_st,
                        "end_time": e_et
                    })
                    save_user_config_db(username, cfg)
                    st.success(f"Added extra lecture for {e_subj} on {e_date_str}!")
                    time.sleep(0.5)
                    st.rerun()

    else:
        st.markdown(f'''
            <div class="dashboard-header">
                <h1 class="dashboard-title">🎓 Daily Attendance ({cfg["selected_year"]} - {cfg["selected_semester"]})</h1>
                <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 14px;">Track your lectures and record attendances or absences.</p>
            </div>
        ''', unsafe_allow_html=True)

        sem_start = sem_data.get("start_date")
        sem_end = sem_data.get("end_date")

        sel_date = st.date_input("Select Attendance Date:", value=datetime.date.today(), key="daily_att_date")
        d_str = sel_date.strftime("%Y-%m-%d")
        d_name = sel_date.strftime("%A")

        if sem_start and sem_end and not (sem_start <= sel_date <= sem_end):
            st.markdown(f'''
                <div class="exam-card" style="background: linear-gradient(135deg, #334155 100%, #1e293b 100%); border-left: 5px solid #64748b;">
                    <h2>⌛ Semester Ended / Not Started</h2>
                    <p style="margin:0; font-size:15px;">Selected date (`{d_str}`) falls outside the active semester timeline (`{sem_start}` to `{sem_end}`). Semester is over or has not yet begun for this date range!</p>
                </div>
            ''', unsafe_allow_html=True)
        else:
            is_holiday = d_str in HOLIDAYS_DB
            is_mid = d_str in sem_data.get("mid_exam_dates", [])

            if is_holiday:
                st.markdown(f'''
                    <div class="holiday-card">
                        <h2>🎉 Holiday Today!</h2>
                        <p style="margin:0; font-size:15px;">{HOLIDAYS_DB[d_str]}</p>
                    </div>
                ''', unsafe_allow_html=True)
            elif is_mid:
                st.markdown(f'''
                    <div class="exam-card">
                        <h2>📝 Mid-Examination Period</h2>
                        <p style="margin:0; font-size:15px;">No regular lectures scheduled during examination days.</p>
                    </div>
                ''', unsafe_allow_html=True)
            else:
                regular_slots = sem_data["timetable"].get(d_name, [])
                cancelled_today = [c["subject"] for c in cfg.get("cancelled_lectures", []) if c["date"] == d_str]
                
                active_slots = []
                for slot in regular_slots:
                    if slot["subject"] not in cancelled_today:
                        active_slots.append(slot)
                        
                for ext in cfg.get("extra_lectures", []):
                    if ext.get("year") == cfg.get("selected_year") and ext.get("semester") == cfg.get("selected_semester"):
                        if ext["date"] == d_str:
                            active_slots.append(ext)

                if not active_slots:
                    st.info(f"No lectures scheduled for {d_name} ({d_str}).")
                else:
                    st.markdown(f"### 📋 Lectures for {d_name} ({d_str})")
                    
                    subj_occurrence_counts = {}
                    
                    for idx, slot in enumerate(active_slots):
                        subj = slot["subject"]
                        subj_occurrence_counts[subj] = subj_occurrence_counts.get(subj, 0) + 1
                        slot_index_in_subj = subj_occurrence_counts[subj] - 1
                        
                        rec_key = f"{d_str}_{subj}_{slot_index_in_subj}"
                        is_absent = rec_key in st.session_state['absent_records']
                        
                        st_t = slot["start_time"].strftime("%I:%M %p") if isinstance(slot["start_time"], datetime.time) else "09:00 AM"
                        end_t = slot["end_time"].strftime("%I:%M %p") if isinstance(slot["end_time"], datetime.time) else "11:00 AM"
                        
                        is_tute = is_tutorial_subject(subj)
                        card_class = "subject-card-tute" if is_tute else "subject-card-main"
                        
                        st.markdown(f'''
                            <div class="{card_class}">
                                <div class="card-header-flex">
                                    <h3 class="subject-title">📚 {subj}</h3>
                                    {'<span class="badge-red">ABSENT</span>' if is_absent else '<span class="badge-green">ATTENDED</span>'}
                                </div>
                                <p style="color: #cbd5e1; margin: 0 0 10px 0; font-size: 14px;">⏰ <b>Time:</b> {st_t} - {end_t}</p>
                        ''', unsafe_allow_html=True)
                        
                        c_btn1, c_btn2, c_btn3 = st.columns([2, 2, 2])
                        with c_btn1:
                            if is_absent:
                                if st.button("✅ Mark Present", key=f"pres_{rec_key}", type="primary"):
                                    st.session_state['absent_records'].discard(rec_key)
                                    save_absents_db(username, st.session_state['absent_records'])
                                    st.rerun()
                            else:
                                if st.button("❌ Mark Absent", key=f"abs_{rec_key}"):
                                    st.session_state['absent_records'].add(rec_key)
                                    save_absents_db(username, st.session_state['absent_records'])
                                    st.rerun()
                        with c_btn2:
                            if st.button("📊 View Stats & History", key=f"modal_btn_{rec_key}"):
                                open_subject_modal(subj, cfg, username)
                                
                        st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. AUTHENTICATION UI & ENTRYPOINT
# ---------------------------------------------------------
def auth_screen():
    query_params = st.query_params
    saved_user_param = query_params.get("saved_user", "")
    saved_pass_param = query_params.get("saved_pass", "")

    st.markdown('<div class="auth-container">', unsafe_allow_html=True)
    
    st.markdown('''
        <div class="auth-hero-banner">
            <div class="auth-hero-title">🎓 Academic Portal</div>
            <div class="auth-hero-subtitle">Lecture Attendance & Academic Management System</div>
        </div>
    ''', unsafe_allow_html=True)

    st.markdown('<div class="auth-form-card">', unsafe_allow_html=True)

    auth_choice = st.radio("", ["Login", "Register"], horizontal=True, key="auth_radio_mode")

    st.write("")

    if auth_choice == "Login":
        l_user = st.text_input("Username", value=saved_user_param, key="login_username")
        l_pass = st.text_input("Password", value=saved_pass_param, type="password", key="login_password")
        remember_me = st.checkbox("Remember My Password", value=bool(saved_user_param))
        
        st.write("")
        if st.button("Sign In to Portal", use_container_width=True, type="primary"):
            if not l_user or not l_pass:
                st.error("Please fill in all fields.")
            else:
                name_found = check_login_db(l_user, l_pass)
                if name_found:
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = name_found
                    st.session_state['current_username'] = l_user.strip().lower()
                    
                    if remember_me:
                        st.query_params["saved_user"] = l_user.strip()
                        st.query_params["saved_pass"] = l_pass
                    else:
                        if "saved_user" in st.query_params:
                            del st.query_params["saved_user"]
                        if "saved_pass" in st.query_params:
                            del st.query_params["saved_pass"]

                    st.success("Login Successful!")
                    time.sleep(0.4)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    else:
        r_user = st.text_input("Choose Username", key="reg_username")
        r_name = st.text_input("Full Name", key="reg_name")
        r_phone = st.text_input("Phone Number", key="reg_phone")
        r_pass = st.text_input("Choose Password", type="password", key="reg_password")
        
        st.write("")
        if st.button("Create New Account", use_container_width=True, type="primary"):
            if not r_user or not r_name or not r_phone or not r_pass:
                st.error("Please fill in all registration fields.")
            else:
                success = register_user_db(r_user, r_name, r_phone, r_pass)
                if success:
                    st.success("Account created successfully! Please switch back to Login.")
                else:
                    st.error("Username already taken. Choose another.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# RUNTIME CONTROLLER
# ---------------------------------------------------------
if not st.session_state['logged_in']:
    auth_screen()
else:
    main_app()
