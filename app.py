# app.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
from interceptor import process_secure_request
from constants import STATES_LIST

st.set_page_config(page_title="TestPrep_Agent", layout="wide", initial_sidebar_state="expanded")



# --- MOCK AUTHENTICATION ---
CURRENT_STUDENT_ID = "student_001"
SESSION_TOKEN = "valid_token"
ACTIVE_TOKEN = "valid_token"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Load student profile on startup via secure interceptor request
if "student_profile" not in st.session_state:
    resp = process_secure_request("GET_STUDENT", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
    if resp["status"] == "success":
        st.session_state.student_profile = resp["data"]
    else:
        st.session_state.student_profile = {"state_code": "WA", "graduation_year": 2028, "target_test_date": ""}

# Define schedule builder helper
def build_schedule_from_db():
    plan_resp = process_secure_request("GENERATE_PLAN", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
    if plan_resp["status"] == "success":
        plan_data = plan_resp.get("data", {})
        # Stash focus and pacing strategy in session state
        st.session_state.overall_focus = plan_data.get("overall_focus", "")
        st.session_state.pacing_strategy = plan_data.get("pacing_strategy", "")
        
        if "schedule_error" in st.session_state:
            del st.session_state.schedule_error
        rows = []
        if plan_data and "schedules" in plan_data:
            start_date = datetime.date.today()
            weeks = {}
            for domain in ['math', 'reading_writing']:
                if plan_data['schedules'].get(domain):
                    for week_data in plan_data['schedules'][domain]:
                        w_num = week_data['week']
                        if w_num not in weeks:
                            weeks[w_num] = {'Math Tasks': [], 'Reading & Writing Tasks': []}
                        if domain == 'math':
                            weeks[w_num]['Math Tasks'].extend(week_data['tasks'])
                        else:
                            weeks[w_num]['Reading & Writing Tasks'].extend(week_data['tasks'])
                            
            for w_num in sorted(weeks.keys()):
                week_start_date = start_date + datetime.timedelta(days=(w_num-1)*7)
                math_str = "\n• ".join(weeks[w_num]['Math Tasks']) if weeks[w_num]['Math Tasks'] else "You finished the curriculum. Now practice the most hard parts."
                if weeks[w_num]['Math Tasks']: math_str = "• " + math_str
                
                rw_str = "\n• ".join(weeks[w_num]['Reading & Writing Tasks']) if weeks[w_num]['Reading & Writing Tasks'] else "You finished the curriculum. Now practice the most hard parts."
                if weeks[w_num]['Reading & Writing Tasks']: rw_str = "• " + rw_str
                
                rows.append({
                    "Week": f"Week {w_num}\n{week_start_date.strftime('%B, %d')}",
                    "Math Focus": math_str,
                    "Reading & Writing Focus": rw_str,
                    "Mastered": False
                })
        st.session_state.schedule_df = pd.DataFrame(rows)
    else:
        st.session_state.schedule_df = pd.DataFrame()
        st.session_state.schedule_error = plan_resp.get("message", "Unknown error generating plan.")

# --- HEADER ---


# --- LEFT PANEL (Slide-in Sidebar) ---
with st.sidebar:
    st.header("Student Profile")
    saved_state = st.session_state.student_profile.get("state_code", "WA")
    state_idx = STATES_LIST.index(saved_state) if saved_state in STATES_LIST else 0
    state_code = st.selectbox("State", STATES_LIST, index=state_idx)
    
    saved_grad_year = st.session_state.student_profile.get("graduation_year", 2028)
    graduation_year = st.number_input("Graduation Year", min_value=2026, max_value=2035, value=int(saved_grad_year))
    if st.button("Save Profile", use_container_width=True):
        payload = {
            "state_code": state_code,
            "graduation_year": graduation_year,
            "target_test_date": st.session_state.student_profile.get("target_test_date", "")
        }
        resp = process_secure_request("SAVE_PROFILE", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
        if resp["status"] == "success":
            st.session_state.student_profile["state_code"] = state_code
            st.session_state.student_profile["graduation_year"] = graduation_year
            build_schedule_from_db()
            #st.success("Saved!")
            st.rerun()
        else:
            st.error(resp["message"])
            
    st.divider()
    import time

    st.header("Save your recent test results")
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
            # 1. Clear the cache so the app is forced to fetch the new scores
            st.cache_data.clear() 
            
            # 2. Re-pull the fresh data into your session state
            build_schedule_from_db()
            
            # 3. Show a toast or success message, then pause briefly before wiping the screen
            st.success("Scores successfully saved!")
            time.sleep(0.75) 
            
            # 4. Now trigger the UI refresh
            st.rerun()
        else:
            st.error(resp["message"])

# --- MAIN LAYOUT ---
center_col, right_col = st.columns([2.5, 1], gap="large")

analytics_resp = process_secure_request("GET_ANALYTICS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
if analytics_resp["status"] == "success":
    analytics_data = analytics_resp.get("data", {})
else:
    st.error(f"Analytics Error: {analytics_resp.get('message')}")
    analytics_data = {}

# Initialize Schedule Data in Session State for Interactive Editing
# Initialize Schedule Data in Session State for Interactive Editing
if "schedule_df" not in st.session_state:
    build_schedule_from_db()

# --- CENTER COLUMN: CORE INTERFACE ---
with center_col:
    st.title("PSAT/SAT Prep Interactive Timeline")
    
    # ---- 3. CENTRAL CONTENT AREA ----
    tab1, tab2, tab3, tab4 = st.tabs([
    "🗓️ Master Academic Schedule", 
    "📐 Mathematics Concept Plan", 
    "📚 Reading and Writing Plan", 
    "💬 Chat with SAT Tutor"
])
    with tab1:
        # Center the control area inside tab1
        col_l, col_mid, col_r = st.columns([0.1, 4.0, 0.1])
        with col_mid:
            # 1. Message about plan
            st.markdown("Here is your personal schedule based on your graduation year.")
            # 2. Strategy from strategist
            pacing = st.session_state.get("pacing_strategy", "")
            if pacing:
                st.markdown(f"*{pacing}*")

            # 3. Message about test date
            st.markdown("Have a test date? Enter it here, and we'll build your study plan so you stay on track and cover everything before test day.")

            # 3–5. Date input + buttons all on one row
            saved_date_str = st.session_state.student_profile.get("target_test_date") or ""
            saved_date_obj = datetime.date.today()
            if saved_date_str:
                try:
                    saved_date_obj = datetime.datetime.strptime(saved_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            row_col1, row_col2, row_col3 = st.columns([2, 1, 1], gap="medium")
            with row_col1:
                test_date_input = st.date_input(
                    "Future Test Date",
                    value=saved_date_obj,
                    label_visibility="collapsed",
                )
            with row_col2:
                if st.button("Save", use_container_width=True, key="save_test_date_btn"):
                    date_str = test_date_input.strftime("%Y-%m-%d") if test_date_input else ""
                    state_code = st.session_state.student_profile.get("state_code", "WA")
                    graduation_year = st.session_state.student_profile.get("graduation_year", 2028)
                    save_payload = {
                        "state_code": state_code,
                        "graduation_year": graduation_year,
                        "target_test_date": date_str,
                    }
                    save_resp = process_secure_request(
                        "SAVE_PROFILE",
                        CURRENT_STUDENT_ID,
                        SESSION_TOKEN,
                        ACTIVE_TOKEN,
                        save_payload,
                    )
                    if save_resp["status"] == "success":
                        st.session_state.student_profile["target_test_date"] = date_str
                        build_schedule_from_db()
                        st.rerun()
                    else:
                        st.error(save_resp["message"])
            with row_col3:
                ics_resp = process_secure_request(
                    "EXPORT_ICS",
                    CURRENT_STUDENT_ID,
                    SESSION_TOKEN,
                    ACTIVE_TOKEN,
                    {"schedule_df": st.session_state.schedule_df},
                )
                if ics_resp["status"] == "success":
                    ics_path = ics_resp["data"]["ics_path"]
                    with open(ics_path, "rb") as f:
                        st.download_button(
                            label="📅 Download Calendar",
                            data=f,
                            file_name="schedule.ics",
                            mime="text/calendar",
                            use_container_width=True,
                            key="dl_ics_btn",
                        )
                else:
                    st.error(ics_resp["message"])


        if "schedule_error" in st.session_state:
            st.error(st.session_state.schedule_error)
        elif not st.session_state.schedule_df.empty:
            display_df = st.session_state.schedule_df[["Week", "Math Focus", "Reading & Writing Focus"]].copy()
            display_df = display_df.set_index("Week")
            st.table(display_df)
        else:
            st.info("No schedule data generated yet.")
            
    with tab2:
        try:
            box = st.container(border=True)
        except TypeError:
            box = st.container()
        with box:
            st.markdown("ℹ️ **Mastered something?** Update your schedule to remove completed tasks from your study plan. *Make sure you don't need extra practice on them, as the schedule will skip these topics!*")
            if st.button("Update my Schedule", use_container_width=True, key="update_schedule_math"):
                build_schedule_from_db()
                st.rerun()
        process_secure_request(
            "RENDER_SYLLABUS",
            CURRENT_STUDENT_ID,
            SESSION_TOKEN,
            ACTIVE_TOKEN,
            {
                "syllabus_file": "agents/skills/curriculum_mapper/math_granular_syllabus.json",
                "marker_class": "math-timeline-marker",
                "key_prefix": "math",
                "column_label": "Comprehensive SAT Math Topic Checklist"
            }
        )

    with tab3:
        try:
            box = st.container(border=True)
        except TypeError:
            box = st.container()
        with box:
            st.markdown("ℹ️ **Mastered something?** Update your schedule to remove completed tasks from your study plan. *Make sure you don't need extra practice on them, as the schedule will skip these topics!*")
            if st.button("Update my Schedule", use_container_width=True, key="update_schedule_rw"):
                build_schedule_from_db()
                st.rerun()
        process_secure_request(
            "RENDER_SYLLABUS",
            CURRENT_STUDENT_ID,
            SESSION_TOKEN,
            ACTIVE_TOKEN,
            {
                "syllabus_file": "agents/skills/curriculum_mapper/rw_granular_syllabus.json",
                "marker_class": "rw-timeline-marker",
                "key_prefix": "rw",
                "column_label": "Comprehensive SAT Reading & Writing Topic Checklist"
            }
        )
            
    with tab4:
        # ==========================================
        # TUTOR CHAT WIDGET
        # ==========================================
        st.subheader("Chat with SAT Tutor Agent")
        st.markdown("Not sure how the PSAT or SAT works? Ask the SAT Tutor Agent about the exam format, rules, scoring, timing, curriculum, or anything else — and get answers based on official College Board information.")
        @st.fragment
        def tutor_chat():
            with st.container(height=300):
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        
            user_input = st.chat_input("Ask a question...", key="tutor_input")
            if user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                with st.spinner("Thinking..."):
                    recent_context = st.session_state.chat_history[-4:]
                    payload = {"message": user_input, "recent_context": recent_context}
                    response = process_secure_request(
                        "TUTOR_CHAT", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload
                    )
                    answer = response.get("data", "Error: Could not reach Tutor Agent.")
                
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()

        tutor_chat()


# --- RIGHT COLUMN: INSIGHTS & SUPPORT ---
with right_col:
    # 1. Widgets Section
    
    # Calculate recent score metrics
    recent_scores = analytics_data.get("recent_scores", [])
    total_delta = None
    math_delta = None
    rw_delta = None
    if recent_scores:
        recent_total = recent_scores[0].get("Total", 0)
        recent_math = recent_scores[0].get("Math", 0)
        recent_rw = recent_scores[0].get("RW", 0)
        recent_date = recent_scores[0].get("Date", "No tests logged")
        if len(recent_scores) > 1:
            total_delta = recent_total - recent_scores[1].get("Total", 0)
            math_delta = recent_math - recent_scores[1].get("Math", 0)
            rw_delta = recent_rw - recent_scores[1].get("RW", 0)
    else:
        recent_total = 0
        recent_math = 0
        recent_rw = 0
        recent_date = "No tests logged"
    
    # Render Recent Score card
    with st.container(border=True):
        st.subheader("Your Recent Score")
        st.metric("Total", f"{recent_total}" if recent_total > 0 else "-", delta=total_delta)
        col_math, col_rw = st.columns(2)
        col_math.metric("Math", f"{recent_math}" if recent_math > 0 else "-", delta=math_delta)
        col_rw.metric("Reading and Writing", f"{recent_rw}" if recent_rw > 0 else "-", delta=rw_delta)
        st.caption(f"Logged on: {recent_date}")
    
    # Calculate predicted NMSI using latest scores
    recent_scores = analytics_data.get("recent_scores", [])
    if recent_scores:
        latest_math = recent_scores[0]["Math"]
        latest_rw = recent_scores[0]["RW"]
    else:
        latest_math = 500
        latest_rw = 500
        
    pred_resp = process_secure_request("CALCULATE_NMSI", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {"scores": {"rw": latest_rw, "math": latest_math}})
    pred_nmsi = pred_resp.get("data", "-") if pred_resp["status"] == "success" else "-"
    state_cutoff = analytics_data.get('nmsi_cutoff', '-')
    state_code = st.session_state.student_profile.get("state_code", "WA")
    
    # Parse to int for comparison
    try:
        pred_val = int(pred_nmsi)
        cutoff_val = int(state_cutoff)
        is_passing = pred_val >= cutoff_val
    except:
        is_passing = False
  
    # Dynamic messages
    if is_passing:
        message = "🎉 You are on the path to the National Merit Scholarship!"
    else:
        message = "Follow the preparation schedule, stay consistent, and believe in yourself. Your effort will add up, and your score will improve. 🌟."
 
    # Render custom combined card
    with st.container(border=True):
        col_pred, col_cut = st.columns(2)
        col_pred.metric("Predicted NMSI Index", f"{pred_nmsi}")
        col_cut.metric(f"{state_code} State Cutoff", f"{state_cutoff}")
        if is_passing:
            st.success(message)
        else:
            st.info(message)

    # Render Score Simulator
    with st.container(border=True):
        st.subheader("NMSI Index Simulator")
        sim_math = st.slider("Simulated Math Score", min_value=160, max_value=800, value=500, step=10, key="sim_math_slider")
        sim_rw = st.slider("Simulated R/W Score", min_value=160, max_value=800, value=500, step=10, key="sim_rw_slider")
        sim_nmsi = int(((2 * sim_rw) + sim_math) / 10)
        
        col_sim_pred, col_sim_cut = st.columns(2)
        col_sim_pred.metric("Simulated NMSI Index", f"{sim_nmsi}")
        col_sim_cut.metric(f"{state_code} Cutoff Target", f"{state_cutoff}")
        
        sim_is_passing = False
        try:
            sim_is_passing = sim_nmsi >= int(state_cutoff)
        except:
            pass
            
        if sim_is_passing:
            st.success("🎉 With these scores, you would meet the cutoff!")
        else:
            st.warning("⚠️ Slide the bar to see how PSAT scores effect NMSI Index.")
