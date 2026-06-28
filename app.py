# app.py
import streamlit as st
import os
from interceptor import process_secure_request
from agents.tutor import SyllabusTutorAgent
from constants import STATES_LIST  
from agents.skills.nmsi_calculator.nmsi_calculator import calculate_selection_index

# --- MOCK AUTHENTICATION ---
# In a real app, these come from a login screen. We hardcode them here to pass the interceptor.
CURRENT_STUDENT_ID = "student_001"
SESSION_TOKEN = "valid_token"
ACTIVE_TOKEN = "valid_token"

# --- Initialize Tutor ---
@st.cache_resource
def get_tutor():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    kb_location = os.path.join(base_dir, "knowledge_base", "SAT_Tutor.md")
    
    if os.path.exists(kb_location):
        return SyllabusTutorAgent(kb_location)
    return None

tutor = get_tutor()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- UI Layout & Sidebar ---
st.set_page_config(page_title="TestPrep_Agent", layout="wide")
st.title("TestPrep_Agent")

with st.sidebar:
    st.header("1. Student Profile")
    state_code = st.selectbox("State", STATES_LIST, index=STATES_LIST.index("WA") if "WA" in STATES_LIST else 0)
    graduation_year = st.number_input("Graduation Year", min_value=2026, max_value=2035, value=2028)
    
    if st.button("Save Profile"):
        payload = {"state_code": state_code, "graduation_year": graduation_year}
        resp = process_secure_request("SAVE_PROFILE", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
        if resp["status"] == "success":
            st.success("Profile saved to database!")
        else:
            st.error(resp["message"])
    
    st.divider()

    st.header("2. Log Mock Scores")
    date_test_taken = st.date_input("Date Test Taken")
    math_score = st.number_input("Math Score", min_value=160, max_value=800, value=500, step=10)
    rw_score = st.number_input("R/W Score", min_value=160, max_value=800, value=500, step=10)
    
    if st.button("Log Scores"):
        payload = {
            "date_test_taken": date_test_taken.strftime("%Y-%m-%d"), 
            "math_score": math_score, 
            "reading_writing_score": rw_score
        }
        resp = process_secure_request("LOG_SCORES", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
        if resp["status"] == "success":
            st.success("Scores saved to database!")
        else:
            st.error(resp["message"])
            
    st.divider()
    
    st.header("3. Target Test Date")
    target_date = st.date_input("When are you taking the real SAT?")
    target_date_str = target_date.strftime("%Y-%m-%d")

# --- Main Dashboard (Tabs) ---
tab_analytics, tab_planner, tab_tutor = st.tabs(["📊 Analytics", "📅 Strategic Planner", "💬 Syllabus Tutor"])

# --- TAB 1: ANALYTICS DASHBOARD ---
with tab_analytics:
    # Securely fetch data via Interceptor
    analytics_resp = process_secure_request("GET_ANALYTICS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
    
    if analytics_resp["status"] == "error":
        st.warning("Please save your profile in the sidebar to view analytics.")
    else:
        data = analytics_resp["data"]
        
        # Create the 3-card layout
        col1, col2, col3 = st.columns(3)
        
        # CARD 1: Personal Best
        with col1:
            st.subheader("🏆 Personal Best")
            st.container(border=True).metric(
                label=f"Date: {data['best_date']}", 
                value=data['best_score'] if data['best_score'] > 0 else "-"
            )
            
        # CARD 2: Score History
        with col2:
            st.subheader("📈 Last 5 Tests")
            if data["recent_scores"]:
                # Streamlit natively converts lists of dicts into nice tables
                st.dataframe(data["recent_scores"], hide_index=True, use_container_width=True)
            else:
                st.info("No practice tests logged yet.")
                
        # CARD 3: NMSI Simulator
            with col3:
                st.subheader(f"🎯 {data['state_code']} NMSI Simulator")
                with st.container(border=True):
                    # NMSI uses PSAT scoring (Max 760 per section)
                    sim_rw = st.slider("R/W Score", min_value=160, max_value=760, value=700, step=10)
                    sim_math = st.slider("Math Score", min_value=160, max_value=760, value=700, step=10)
                    
                    # 1. Calculate simulated score from sliders
                    nmsi_score = calculate_selection_index(sim_rw, sim_math)
                    real_cutoff = data['nmsi_cutoff']
                    
                    # 2. Calculate real NMSI from latest test (if any)
                    if data["recent_scores"]:
                        # Index [0] grabs the most recent test from the sorted list
                        latest_test = data["recent_scores"][0] 
                        real_nmsi = calculate_selection_index(latest_test["RW"], latest_test["Math"])
                        st.caption(f"Your Latest Real NMSI: **{real_nmsi}**")
                    else:
                        st.caption("Your Latest Real NMSI: **No tests logged**")
                    
                    # 3. Display the projected metric (delta removed as requested)
                    st.metric(f"Projected Index (Target: {real_cutoff})", value=nmsi_score)

# --- TAB 2: STRATEGIC PLANNER ---
with tab_planner:
    st.write("Generate a personalized study timeline backed by your saved data.")

    if st.button("Generate Strategic Timeline", type="primary"):
        # ROUTE THROUGH INTERCEPTOR
        payload = {"test_date": target_date_str}
        response = process_secure_request("GENERATE_PLAN", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
        
        if response["status"] == "error":
            st.error(response["message"])
        else:
            schedule_json = response["data"]
            
            st.success(f"**Target Date:** {schedule_json.get('target_test_date')} ({schedule_json.get('weeks_remaining')} weeks remaining)")
            st.info(f"**Current Strategy:** {schedule_json.get('pacing_strategy')}")
            st.warning(f"**Focus:** {schedule_json.get('overall_focus')}")
            st.divider()
            
            st.subheader("📅 Your Strategic Study Plan")
            
            # --- 1. Table Header ---
            col1, col2, col3 = st.columns([1, 4, 1.5])
            with col1: st.markdown("**Week**")
            with col2: st.markdown("**Tasks**")
            with col3: st.markdown("**Mastery**")
            st.divider()
            
            # --- 2. Data Prep: Group tasks by week number ---
            weeks_dict = {}
            for domain in ['math', 'reading_writing']:
                if schedule_json['schedules'].get(domain):
                    for week_data in schedule_json['schedules'][domain]:
                        w_num = week_data['week']
                        if w_num not in weeks_dict:
                            weeks_dict[w_num] = {'math': [], 'reading_writing': []}
                        weeks_dict[w_num][domain] = week_data['tasks']

            # --- 3. Render the Table Rows ---
            for w_num in sorted(weeks_dict.keys()):
                col1, col2, col3 = st.columns([1, 4, 1.5])
                
                math_tasks = weeks_dict[w_num]['math']
                rw_tasks = weeks_dict[w_num]['reading_writing']
                
                # Column 1: Week Number
                with col1:
                    st.write(f"Week {w_num}")
                
                # Column 2: Combined Tasks
                with col2:
                    for task in math_tasks:
                        st.markdown(f"**Math:** {task}")
                    for task in rw_tasks:
                        st.markdown(f"**R&W:** {task}")
                        
                # Column 3: Mark Mastered Buttons (Preserving your DB update logic!)
                with col3:
                    for task in math_tasks:
                        if task != "🎯 FULL-LENGTH DIGITAL PRACTICE TEST":
                            if st.button("Mark Mastered", key=f"math_{w_num}_{task}"):
                                process_secure_request("UPDATE_SYLLABUS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"topic": task, "is_completed": 1})
                                st.rerun()
                        else:
                            st.write("") # Invisible spacer to keep alignment perfect

                    for task in rw_tasks:
                        if task != "🎯 FULL-LENGTH DIGITAL PRACTICE TEST":
                            if st.button("Mark Mastered", key=f"rw_{w_num}_{task}"):
                                process_secure_request("UPDATE_SYLLABUS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"topic": task, "is_completed": 1})
                                st.rerun()
                        else:
                            st.write("") # Invisible spacer to keep alignment perfect
                
                st.divider()

# --- TAB 3: SYLLABUS TUTOR ---
with tab_tutor:
    st.write("Ask questions about the SAT format, rules, and concepts. I only pull answers directly from the official College Board framework.")
    
    if not tutor:
        st.warning("⚠️ Knowledge base file not found. Please place 'SAT_Tutor.md' in the 'knowledge_base' folder.")
    else:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        user_input = st.chat_input("Ask a question (e.g., 'What is the format of the math section?')")
        
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)
                
            with st.chat_message("assistant"):
                with st.spinner("Searching the syllabus..."):
                    answer = tutor.answer_question(user_input)
                    st.markdown(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})