import datetime
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Attendance Tracker", page_icon="🎓", layout="centered"
)

# Dynamic Greeting based on current time
hour = datetime.datetime.now().hour
if hour < 12:
    greeting = "Good Morning ☀️"
elif hour < 18:
    greeting = "Good Afternoon 🌤️"
else:
    greeting = "Good Evening 🌙"

# Modern & Professional Custom CSS
st.markdown(
    """
    <style>
    /* Main Background Styling */
    .stApp {
        background-color: #0b0f19;
    }
    
    /* Header Section Styling */
    .header-box {
        text-align: center;
        padding-top: 10px;
        padding-bottom: 20px;
    }
    .header-title {
        color: #ffffff;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .header-greeting {
        color: #818cf8;
        font-size: 1.1rem;
        font-weight: 500;
    }
    .header-subtext {
        color: #94a3b8;
        font-size: 0.9rem;
    }
    
    /* Input & Form Tweaks */
    .stTextInput > div > div > input {
        background-color: #1e293b;
        color: #ffffff;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    
    /* Button Styling */
    .stButton > button {
        width: 100%;
        background-color: #4f46e5;
        color: white;
        border-radius: 10px;
        font-weight: 600;
        padding: 10px;
        border: none;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #4338ca;
        color: white;
    }
    
    /* Hide Streamlit Header Elements for Clean Look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)

# Header UI (No Extra Cards - Directly Focused)
st.markdown(
    f"""
    <div class="header-box">
        <div style="font-size: 3rem;">🎓</div>
        <div class="header-title">Attendance Tracker</div>
        <div class="header-greeting">{greeting}</div>
        <div class="header-subtext">Welcome back! Please enter your details.</div>
    </div>
""",
    unsafe_allow_html=True,
)

# Center Alignment Layout using Columns
col1, main_col, col2 = st.columns([1, 6, 1])

with main_col:
    # Login & Register Tabs
    tab_login, tab_register = st.tabs(["🔒 Sign In", "👤 Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username or Email", placeholder="student@university.ac.lk")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            submit_login = st.form_submit_button("Sign In")
            
            if submit_login:
                if username and password:
                    st.success(f"Welcome back, {username}!")
                else:
                    st.error("Please enter both username and password.")

    with tab_register:
        with st.form("register_form"):
            full_name = st.text_input("Full Name", placeholder="John Doe")
            reg_email = st.text_input("Email Address", placeholder="student@university.ac.lk")
            reg_password = st.text_input("Create Password", type="password", placeholder="••••••••")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
            
            submit_register = st.form_submit_button("Create Account")
            
            if submit_register:
                if not full_name or not reg_email or not reg_password:
                    st.error("Please fill in all required fields.")
                elif reg_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    st.success("Account created successfully! You can now log in.")
