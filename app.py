import streamlit as st
import hashlib
import sqlite3
import uuid
from datetime import date

import interceptor
from agents import StrategistAgent
from constants import STATES_LIST, STATE_CUTOFFS

st.set_page_config(page_title="TestPrep_Agent", layout="wide")

# --- DATABASE INITIALIZATION & HELPERS ---
def get_db_connection():
    """Builds only the dynamic user tables, ignoring static reference data."""
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            pin_hash TEXT,
            state_code TEXT,
            graduation_year INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT,
            test_date TEXT,
            sat_total_score INTEGER,
            math_score INTEGER,
            reading_writing_score INTEGER
        )
    ''')
    conn.commit()
    return conn

def hash_pin(pin):
    return hashlib.sha256(pin.encode()).hexdigest()

def calculate_selection_index(rw_score, math_score):
    if not rw_score or not math_score:
        return 0
    return int(((2 * rw_score) + math_score) / 10)

def get_state_target(state_code):
    """Dictionary lookup for NMSI cutoffs using constants.py."""
    return STATE_CUTOFFS.get(state_code, 220)

# --- SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'student_id' not in st.session_state:
    st.session_state['student_id'] = None
if 'session_token' not in st.session_state:
    st.session_state['session_token'] = None
if 'action_plan' not in st.session_state:
    st.session_state['action_plan'] = None

# --- THE SLIDE-OUT SIDEBAR (AUTH & SECURE DATA ENTRY ONLY) ---
with st.sidebar:
    if not st.session_state['authenticated']:
        st.header("🔒 Access Control")
        auth_mode = st.radio("Select Action", ["Login", "Register New Student"])
        
        if auth_mode == "Register New Student":
            st.subheader("Create Account")
            new_id = st.text_input("New Student ID")
            new_pin = st.text_input("Create 4-Digit PIN", type="password")
            grad_year = st.number_input("Target Graduation Year", min_value=2026, max_value=2032, value=2028)
            
            if st.button("Register"):
                if new_id and new_pin:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM students WHERE student_id = ?", (new_id,))
                    if c.fetchone():
                        st.error("Student ID already exists.")
                    else:
                        c.execute("INSERT INTO students (student_id, pin_hash, state_code, graduation_year) VALUES (?, ?, ?, ?)", 
                                  (new_id, hash_pin(new_pin), "", grad_year))
                        conn.commit()
                        st.success("Account created! You can now login.")
                    conn.close()
                else:
                    st.error("Please fill out all fields.")

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
                        st.session_state['student_id'] = user[0] 
                        st.session_state['state_code'] = user[2] 
                        st.session_state['class_year'] = user[3] 
                        st.session_state['session_token'] = str(uuid.uuid4())
                        st.rerun()
                    else:
                        st.error("Invalid Student ID or PIN.")
                else:
                    st.error("Please enter both Student ID and PIN.")
                    
    else:
        st.success(f"Session Locked: {st.session_state['session_token'][:8]}...")
        st.divider()
        
        with st.expander("⚙️ Secure Data Entry", expanded=False):
            with st.form("intake_form"):
                current_state = st.session_state.get('state_code')
                default_index = STATES_LIST.index(current_state) if current_state in STATES_LIST else None
                
                state_code = st.selectbox("Registered State", STATES_LIST, index=default_index, placeholder="Select a State...")
                new_grad_year = st.number_input("Update Graduation Year", min_value=2026, max_value=2032, value=st.session_state.get('class_year', 2028))
                
                if st.form_submit_button("Save Profile"):
                    response = interceptor.process_secure_request(
                        action_type="SAVE_PROFILE",
                        student_id=st.session_state['student_id'],
                        session_token=st.session_state['session_token'],
                        active_token=st.session_state['session_token'],
                        payload={"state_code": state_code, "graduation_year": new_grad_year}
                    )
                    if response["status"] == "success":
                        st.success("Profile Updated.")
                        st.session_state['state_code'] = state_code
                        st.session_state['class_year'] = new_grad_year
                    else:
                        st.error(response["message"])

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
        
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.session_state['authenticated'] = False
            st.rerun()

# --- MAIN DASHBOARD VISUALS ---
if st.session_state['authenticated']:
    st.title("🎓 PSAT/SAT Strategic Timeline")
    st.caption(f"Active Secure Session: `{st.session_state['student_id']}` | Class of {st.session_state.get('class_year', 'Unknown')}")
    
    latest_rw = 680
    latest_math = 640
    current_index = calculate_selection_index(latest_rw, latest_math)
    
    user_state = st.session_state.get('state_code')
    
    # ROW 1: Top Array Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Latest PSAT Total", value=f"{latest_rw + latest_math}/1520")
        
    if user_state in STATES_LIST:
        target_cutoff = get_state_target(user_state)
        with col2:
            delta_val = current_index - target_cutoff
            st.metric(label="Current NMSI", value=str(current_index), delta=f"{delta_val} vs Target" if delta_val >= 0 else f"{delta_val} pts off Target")
        with col3:
            st.metric(label=f"State Target ({user_state})", value=str(target_cutoff))
    else:
        target_cutoff = 220 
        with col2:
            st.metric(label="Current NMSI", value=str(current_index))
        with col3:
            st.metric(label="State Target", value="Pending", delta="Update profile in sidebar", delta_color="off")

    st.divider()

    st.subheader("🧮 National Merit Trajectory Simulator")
    st.write("Because the ERW section is multiplied by 2, it drives ~66% of the final index. Adjust the sliders to map out the required section scores to hit the benchmark.")
    
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

    # --- HEADLESS AGENT SCHEDULE DASHBOARD ---
    st.header("🧠 Autonomous Action Plan")
    if st.button("Generate Strategic Timeline", type="primary"):
        with st.spinner("Agent is mapping the Khan Academy curriculum to your remaining timeline..."):
            agent = StrategistAgent(
                student_id=st.session_state['student_id'], 
                state_code=st.session_state.get('state_code', 'Unknown'),
                class_year=st.session_state.get('class_year', 2028)
            )
            st.session_state['action_plan'] = agent.generate_action_plan()

    # Render the Action Plan JSON if generated
    if st.session_state['action_plan']:
        plan = st.session_state['action_plan']
        
        if "error" in plan:
            st.error(plan["error"])
        else:
            st.success("Curriculum Mapping Complete.")
            st.write(f"**Strategic Insight:** {plan.get('analysis_summary', '')}")
            
            weeks = plan.get('total_weeks', 'Calculated')
            st.subheader(f"🗓️ Comprehensive Pacing Guide ({weeks} Weeks)")
            
            # Draw a dual-column UI grid for the schedule
            for item in plan.get('schedule', []):
                with st.container():
                    col_week, col_math, col_rw = st.columns([1, 2, 2])
                    
                    with col_week: 
                        st.markdown(f"### {item.get('week')}")
                        
                    with col_math: 
                        st.markdown(f"**🧮 Math:** {item.get('math_topic')}")
                        st.caption(f"[Khan Academy Practice]({item.get('math_link')})")
                        
                    with col_rw: 
                        st.markdown(f"**📚 Reading/Writing:** {item.get('rw_topic')}")
                        st.caption(f"[Khan Academy Practice]({item.get('rw_link')})")
                        
                    st.divider()

else:
    st.warning("Awaiting Zero-Trust Authentication. Please log in using the sidebar to access the dashboard.")