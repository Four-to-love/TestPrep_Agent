import streamlit as st
import hashlib
import os
from google import genai
import sqlite3
import uuid
from datetime import date
import pandas as pd
import interceptor
from agents import StrategistAgent, SyllabusTutorAgent
from constants import STATES_LIST, STATE_CUTOFFS

st.set_page_config(page_title="TestPrep_Agent", layout="wide")

# --- DATABASE INITIALIZATION & HELPERS ---
def get_db_connection():
    """Builds the dynamic user tables."""
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
    # NEW TABLE: To store syllabus checkmarks persistently
    c.execute('''
        CREATE TABLE IF NOT EXISTS syllabus_progress (
            student_id TEXT,
            topic TEXT,
            is_completed INTEGER,
            PRIMARY KEY (student_id, topic)
        )
    ''')
    conn.commit()
    return conn


@st.cache_resource
def load_sat_framework():
    """Uploads the massive PDF to Gemini once and caches the file object."""
    client = genai.Client()
    
    # Dynamically build the absolute path to where app.py lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(base_dir, "knowledge_base", "sat_framework.pdf")
    
    # Check if the file actually exists before trying to upload
    if not os.path.exists(pdf_path):
        st.error(f"File not found! I am looking exactly here: {pdf_path}")
        return None
        
    try:
        # Upload the file to Google's servers securely
        uploaded_file = client.files.upload(file=pdf_path)
        return uploaded_file
    except Exception as e:
        st.error(f"Failed to load PDF Framework: {e}")
        return None

def hash_pin(pin): return hashlib.sha256(pin.encode()).hexdigest()
def calculate_selection_index(rw_score, math_score): return int(((2 * rw_score) + math_score) / 10) if rw_score and math_score else 0
def get_state_target(state_code): return STATE_CUTOFFS.get(state_code, 220)

# --- SESSION STATE ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'student_id' not in st.session_state: st.session_state['student_id'] = None
if 'session_token' not in st.session_state: st.session_state['session_token'] = None
if 'action_plan' not in st.session_state: st.session_state['action_plan'] = None

# --- THE SLIDE-OUT SIDEBAR ---
with st.sidebar:
    if not st.session_state['authenticated']:
        st.header("🔒 Access Control")
        auth_mode = st.radio("Select Action", ["Login", "Register New Student"])
        
        if auth_mode == "Register New Student":
            new_id = st.text_input("New Student ID")
            new_pin = st.text_input("Create 4-Digit PIN", type="password")
            grad_year = st.number_input("Target Graduation Year", 2026, 2032, 2028)
            if st.button("Register") and new_id and new_pin:
                conn = get_db_connection(); c = conn.cursor()
                c.execute("SELECT * FROM students WHERE student_id = ?", (new_id,))
                if c.fetchone(): st.error("ID exists.")
                else:
                    c.execute("INSERT INTO students VALUES (?, ?, ?, ?)", (new_id, hash_pin(new_pin), "", grad_year))
                    conn.commit(); st.success("Account created!")
                conn.close()
        elif auth_mode == "Login":
            student_id = st.text_input("Student ID"); pin = st.text_input("PIN", type="password")
            if st.button("Login") and student_id and pin:
                conn = get_db_connection(); c = conn.cursor()
                c.execute("SELECT * FROM students WHERE student_id = ? AND pin_hash = ?", (student_id, hash_pin(pin)))
                user = c.fetchone(); conn.close()
                if user:
                    st.session_state.update({'authenticated': True, 'student_id': user[0], 'state_code': user[2], 'class_year': user[3], 'session_token': str(uuid.uuid4())})
                    st.rerun()
                else: st.error("Invalid credentials.")
    else:
        st.success(f"Session Locked: {st.session_state['session_token'][:8]}...")
        st.divider()
        with st.expander("⚙️ Secure Data Entry", expanded=False):
            with st.form("intake_form"):
                current_state = st.session_state.get('state_code')
                default_index = STATES_LIST.index(current_state) if current_state in STATES_LIST else 0
                state_code = st.selectbox("State", STATES_LIST, index=default_index)
                new_grad_year = st.number_input("Graduation Year", 2026, 2032, st.session_state.get('class_year', 2028))
                if st.form_submit_button("Save Profile"):
                    if interceptor.process_secure_request("SAVE_PROFILE", st.session_state['student_id'], st.session_state['session_token'], st.session_state['session_token'], {"state_code": state_code, "graduation_year": new_grad_year})["status"] == "success":
                        st.session_state.update({'state_code': state_code, 'class_year': new_grad_year}); st.success("Updated")
            with st.form("score_logger_form"):
                test_date = st.date_input("Test Date", date.today()); rw = st.number_input("R/W", 160, 800, 680, 10); math = st.number_input("Math", 160, 800, 640, 10)
                if st.form_submit_button("Log Scores"):
                    interceptor.process_secure_request("LOG_SCORES", st.session_state['student_id'], st.session_state['session_token'], st.session_state['session_token'], {"test_date": str(test_date), "math_score": math, "reading_writing_score": rw})
                    st.success("Logged")
        
        st.divider()
        if st.button("Logout", use_container_width=True): st.session_state.clear(); st.rerun()

# --- MAIN DASHBOARD VISUALS ---
if st.session_state['authenticated']:
    st.title("🎓 PSAT/SAT Strategic Timeline")
    st.caption(f"Student: `{st.session_state['student_id']}` | Class of {st.session_state.get('class_year', 'Unknown')}")
    
    # 1. Fetch REAL practice scores from the database
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT test_date, sat_total_score, math_score, reading_writing_score FROM practice_scores WHERE student_id = ? ORDER BY test_date DESC", (st.session_state['student_id'],))
    all_scores = c.fetchall()
    conn.close()

    # Extract latest scores for the top array
    if all_scores:
        latest_date = all_scores[0][0]
        latest_total = all_scores[0][1]
        latest_math = all_scores[0][2]
        latest_rw = all_scores[0][3]
    else:
        latest_total, latest_math, latest_rw = 0, 0, 0

    current_index = calculate_selection_index(latest_rw, latest_math)
    user_state = st.session_state.get('state_code')
    
    # 2. ROW 1: Top Array Metrics
    col1, col2, col3 = st.columns(3)
    with col1: 
        if all_scores:
            st.metric("Latest Total Score", f"{latest_total}/1600", f"Tested: {latest_date}")
        else:
            st.metric("Latest Total Score", "N/A", "Log scores in sidebar")
            
    if user_state in STATES_LIST:
        target = get_state_target(user_state)
        delta = current_index - target
        with col2: st.metric("Current NMSI", current_index, f"{delta} pts" if delta >= 0 else f"{delta} pts off")
        with col3: st.metric(f"State Target ({user_state})", target)
    else:
        target = 220 
        with col2: st.metric("Current NMSI", current_index)
        with col3: st.metric("State Target", "Pending", "Update profile", "off")

    st.divider()

    # 3. ROW 2: Simulator & Score History Card
    sim_col, history_col = st.columns([3, 2])
    
    with sim_col:
        st.subheader("🧮 NMSI Trajectory Simulator")
        st.write("Adjust the sliders to map out the required section scores to hit your state benchmark.")
        
        sim_rw = st.slider("Simulated Reading & Writing Score", 160, 800, latest_rw if latest_rw > 0 else 700, 10)
        sim_math = st.slider("Simulated Math Score", 160, 800, latest_math if latest_math > 0 else 700, 10)
        
        sim_index = calculate_selection_index(sim_rw, sim_math)
        if sim_index >= target:
            st.success(f"🎉 Simulated Index: {sim_index} (Meets National Merit requirements!)")
        else:
            st.warning(f"⚠️ Simulated Index: {sim_index} (Falls below cutoff by {target - sim_index} pts)")

    with history_col:
        st.subheader("📈 Score History")
        if all_scores:
            # Create a clean dataframe for the interactive table
            df = pd.DataFrame(all_scores, columns=["Date", "Total", "Math", "R/W"])
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("No practice scores logged yet. Use the sidebar to enter your first test!")

    st.divider()

    st.header("🧠 Autonomous Action Plan")
    if st.button("Generate Strategic Timeline", type="primary"):
        with st.spinner("Agent is mapping the Khan Academy curriculum to your remaining timeline..."):
            agent = StrategistAgent(st.session_state['student_id'], st.session_state.get('state_code', 'Unknown'), st.session_state.get('class_year', 2028))
            st.session_state['action_plan'] = agent.generate_action_plan()

    if st.session_state['action_plan']:
        plan = st.session_state['action_plan']
        if "error" in plan: st.error(plan["error"])
        else:
            st.success("Curriculum Mapping Complete.")
            st.write(f"**Strategic Insight:** {plan.get('analysis_summary', '')}")
            st.subheader(f"🗓️ Comprehensive Pacing Guide ({plan.get('total_weeks', 'Calculated')} Weeks)")
            for item in plan.get('schedule', []):
                with st.container():
                    c_week, c_math, c_rw = st.columns([1, 2, 2])
                    with c_week: st.markdown(f"### {item.get('week')}")
                    with c_math: st.markdown(f"**🧮 Math:** {item.get('math_topic')}"); st.caption(f"[Practice]({item.get('math_link')})")
                    with c_rw: st.markdown(f"**📚 R/W:** {item.get('rw_topic')}"); st.caption(f"[Practice]({item.get('rw_link')})")
                    st.divider()

    # --- MASTER SYLLABUS TRACKER ---
    st.header("✅ Master Syllabus Tracker")
    st.write("Track your progress across the complete Digital SAT curriculum. Changes save automatically.")

    # 1. Fetch saved progress from SQLite
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT topic, is_completed FROM syllabus_progress WHERE student_id = ?", (st.session_state['student_id'],))
    progress_data = {row[0]: bool(row[1]) for row in c.fetchall()}
    conn.close()

    # 2. Callback function that fires when a checkbox is clicked
    def handle_toggle(topic_name):
        is_checked = st.session_state[f"chk_{topic_name}"]
        interceptor.process_secure_request(
            action_type="UPDATE_SYLLABUS",
            student_id=st.session_state['student_id'],
            session_token=st.session_state['session_token'],
            active_token=st.session_state['session_token'],
            payload={"topic": topic_name, "is_completed": 1 if is_checked else 0}
        )

    # 3. Render the interactive UI grid
    math_topics = [
        "Algebra: Linear Equations", "Algebra: Systems of Equations", 
        "Advanced Math: Quadratics", "Advanced Math: Non-Linear Functions", 
        "Problem-Solving: Rates & Percentages", "Geometry: Triangles & Trigonometry"
    ]
    
    rw_topics = [
        "Information & Ideas: Central Ideas", "Information & Ideas: Command of Evidence", 
        "Craft & Structure: Words in Context", "Craft & Structure: Text Structure", 
        "Expression of Ideas: Transitions", "Standard English Conventions: Boundaries"
    ]

    checklist_col1, checklist_col2 = st.columns(2)

    with checklist_col1:
        st.subheader("🧮 Math")
        for t in math_topics:
            # Connect the state, unique key, and on_change callback
            st.checkbox(t, value=progress_data.get(t, False), key=f"chk_{t}", on_change=handle_toggle, args=(t,))

    with checklist_col2:
        st.subheader("📚 Reading & Writing")
        for t in rw_topics:
            st.checkbox(t, value=progress_data.get(t, False), key=f"chk_{t}", on_change=handle_toggle, args=(t,))

# --- NOTEBOOK-LM STYLE CHAT INTERFACE ---
    st.divider()
    st.header("💬 Interactive Syllabus Tutor")
    st.write("Ask me anything about what is on the test! I have the entire 200-page official College Board Framework memorized.")

    # 1. Load the PDF into memory (this runs fast because it's cached!)
    framework_pdf = load_sat_framework()

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("E.g., Exactly what percentage of the math section is Algebra?"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.chat_messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Scanning the official framework..."):
                
                # 2. Pass the PDF object into the agent
                tutor = SyllabusTutorAgent(uploaded_file=framework_pdf)
                answer = tutor.answer_question(prompt)
                st.markdown(answer)
                
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

else:
    st.warning("Awaiting Zero-Trust Authentication. Please log in using the sidebar to access the dashboard.")