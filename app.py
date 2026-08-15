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
            record_key TEXT,
            PRIMARY KEY (username, record_key)
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
    if row:
        data = json.loads(row[0])
        data["start_date"] = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        data["end_date"] = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        
        for day in data["custom_timetable"]:
            for session in data["custom_timetable"][day]:
                session["start_time"] = datetime.datetime.strptime(session["start_time"], "%H:%M:%S").time()
                session["end_time"] = datetime.datetime.strptime(session["end_time"], "%H:%M:%S").time()
                
        for ext in data.get("extra_lectures", []):
            ext["start_time"] = datetime.datetime.strptime(ext["start_time"], "%H:%M:%S").time()
            ext["end_time"] = datetime.datetime.strptime(ext["end_time"], "%H:%M:%S").time()
            
        return data
    return None

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
    
    # Hour selection (1-12)
    default_h12 = default_time.hour % 12
    default_h12 = 12 if default_h12 == 0 else default_h12
    hours = [f"{i:02d}" for i in range(1, 13)]
    
    # Minute selection (00-59)
    minutes = [f"{i:02d}" for i in range(60)]
    
    # AM/PM selection
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
# 1. PAGE CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(page_title="Lecture Attendance Tracker", page_icon="🎓", layout="wide")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    font-family: 'Inter', sans-serif;
}
.auth-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 30px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}
.holiday-card {
    background: linear-gradient(135deg, #d97706 0%, #b45309 100%);
    color: white;
    padding: 15px;
    border-radius: 12px;
    border-left: 6px solid #fef08a;
    margin-bottom: 20px;
}
.exam-card {
    background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
    color: white;
    padding: 15px;
    border-radius: 12px;
    border-left: 6px solid #fca5a5;
    margin-bottom: 20px;
}
.stat-box {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 10px;
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


# ---------------------------------------------------------
# 3. HELPER MATH FUNCTION (80% ATTENDANCE CALCULATION)
# ---------------------------------------------------------
def calculate_subject_stats(subj, cfg, absent_records):
    start_d = cfg["start_date"]
    end_d = cfg["end_date"]
    
    total_lectures = 0
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
                        
            for ext in cfg.get("extra_lectures", []):
                if ext["subject"] == subj and ext["date"] == d_str:
                    total_lectures += 1
                    
        curr_d += datetime.timedelta(days=1)

    absences = sum(1 for rec in absent_records if f"_{subj}_" in rec)
    attended = max(0, total_lectures - absences)
    
    curr_percentage = (attended / total_lectures * 100) if total_lectures > 0 else 100.0
    
    max_allowed_absences = math.floor(total_lectures * 0.20)
    safe_absences_left = max_allowed_absences - absences

    return {
        "total": total_lectures,
        "absences": absences,
        "attended": attended,
        "percentage": curr_percentage,
        "max_allowed": max_allowed_absences,
        "safe_left": safe_absences_left
    }


# ---------------------------------------------------------
# 4. MAIN DASHBOARD & APPLICATION LOGIC
# ---------------------------------------------------------
def main_app():
    username = st.session_state['current_username']
    user_display = st.session_state['current_user']

    if 'cfg' not in st.session_state:
        loaded_cfg = load_user_config_db(username)
        if loaded_cfg:
            st.session_state['cfg'] = loaded_cfg
        else:
            st.session_state['cfg'] = {
                "setup_complete": False,
                "start_date": datetime.date.today(),
                "end_date": datetime.date.today() + datetime.timedelta(days=120),
                "mid_exam_dates": [],
                "custom_timetable": {day: [] for day in DAYS_OF_WEEK},
                "cancelled_lectures": [],
                "extra_lectures": []
            }

    if 'absent_records' not in st.session_state:
        st.session_state['absent_records'] = load_absents_db(username)

    cfg = st.session_state['cfg']

    st.sidebar.markdown(f"### 👤 Welcome, {user_display}")
    
    nav_mode = st.sidebar.radio("Navigation Menu:", ["🎓 Daily Attendance", "🚫 Cancel / Extra Lectures", "⚙️ Timetable Setup"])
    
    st.sidebar.write("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['current_user'] = ""
        st.session_state['current_username'] = ""
        if 'cfg' in st.session_state: del st.session_state['cfg']
        if 'absent_records' in st.session_state: del st.session_state['absent_records']
        st.rerun()

    # ---------------------------------------------------------
    # STEP 1: INITIAL SETUP IF NOT COMPLETED
    # ---------------------------------------------------------
    if not cfg["setup_complete"] or nav_mode == "⚙️ Timetable Setup":
        st.markdown("<h1 style='color: white;'>⚙️ Semester & Timetable Setup</h1>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        start_d = c1.date_input("Semester Start Date", value=cfg["start_date"])
        end_d = c2.date_input("Semester End Date", value=cfg["end_date"])

        mid_dates = st.date_input("Select Mid-Exam Date Range", value=(start_d + datetime.timedelta(days=30), start_d + datetime.timedelta(days=36)))

        st.write("---")
        st.subheader("🗓️ Weekly Timetable")
        for day in DAYS_OF_WEEK:
            with st.expander(f"📌 **{day} Sessions**", expanded=True):
                day_list = cfg["custom_timetable"].get(day, [])
                updated_day_list = []
                for idx, slot in enumerate(day_list):
                    col_subj, col_s_time, col_e_time, col_del = st.columns([3, 3, 3, 1])
                    with col_subj:
                        s_name = st.text_input(f"Subject Name", value=slot["subject"], key=f"s_{day}_{idx}")
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
                    if s_name.strip():
                        updated_day_list.append({"subject": s_name.strip(), "start_time": s_time, "end_time": e_time})

                cfg["custom_timetable"][day] = updated_day_list
                if st.button(f"➕ Add Session to {day}", key=f"add_{day}"):
                    cfg["custom_timetable"][day].append({"subject": "New Subject", "start_time": datetime.time(9, 0), "end_time": datetime.time(11, 0)})
                    st.rerun()

        if st.button("🚀 Save Setup & Launch Dashboard", use_container_width=True, type="primary"):
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
            
            save_user_config_db(username, cfg)
            st.success("Setup Saved Permanently!")
            time.sleep(0.5)
            st.rerun()

    # ---------------------------------------------------------
    # NAVIGATION 2: CANCEL / EXTRA LECTURES
    # ---------------------------------------------------------
    elif nav_mode == "🚫 Cancel / Extra Lectures":
        st.markdown("<h1 style='color: white;'>🛠️ Manage Cancelled & Extra Lectures</h1>", unsafe_allow_html=True)
        
        tab_cancel, tab_extra = st.tabs(["🚫 Cancel a Scheduled Lecture", "➕ Add an Extra Lecture"])
        
        all_subjects = sorted(list(set(l["subject"] for day in cfg["custom_timetable"] for l in cfg["custom_timetable"][day])))

        # TAB 1: CANCEL LECTURE
        with tab_cancel:
            st.subheader("Cancel a Lecture for a Specific Date")
            if not all_subjects:
                st.warning("Please setup your timetable first in Timetable Setup!")
            else:
                c_date = st.date_input("Select Cancel Date:", min_value=cfg["start_date"], max_value=cfg["end_date"], key="c_date")
                c_day_name = c_date.strftime("%A")
                
                day_lectures = cfg["custom_timetable"].get(c_day_name, [])
                day_subjects = sorted(list(set(l["subject"] for l in day_lectures)))

                if not day_subjects:
                    st.info(f"No regular lectures scheduled on {c_day_name}s.")
                else:
                    c_subj = st.selectbox("Select Subject to Cancel:", options=day_subjects, key="c_subj")
                    
                    if st.button("🚫 Cancel This Lecture", type="primary"):
                        c_date_str = c_date.strftime("%Y-%m-%d")
                        if not any(c["subject"] == c_subj and c["date"] == c_date_str for c in cfg["cancelled_lectures"]):
                            cfg["cancelled_lectures"].append({"subject": c_subj, "date": c_date_str})
                            save_user_config_db(username, cfg)
                            st.success(f"{c_subj} cancelled on {c_date_str} successfully!")
                            time.sleep(0.5)
                            st.rerun()

            st.write("---")
            st.write("### 📋 Currently Cancelled Lectures")
            if cfg["cancelled_lectures"]:
                for idx, item in enumerate(cfg["cancelled_lectures"]):
                    col_info, col_btn = st.columns([4, 1])
                    col_info.write(f"❌ **{item['subject']}** on `{item['date']}`")
                    if col_btn.button("Restore", key=f"rest_{idx}"):
                        cfg["cancelled_lectures"].pop(idx)
                        save_user_config_db(username, cfg)
                        st.rerun()
            else:
                st.info("No cancelled lectures recorded.")

        # TAB 2: EXTRA LECTURE
        with tab_extra:
            st.subheader("Schedule an Extra Lecture")
            if not all_subjects:
                st.warning("Please setup your timetable first in Timetable Setup!")
            else:
                e_date = st.date_input("Select Extra Lecture Date:", min_value=cfg["start_date"], max_value=cfg["end_date"], key="e_date")
                e_subj = st.selectbox("Select Subject for Extra Class:", options=all_subjects, key="e_subj")
                
                col_st, col_et = st.columns(2)
                with col_st:
                    e_st = mobile_time_picker("Start Time", key_prefix="e_st", default_time=datetime.time(9, 0))
                with col_et:
                    e_et = mobile_time_picker("End Time", key_prefix="e_et", default_time=datetime.time(11, 0))

                if st.button("➕ Schedule Extra Lecture", type="primary"):
                    e_date_str = e_date.strftime("%Y-%m-%d")
                    cfg["extra_lectures"].append({
                        "subject": e_subj,
                        "date": e_date_str,
                        "start_time": e_st,
                        "end_time": e_et
                    })
                    save_user_config_db(username, cfg)
                    st.success(f"Extra lecture for {e_subj} added on {e_date_str}!")
                    time.sleep(0.5)
                    st.rerun()

            st.write("---")
            st.write("### 📋 Scheduled Extra Lectures")
            if cfg["extra_lectures"]:
                for idx, item in enumerate(cfg["extra_lectures"]):
                    col_info, col_btn = st.columns([4, 1])
                    formatted_time = f"{item['start_time'].strftime('%I:%M %p')} - {item['end_time'].strftime('%I:%M %p')}"
                    col_info.write(f"➕ **{item['subject']}** on `{item['date']}` (`{formatted_time}`)")
                    if col_btn.button("Remove", key=f"rm_ext_{idx}"):
                        cfg["extra_lectures"].pop(idx)
                        save_user_config_db(username, cfg)
                        st.rerun()
            else:
                st.info("No extra lectures scheduled.")

    # ---------------------------------------------------------
    # NAVIGATION 1: DAILY ATTENDANCE & SUBJECT PROGRESS
    # ---------------------------------------------------------
    elif nav_mode == "🎓 Daily Attendance":
        st.markdown("<h1 style='color: white;'>🎓 Lecture Attendance Dashboard</h1>", unsafe_allow_html=True)
        
        col_main, col_stats = st.columns([2.2, 1.2])

        # LEFT COLUMN: DAILY TRACKER
        with col_main:
            st.subheader("📅 Daily Attendance Tracker")
            selected_date = st.date_input("Choose Date:", value=datetime.date.today() if cfg["start_date"] <= datetime.date.today() <= cfg["end_date"] else cfg["start_date"], min_value=cfg["start_date"], max_value=cfg["end_date"])
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
                st.info("No lectures scheduled for this date!")
            else:
                for idx, lec in enumerate(active_lectures):
                    subj = lec["subject"]
                    formatted_time = f"{lec['start_time'].strftime('%I:%M %p')} - {lec['end_time'].strftime('%I:%M %p')}"
                    extra_tag = " (Extra Class)" if lec.get("is_extra") else ""
                    
                    record_key = f"{selected_str}_{subj}_{idx}"
                    is_absent = record_key in st.session_state['absent_records']

                    st.markdown('<div class="stat-box">', unsafe_allow_html=True)
                    c_info, c_chk = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"**📖 {subj}**{extra_tag}  \n`⏰ {formatted_time}`")
                    with c_chk:
                        absent_marked = st.checkbox("Mark Absent", value=is_absent, key=f"chk_{record_key}", disabled=is_holiday or is_mid_exam)
                        
                        if absent_marked != is_absent:
                            if absent_marked:
                                st.session_state['absent_records'].add(record_key)
                            else:
                                st.session_state['absent_records'].discard(record_key)
                            save_absents_db(username, st.session_state['absent_records'])
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

        # RIGHT COLUMN: SUBJECT PROGRESS & 80% CALCULATION
        with col_stats:
            st.subheader("📊 80% Attendance Requirement")
            all_subjects = sorted(list(set(l["subject"] for day in cfg["custom_timetable"] for l in cfg["custom_timetable"][day])))

            if not all_subjects:
                st.info("No subjects found. Please setup timetable.")
            else:
                for subj in all_subjects:
                    stats = calculate_subject_stats(subj, cfg, st.session_state['absent_records'])
                    
                    with st.expander(f"📚 **{subj}** ({stats['percentage']:.1f}%)", expanded=True):
                        st.write(f"• **Total Lectures:** {stats['total']}")
                        st.write(f"• **Attended:** {stats['attended']} | **Absences:** {stats['absences']}")
                        
                        st.progress(min(1.0, stats['percentage'] / 100.0))
                        
                        if stats['safe_left'] >= 0:
                            st.success(f"🎯 **Safe to cut:** {stats['safe_left']} more lecture(s) to stay above 80%.")
                        else:
                            st.error(f"⚠️ **Warning:** Attendance below 80%! You must attend upcoming lectures!")


# ---------------------------------------------------------
# 5. AUTHENTICATION SYSTEM (LOGIN / REGISTER)
# ---------------------------------------------------------
def auth_interface():
    st.markdown("<h1 style='text-align: center; color: white;'>🎓 Lecture Attendance App</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Login Mode", use_container_width=True, type="primary" if st.session_state['auth_mode'] == "Login" else "secondary"):
            st.session_state['auth_mode'] = "Login"
            st.rerun()
    with col2:
        if st.button("📝 Register Mode", use_container_width=True, type="primary" if st.session_state['auth_mode'] == "Register" else "secondary"):
            st.session_state['auth_mode'] = "Register"
            st.rerun()

    if st.session_state['auth_mode'] == "Login":
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.subheader("Login to Your Account")
        login_u = st.text_input("Username", key="l_user")
        login_p = st.text_input("Password", type="password", key="l_pass")

        if st.button("🚀 Sign In", use_container_width=True, type="primary"):
            user_display_name = check_login_db(login_u, login_p)
            if user_display_name:
                st.session_state['logged_in'] = True
                st.session_state['current_user'] = user_display_name
                st.session_state['current_username'] = login_u.strip().lower()
                st.toast("Login Successful!", icon="🎉")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid Username or Password.")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        st.subheader("Create a New Account")
        reg_fname = st.text_input("Full Name", placeholder="e.g. Kasun Perera")
        reg_phone = st.text_input("Phone Number", placeholder="e.g. 0771234567")
        reg_u = st.text_input("Username", placeholder="Choose a unique username")
        reg_p = st.text_input("Password", type="password", key="reg_p")
        reg_cp = st.text_input("Confirm Password", type="password", key="reg_cp")

        if st.button("✨ Register Account", use_container_width=True, type="primary"):
            clean_u = reg_u.strip()
            if not reg_fname.strip() or not clean_u or not reg_p:
                st.warning("Please fill in all details!")
            elif reg_p != reg_cp:
                st.error("Passwords do not match!")
            else:
                if register_user_db(clean_u, reg_fname, reg_phone, reg_p):
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = reg_fname.strip()
                    st.session_state['current_username'] = clean_u.lower()
                    st.success("Account Created Successfully! Directing to App...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Username already taken! Try another one.")
        st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# 6. APP ROUTING
# ---------------------------------------------------------
if st.session_state['logged_in']:
    main_app()
else:
    auth_interface()
