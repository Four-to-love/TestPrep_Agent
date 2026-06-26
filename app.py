import streamlit as st
import hashlib
import sqlite3
import uuid
from datetime import date

# IMPORT THE NEW SHIELD
import interceptor

# 1. Page Configuration
st.set_page_config(page_title="TestPrep_Agent", layout="wide")

# 2. Database Connection Helper (Only used for login/registration now)
def get_db_connection():
    return sqlite3.connect('student_state.db')

# 3. Security Protocol: Hashing the PIN
def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'student_id' not in st.session_state:
    st.session_state['student_id'] = None
if 'session_token' not in st.session_state:
    st.session_state['session_token'] = None

# 4. Sidebar: Registration & Login
with st.sidebar:
    st.header("🔒 Access Control")
    auth_mode = st.radio("Select Action", ["Login", "Register New Student"])
    
    if auth_mode == "Register New Student":
        st.subheader("Create Account")
        new_id = st.text_input("New Student ID")
        new_pin = st.text_input("Create 4-Digit PIN", type="password")
        
        if st.button("Register"):
            if new_id and new_pin:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM students WHERE student_id = ?", (new_id,))
                if c.fetchone():
                    st.error("Student ID already exists.")
                else:
                    c.execute("INSERT INTO students (student_id, pin_hash, state_code) VALUES (?, ?, ?)", 
                              (new_id, hash_pin(new_pin), ""))
                    conn.commit()
                    st.success("Account created! You can now login.")
                conn.close()
            else:
                st.error("Please fill out both fields.")

    elif auth_mode == "Login":
        st.subheader("Secure Login")
        student_id = st.text_input("Student ID")
        pin = st.text_input("4-Digit PIN", type="password")
        
        if st.button("Login"):
            if student_id and pin:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM students WHERE student_id = ? AND pin_hash = ?", 
                          (student_id, hash_pin(pin)))
                user = c.fetchone()
                conn.close()
                
                if user:
                    st.session_state['authenticated'] = True
                    st.session_state['student_id'] = student_id
                    st.session_state['session_token'] = str(uuid.uuid4())
                    st.success(f"Session Locked. Token: {st.session_state['session_token'][:8]}...")
                else:
                    st.error("Invalid Student ID or PIN.")
            else:
                st.error("Please enter both Student ID and PIN.")
                
    if st.session_state['authenticated']:
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state['student_id'] = None
            st.session_state['session_token'] = None
            st.rerun()

# 5. Main Dashboard: Interceptor-Routed Ingestion
if st.session_state['authenticated']:
    st.title("🎓 TestPrep_Agent Dashboard")
    st.write(f"Active Session: `{st.session_state['student_id']}`")
    
    tab1, tab2 = st.tabs(["📋 Student Profile", "📊 Log Practice Scores"])
    
    with tab1:
        with st.form("intake_form"):
            st.subheader("Context Initialization")
            state_code = st.selectbox(
                "Registered State", 
                ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
                 "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                 "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                 "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                 "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
            ) 
            
            submit_profile = st.form_submit_button("Save Profile")
            if submit_profile:
                # ROUTE THROUGH INTERCEPTOR
                payload = {"state_code": state_code}
                response = interceptor.process_secure_request(
                    action_type="SAVE_PROFILE",
                    student_id=st.session_state['student_id'],
                    session_token=st.session_state['session_token'],
                    active_token=st.session_state['session_token'],
                    payload=payload
                )
                
                if response["status"] == "success":
                    st.success(response["message"])
                else:
                    st.error(response["message"])
                
    with tab2:
        with st.form("score_logger_form"):
            st.subheader("Record Practice Test Results")
            test_date = st.date_input("Test Date", date.today())
            
            # We removed the front-end boundaries so we can test the Interceptor!
            math_score = st.number_input("Math Section Score (200 - 800)", value=500, step=10)
            rw_score = st.number_input("Reading and Writing Section Score (200 - 800)", value=500, step=10)
            
            submit_scores = st.form_submit_button("Submit Scores")
            
            if submit_scores:
                # ROUTE THROUGH INTERCEPTOR
                payload = {
                    "test_date": str(test_date),
                    "math_score": math_score,
                    "reading_writing_score": rw_score
                }
                
                response = interceptor.process_secure_request(
                    action_type="LOG_SCORES",
                    student_id=st.session_state['student_id'],
                    session_token=st.session_state['session_token'],
                    active_token=st.session_state['session_token'],
                    payload=payload
                )
                
                if response["status"] == "success":
                    st.success(response["message"])
                else:
                    st.error(response["message"])
else:
    st.warning("Awaiting Zero-Trust Authentication. Please log in using the sidebar.")