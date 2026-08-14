import sqlite3
import datetime
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(page_title="Lecture Attendance App", page_icon="📚", layout="wide")

# DB Setup
def get_db_connection():
    conn = sqlite3.connect("attendance_app.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subject_name TEXT NOT NULL,
            target_percentage REAL NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS lectures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# Authentication Functions
def register_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# Data Helper Functions
def add_subject(username, subject_name, target):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO subjects (username, subject_name, target_percentage) VALUES (?, ?, ?)",
              (username, subject_name, target))
    conn.commit()
    conn.close()

def get_subjects(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM subjects WHERE username = ?", (username,))
    subs = c.fetchall()
    conn.close()
    return subs

def add_lecture(subject_id, date, start_time, end_time, status):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO lectures (subject_id, date, start_time, end_time, status) VALUES (?, ?, ?, ?, ?)",
              (subject_id, str(date), str(start_time), str(end_time), status))
    conn.commit()
    conn.close()

def get_lectures(subject_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM lectures WHERE subject_id = ? ORDER BY date DESC", (subject_id,))
    lecs = c.fetchall()
    conn.close()
    return lecs

def delete_lecture(lecture_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lectures WHERE id = ?", (lecture_id,))
    conn.commit()
    conn.close()

def delete_subject(subject_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM lectures WHERE subject_id = ?", (subject_id,))
    c.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))
    conn.commit()
    conn.close()

# MAIN APP UI
st.title("📚 Lecture Attendance Tracker")

if not st.session_state.authenticated:
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to your account")
        l_user = st.text_input("Username", key="l_user")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            if login_user(l_user, l_pass):
                st.session_state.authenticated = True
                st.session_state.username = l_user
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
                
    with tab2:
        st.subheader("Create a new account")
        r_user = st.text_input("Username", key="r_user")
        r_pass = st.text_input("Password", type="password", key="r_pass")
        if st.button("Register"):
            if r_user and r_pass:
                if register_user(r_user, r_pass):
                    st.success("Account created! Please login.")
                else:
                    st.error("Username already exists.")
            else:
                st.warning("Please fill out all fields.")

else:
    # Sidebar
    st.sidebar.write(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()

    st.sidebar.header("Subjects Manager")
    
    # Add Subject
    with st.sidebar.expander("➕ Add New Subject"):
        new_sub = st.text_input("Subject Name")
        target_pct = st.number_input("Target Attendance %", min_value=1.0, max_value=100.0, value=80.0, step=1.0)
        if st.button("Add Subject"):
            if new_sub:
                add_subject(st.session_state.username, new_sub, target_pct)
                st.success("Subject Added!")
                st.rerun()

    # Get Subjects
    subjects = get_subjects(st.session_state.username)
    
    if not subjects:
        st.info("No subjects added yet. Add a subject from the sidebar to get started.")
    else:
        sub_dict = {s["subject_name"]: s["id"] for s in subjects}
        selected_sub_name = st.selectbox("Select Subject", list(sub_dict.keys()))
        selected_sub_id = sub_dict[selected_sub_name]
        
        # Get selected subject data
        selected_sub = next(s for s in subjects if s["id"] == selected_sub_id)
        target = selected_sub["target_percentage"]

        # Delete Subject Option
        with st.sidebar.expander("🗑️ Delete Subject"):
            st.warning(f"Delete {selected_sub_name}?")
            if st.button("Confirm Delete Subject"):
                delete_subject(selected_sub_id)
                st.success("Subject Deleted")
                st.rerun()

        # Tabs for Navigation
        tab_dash, tab_add, tab_history = st.tabs(["📊 Dashboard", "➕ Mark Attendance", "📜 Attendance History"])

        lectures = get_lectures(selected_sub_id)
        total_lectures = len(lectures)
        attended_lectures = len([l for l in lectures if l["status"] == "Attended"])
        absent_lectures = total_lectures - attended_lectures
        
        curr_pct = (attended_lectures / total_lectures * 100) if total_lectures > 0 else 0.0

        with tab_dash:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Lectures", total_lectures)
            col2.metric("Attended", attended_lectures)
            col3.metric("Absent", absent_lectures)
            col4.metric("Current Attendance", f"{curr_pct:.1f}%")

            st.write("---")
            if total_lectures > 0:
                if curr_pct >= target:
                    st.success(f"🎉 Great job! Your attendance ({curr_pct:.1f}%) is at or above target ({target}%).")
                else:
                    st.warning(f"⚠️ Your attendance ({curr_pct:.1f}%) is below your target ({target}%).")

                # Analytics & Predictions
                st.subheader("📊 Analytics & Predictions")
                
                if curr_pct < target:
                    needed = 0
                    while True:
                        if ((attended_lectures + needed) / (total_lectures + needed)) * 100 >= target:
                            break
                        needed += 1
                    st.info(f"👉 You need to attend the next **{needed}** consecutive lectures to hit your {target}% target.")
                else:
                    can_miss = 0
                    temp_total = total_lectures
                    while True:
                        temp_total += 1
                        if (attended_lectures / temp_total) * 100 < target:
                            break
                        can_miss += 1
                    st.info(f"👉 You can afford to miss **{can_miss}** upcoming lectures while staying above {target}%.")

        with tab_add:
            st.subheader("Mark Attendance for a Class")
            with st.form("mark_attendance_form"):
                d = st.date_input("Date", datetime.date.today())
                
                # step=60 added to fix mobile freeze issue
                t_start = st.time_input("Start Time", datetime.time(8, 0), step=60)
                t_end = st.time_input("End Time", datetime.time(10, 0), step=60)
                
                status = st.radio("Status", ["Attended", "Absent"])
                
                submitted = st.form_submit_button("Save Attendance")
                if submitted:
                    add_lecture(selected_sub_id, d, t_start, t_end, status)
                    st.success("Attendance Recorded!")
                    st.rerun()

        with tab_history:
            st.subheader("Attendance Log")
            if lectures:
                df = pd.DataFrame([dict(l) for l in lectures])
                st.dataframe(df[["date", "start_time", "end_time", "status"]], use_container_width=True)
                
                st.write("---")
                st.subheader("Manage Records")
                lec_to_del = st.selectbox("Select Lecture ID to delete", [l["id"] for l in lectures])
                if st.button("Delete Record"):
                    delete_lecture(lec_to_del)
                    st.success("Record Deleted")
                    st.rerun()
            else:
                st.info("No attendance records found.")
