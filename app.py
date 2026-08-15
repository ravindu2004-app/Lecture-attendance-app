import streamlit as st
import sqlite3
import json
import datetime
import math

# --- DATABASE SETUP ---
def get_db_conn():
    conn = sqlite3.connect('attendance_data.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_configs (username TEXT, term_key TEXT, config_json TEXT, PRIMARY KEY(username, term_key))')
    c.execute('CREATE TABLE IF NOT EXISTS absent_records (username TEXT, term_key TEXT, record_key TEXT)')
    conn.commit()
    conn.close()

init_db()

# --- DATA HELPERS ---
def save_config(username, term_key, config_dict):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO user_configs VALUES (?, ?, ?)', (username, term_key, json.dumps(config_dict)))
    conn.commit()
    conn.close()

def load_config(username, term_key):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('SELECT config_json FROM user_configs WHERE username=? AND term_key=?', (username, term_key))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else None

# --- UI LOGIC ---
st.set_page_config(page_title="Academic Tracker", layout="wide")

if 'username' not in st.session_state: st.session_state.username = "user1" # Demo user

# Sidebar for Term Selection
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Timetable Setup"])

year = st.sidebar.selectbox("Select Year", ["Year 1", "Year 2", "Year 3", "Year 4"])
sem = st.sidebar.selectbox("Select Semester", ["Semester 1", "Semester 2"])
term_key = f"{year}_{sem}"

# --- SETUP PAGE ---
if page == "Timetable Setup":
    st.title(f"Setup Timetable for {term_key}")
    cfg = load_config(st.session_state.username, term_key) or {"subjects": [], "timetable": {}}
    
    new_sub = st.text_input("Add Subject")
    if st.button("Add"):
        if new_sub and new_sub not in cfg["subjects"]:
            cfg["subjects"].append(new_sub)
            save_config(st.session_state.username, term_key, cfg)
            st.rerun()
    
    st.write("Current Subjects:", cfg["subjects"])
    # මෙතන ටයිම් ටේබල් සෙටප් එක හදාගන්න (සරලව)
    if st.button("Save Timetable"):
        save_config(st.session_state.username, term_key, cfg)
        st.success("Saved!")

# --- DASHBOARD PAGE ---
else:
    st.title(f"Dashboard - {term_key}")
    cfg = load_config(st.session_state.username, term_key)
    
    if not cfg or not cfg["subjects"]:
        st.warning(f"There are no subjects for {term_key}. Please go to 'Timetable Setup' to add them.")
    else:
        st.success(f"Tracking {len(cfg['subjects'])} subjects.")
        
        # Attendance tracking UI here...
        # ඔයාගේ කලින් තිබ්බ ලොජික් එක මෙතන දාන්න
        # මේක දැන් ඉබේම අදාල semester එකට විතරයි වැඩ කරන්නේ
