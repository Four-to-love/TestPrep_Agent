import streamlit as st
import hashlib
import sqlite3
import uuid
from datetime import date

# IMPORT THE NEW SHIELD
import interceptor

# 1. Page Configuration
st.set_page_config(page_title="TestPrep_Agent", layout="wide")

# 2. Database & Math Helpers
def get_db_connection():
    return sqlite3.connect('student_state.db')

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def calculate_selection_index(rw_score, math_score):
    """Computes the official NMSC Selection Index formula."""
    if not rw_score or not math_score:
        return 0
    return int(((2 * rw_score) + math_score) / 10)

# 3. Initialize Session State
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'student_id' not in st.session_state:
    st.session_state['student_id'] = None
if 'session_token' not in st.session_state:
    st.session_state['session_token'] = None

# 4. Sidebar: Authentication & Secure Data Entry
with st.sidebar:
    if not st.session_state['authenticated']:
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
                        st.rerun()
                    else:
                        st.error("Invalid Student ID or PIN.")
                else:
                    st.error("Please enter both Student ID and PIN.")
                    
    else:
        # User is logged in: Show Secure Forms and Logout
        st.success(f"Session Locked: {st.session_state['session_token'][:8]}...")
        
        st.divider()
        st.header("⚙️ Secure Data Entry")
        
        with st.expander("Update Profile (State Code)", expanded=False):
            with st.form("intake_form"):
                # Expanded list for the dashboard
                state_code = st.selectbox(
                    "Registered State", 
                    ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", 
                     "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", 
                     "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", 
                     "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", 
                     "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
                )
                if st.form_submit_button("Save Profile"):
                    response = interceptor.process_secure_request(
                        action_type="SAVE_PROFILE",
                        student_id=st.session_state['student_id'],
                        session_token=st.session_state['session_token'],
                        active_token=st.session_state['session_token'],
                        payload={"state_code": state_code}
                    )
                    if response["status"] == "success":
                        st.success("Profile Updated.")
                    else:
                        st.error(response["message"])

        with st.expander("Log Practice Scores", expanded=False):
            with st.form("score_logger_form"):
                test_date = st.date_input("Test Date", date.today())
                rw_score = st.number_input("Reading/Writing (200-760)", value=680, step=10)
                math_score = st.number_input("Math (200-760)", value=640, step=10)
                
                if st.form_submit_button("Submit Scores"):
                    response = interceptor.process_secure_request(
                        action_type="LOG_SCORES",
                        student_id=st.session_state['student_id'],
                        session_token=st.session_state['session_token'],
                        active_token=st.session_state['session_token'],
                        payload={"test_date": str(test_date), "math_score": math_score, "reading_writing_score": rw_score}
                    )
                    if response["status"] == "success":
                        st.success("Scores Logged securely.")
                    else:
                        st.error(response["message"])
        
        st.divider()
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.session_state['student_id'] = None
            st.session_state['session_token'] = None
            st.rerun()

# 5. Main Dashboard
if st.session_state['authenticated']:
    st.title("🎓 PSAT/SAT Strategic Timeline")
    st.caption(f"Active Secure Session: `{st.session_state['student_id']}` | Target Admissions Cycle: 2028")
    
    # Mock data retrieval for current scores (Normally pulled via get_student_scores tool)
    latest_rw = 680
    latest_math = 640
    current_index = calculate_selection_index(latest_rw, latest_math)
    target_cutoff = 222 # Hardcoded WA state target for demonstration
    
    # ROW 1: Top Array Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Latest PSAT Total", value=f"{latest_rw + latest_math}/1520")
    with col2:
        delta_val = current_index - target_cutoff
        st.metric(
            label="Current NMSI", 
            value=str(current_index), 
            delta=f"{delta_val} vs Target" if delta_val >= 0 else f"{delta_val} points off Target"
        )
    with col3:
        st.metric(label="State Target Cutoff (WA)", value=str(target_cutoff))

    st.divider()

    # ROW 2: Interactive NMSI Simulator
    st.subheader("🧮 National Merit Trajectory Simulator")
    st.write("Because the ERW section is multiplied by 2, it drives ~66% of the final index. Adjust the sliders to map out the required section scores to hit the 222 threshold.")
    
    sim_col1, sim_col2 = st.columns([2, 1])
    with sim_col1:
        sim_rw = st.slider("Simulated Reading & Writing Score", min_value=160, max_value=760, value=700, step=10)
        sim_math = st.slider("Simulated Math Score", min_value=160, max_value=760, value=700, step=10)
    
    with sim_col2:
        sim_index = calculate_selection_index(sim_rw, sim_math)
        st.metric(label="Simulated Selection Index", value=sim_index, delta=sim_index - target_cutoff)
        if sim_index >= target_cutoff:
            st.success("🎉 Trajectory meets National Merit requirements!")
        else:
            st.warning("Trajectory falls below cutoff.")

    st.divider()
    
    # ROW 3: Placeholder for Chat / Gantt
    st.subheader("🤖 Strategist Agent Console")
    st.info("The multi-agent execution loop and Gantt chart visualization will be integrated here.")

else:
    st.warning("Awaiting Zero-Trust Authentication. Please log in using the sidebar to access the dashboard.")