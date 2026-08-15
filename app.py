import streamlit as st
import pandas as pd
import datetime
import time
import math
import sqlite3
import json

# ---------------------------------------------------------
# DATABASE CONNECTION (සම්පූර්ණම database එක එක තැනකට ගත්තා)
# ---------------------------------------------------------
def get_db_conn():
    # මෙතන පරණ database එකේ නම පාවිච්චි කරන්න
    return sqlite3.connect('attendance_app.db', check_same_thread=False)

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, name TEXT, phone TEXT, password TEXT)''')
    # මෙතන table එකේ term_key එක අනිවාර්යයි
    c.execute('''CREATE TABLE IF NOT EXISTS user_configs (username TEXT, term_key TEXT, config_json TEXT, PRIMARY KEY (username, term_key))''')
    c.execute('''CREATE TABLE IF NOT EXISTS absent_records (username TEXT, term_key TEXT, record_key TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# DATABASE LOGIC (TERM_KEY එක අනුව වෙන් වෙන විදිහට)
# ---------------------------------------------------------
def save_user_config_db(username, term_key, cfg):
    conn = get_db_conn()
    c = conn.cursor()
    # clean_u එක session එකේ username එකෙන් ගන්න
    c.execute("INSERT OR REPLACE INTO user_configs VALUES (?, ?, ?)", (username, term_key, json.dumps(cfg)))
    conn.commit()
    conn.close()

def load_user_config_db(username, term_key):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT config_json FROM user_configs WHERE username=? AND term_key=?", (username, term_key))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

# --- ඔයාගේ අනිත් පරණ Functions ඔක්කොම මෙතනට දාගන්න ---
# (register_user_db, check_login_db, load_absents_db, save_absents_db)
# මේවායේ අනිවාර්යයෙන් 'term_key' එක පරාමිතියක් විදිහට pass කරන්න.

# ---------------------------------------------------------
# MAIN APP (ඔයාගේ Navigation පැනල් එකයි, UI එකයි තියෙන තැන)
# ---------------------------------------------------------
def main_app():
    # Sidebar එකේ Year / Semester සිලෙක්ට් කරන්න
    with st.sidebar:
        st.write("### ⚙️ Semester Selection")
        sel_y = st.selectbox("Select Year", ["Year 1", "Year 2", "Year 3", "Year 4"])
        sel_s = st.selectbox("Select Semester", ["Semester 1", "Semester 2"])
        term_key = f"{sel_y}_{sel_s}".replace(" ", "_")
        
        # දැනට logged in user ගේ username එක
        username = st.session_state['current_username']
        
        # Navigation menus... (ඔයාගේ කලින් තිබ්බම)
        if st.button("⚙️ Timetable Setup"):
            st.session_state['nav_mode'] = "⚙️ Timetable Setup"
        # ... අනෙක් මෙනු ඔක්කොම මෙතන තියෙන්න ඕනේ

    # 1. දැන් Timetable Setup එකේදී මේ term_key එක පාවිච්චි කරන්න
    if st.session_state['nav_mode'] == "⚙️ Timetable Setup":
        # මේ term_key එකට අදාල cfg එක ලෝඩ් කරගන්න
        cfg = load_user_config_db(username, term_key) or { "subjects": [], "timetable": {} }
        
        # සබ්ජෙක්ට්ස් ඇඩ් කරන්න - දැන් මේවා සේව් වෙන්නේ අර ටර්ම් එකට
        st.subheader("Add Subjects")
        # ... (Subject adding logic)
        
        # සේව් බටන් එකේදී
        if st.button("Apply Changes"):
            save_user_config_db(username, term_key, cfg)
            st.success(f"Saved for {term_key}")

    # 2. Dashboard එකේදී
    elif st.session_state['nav_mode'] == "📊 Overall Overview":
        cfg = load_user_config_db(username, term_key)
        if not cfg:
            st.warning("No data found for this semester. Please configure in Timetable Setup.")
        else:
            # ඩෑෂ්බෝඩ් එකේ පර්ෆෝමන්ස් ලොජික් එක මෙතන දාන්න
            st.write(f"Showing performance for {term_key}")

# ---------------------------------------------------------
# APP ENTRY
# ---------------------------------------------------------
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # Login / Register UI (ඔයාගේ පරණ එක)
    pass
else:
    main_app()
