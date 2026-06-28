# app.py
import streamlit as st
import pandas as pd
import os
from interceptor import process_secure_request
from constants import STATES_LIST

# --- PAGE CONFIG & STYLING ---
# initial_sidebar_state="collapsed" hides the default sidebar entirely
st.set_page_config(page_title="TestPrep_Agent", layout="wide", initial_sidebar_state="collapsed")

# def load_css(file_name):
#     if os.path.exists(file_name):
#         with open(file_name) as f:
#             st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# load_css("style.css")

# --- MOCK AUTHENTICATION ---
CURRENT_STUDENT_ID = "student_001"
SESSION_TOKEN = "valid_token"
ACTIVE_TOKEN = "valid_token"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- TOP NAVIGATION (Mock Header) ---
st.markdown("### TestPrep_Agent")
st.divider()

# --- THE MASTER GRID ---
# 1:2:1 ratio gives the middle column twice the width
left_col, mid_col, right_col = st.columns([1, 2, 1], gap="large")

# ==========================================
# LEFT COLUMN: DATA ENTRY
# ==========================================
with left_col:
    st.subheader("1. Get Started & Log Progress")
    
    with st.container(border=True):
        st.markdown("**Student Profile**")
        state_code = st.selectbox("State", STATES_LIST, index=STATES_LIST.index("WA") if "WA" in STATES_LIST else 0)
        graduation_year = st.number_input("Graduation Year", min_value=2026, max_value=2035, value=2028)
        
        if st.button("Save Profile", use_container_width=True):
            payload = {"state_code": state_code, "graduation_year": graduation_year}
            resp = process_secure_request("SAVE_PROFILE", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
            if resp["status"] == "success":
                st.success("Saved!")
            else:
                st.error(resp["message"])

    with st.container(border=True):
        st.markdown("**Log Mock Scores**")
        date_test_taken = st.date_input("Test Date")
        math_score = st.number_input("Math Score", min_value=160, max_value=800, value=500, step=10)
        rw_score = st.number_input("R/W Score", min_value=160, max_value=800, value=500, step=10)
        
        if st.button("Log Scores", use_container_width=True):
            payload = {
                "date_test_taken": date_test_taken.strftime("%Y-%m-%d"), 
                "math_score": math_score, 
                "reading_writing_score": rw_score
            }
            resp = process_secure_request("LOG_SCORES", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
            if resp["status"] == "success":
                st.success("Saved!")
            else:
                st.error(resp["message"])

# ==========================================
# MIDDLE COLUMN: INSIGHTS & STRATEGY
# ==========================================
with mid_col:
    st.subheader("📊 Analytics Dashboard")
    
    analytics_resp = process_secure_request("GET_ANALYTICS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
    
    if analytics_resp["status"] == "error":
        st.warning("Please save your profile to view analytics.")
    else:
        data = analytics_resp["data"]
        
        # Nested grid for the 3 analytics cards
        a_col1, a_col2, a_col3 = st.columns(3)
        
        with a_col1:
            with st.container(border=True):
                st.markdown("**🏆 Personal Best**")
                st.metric(
                    label=f"Date: {data.get('best_date', '-')}", 
                    value=data.get('best_score', '-') if data.get('best_score', 0) > 0 else "-"
                )
                
            with st.container(border=True):
                st.markdown("**🎯 Next Milestone**")
                target_date = st.date_input("Target Test Date")
                
        with a_col2:
            with st.container(border=True):
                st.markdown("**📈 Score History**")
                if data.get("recent_scores"):
                    # Convert to pandas dataframe to render a line chart
                    df = pd.DataFrame(data["recent_scores"])
                    # Use 'Date' as index if it exists so it plots along the X-axis
                    if "Date" in df.columns:
                        df = df.set_index("Date")
                    # Plot specific columns to avoid plotting unrelated integers
                    cols_to_plot = [c for c in ["Math", "RW", "Total"] if c in df.columns]
                    st.line_chart(df[cols_to_plot], height=200)
                else:
                    st.info("No practice tests logged yet.")
                    
        with a_col3:
            with st.container(border=True):
                st.markdown(f"**🎯 {data.get('state_code', 'State')} NMSI Simulator**")
                sim_rw = st.slider("R/W", 160, 760, 700, 10)
                sim_math = st.slider("Math", 160, 760, 700, 10)
                
                sim_nmsi_resp = process_secure_request("CALCULATE_NMSI", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"scores": {"rw": sim_rw, "math": sim_math}})
                nmsi_score = sim_nmsi_resp.get("data", "Error") if sim_nmsi_resp["status"] == "success" else "Error"
                
                st.metric(f"Simulated Index (Target: {data.get('nmsi_cutoff', '-')})", value=nmsi_score)

    st.divider()
    
    st.subheader("📅 Strategic Study Planner")
    with st.container(border=True):
        if st.button("Generate Timeline Strategy", type="primary"):
            payload = {"test_date": target_date.strftime("%Y-%m-%d")}
            response = process_secure_request("GENERATE_PLAN", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
            
            if response["status"] == "success":
                schedule_json = response["data"]
                st.success(f"**Target Date:** {schedule_json.get('target_test_date')} ({schedule_json.get('weeks_remaining')} weeks)")
                
                weeks_dict = {}
                for domain in ['math', 'reading_writing']:
                    if schedule_json['schedules'].get(domain):
                        for week_data in schedule_json['schedules'][domain]:
                            w_num = week_data['week']
                            if w_num not in weeks_dict:
                                weeks_dict[w_num] = {'math': [], 'reading_writing': []}
                            weeks_dict[w_num][domain] = week_data['tasks']

                for w_num in sorted(weeks_dict.keys()):
                    with st.expander(f"Week {w_num} Tasks"):
                        for task in weeks_dict[w_num]['math']: 
                            st.checkbox(f"**Math:** {task}", key=f"math_{w_num}_{task}")
                        for task in weeks_dict[w_num]['reading_writing']: 
                            st.checkbox(f"**R&W:** {task}", key=f"rw_{w_num}_{task}")

# ==========================================
# RIGHT COLUMN: TUTOR & MASTERY
# ==========================================
with right_col:
    st.subheader("📚 Syllabus & Tutor Hub")
    
    with st.container(border=True):
        st.markdown("**Mastery Tracker**")
        syllabus_topics = ["Heart of Algebra", "Problem Solving and Data Analysis", "Passport to Advanced Math"]
        
        for topic in syllabus_topics:
            with st.expander(f"📖 {topic}"):
                is_completed = st.checkbox("Mark Mastered", key=f"chk_{topic}")
                if is_completed:
                    process_secure_request("UPDATE_SYLLABUS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"topic": topic, "is_completed": 1})
                if st.button("Ask AI to Break This Down", key=f"btn_{topic}", use_container_width=True):
                    with st.spinner("Generating..."):
                        response = process_secure_request("EXPAND_TOPIC", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"topic_name": topic})
                        if response.get("status") == "success":
                            st.markdown(response["data"])

    st.markdown("**Chat with Tutor Agent**")
    if st.button("🧹 Clear", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    chat_container = st.container(height=400, border=True)
    
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    user_input = st.chat_input("Ask a question...")
    
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.rerun()
        
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        latest_question = st.session_state.chat_history[-1]["content"]
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    recent_context = st.session_state.chat_history[-4:]
                    payload = {"message": latest_question, "recent_context": recent_context}
                    response = process_secure_request("TUTOR_CHAT", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
                    answer = response.get("data", "Error: Could not reach Tutor Agent.")
                    st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})