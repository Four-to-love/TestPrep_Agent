# app.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
from interceptor import process_secure_request
from constants import STATES_LIST
from agents.skills.calendar_export.export_ics import export_schedule_to_ics

st.set_page_config(page_title="TestPrep_Agent", layout="wide", initial_sidebar_state="collapsed", menu_items={})

def load_css(file_name):
    dir_path = os.path.dirname(__file__)
    full_path = os.path.join(dir_path, file_name)
    if os.path.exists(full_path):
        with open(full_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    elif os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css("style.css")

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
# Removed placeholder image to utilize page space for tabs

# --- LEFT PANEL (Floating Popover) ---
floating_left_panel_css = """
<style>
    /* Hide the native sidebar toggle arrow entirely */
    [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Pin the left panel popover to the bottom-left corner */
    [data-testid="stPopover"]:first-of-type {
        position: fixed;
        bottom: 0px !important;
        left: 40px !important;
        right: auto !important;
        width: 300px !important;
        z-index: 9998;
    }

    /* Style the trigger button to look like a gold docked bar (flat bottom, rounded top) */
    [data-testid="stPopover"]:first-of-type > button {
        border-radius: 12px 12px 0px 0px !important;
        height: 45px;
        width: 100% !important;
        box-shadow: 0 -4px 15px rgba(0,0,0,0.15) !important;
        background-color: #e1ad01 !important;
        color: #15343f !important;
        font-weight: bold !important;
        border: none !important;
    }

    [data-testid="stPopover"]:first-of-type > button:hover {
        background-color: #cfa001 !important;
        color: #15343f !important;
    }
</style>
"""
st.markdown(floating_left_panel_css, unsafe_allow_html=True)

with st.popover("⚙️ Profile & Scores"):
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
            st.success("Saved!")
            st.rerun()
        else:
            st.error(resp["message"])
            
    st.divider()
    st.header("Log Mock Scores")
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

# --- MAIN LAYOUT ---
center_col, right_col = st.columns([2.5, 1], gap="large")

# Fetch analytics for right column metrics
analytics_resp = process_secure_request("GET_ANALYTICS", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, {})
analytics_data = analytics_resp.get("data", {}) if analytics_resp["status"] == "success" else {}

# Initialize Schedule Data in Session State for Interactive Editing
# Initialize Schedule Data in Session State for Interactive Editing
if "schedule_df" not in st.session_state:
    build_schedule_from_db()

# --- CENTER COLUMN: CORE INTERFACE ---
with center_col:
    st.markdown('<h1 class="main-title">PSAT/SAT Prep Interactive Timeline</h1>', unsafe_allow_html=True)
    
    # ---- 3. CENTRAL CONTENT AREA ----
    tab1, tab2, tab3, tab4 = st.tabs(["🗓️ Interactive Schedule", "📐 Math Timeline", "📚 Reading & Writing Timeline", "💡 Study Tips"])

    with tab1:
        # Center the control area inside tab1
        col_l, col_mid, col_r = st.columns([0.6, 3.0, 0.6])
        with col_mid:
            # 1. Strategy from strategist
            pacing = st.session_state.get("pacing_strategy", "")
            if pacing:
                st.markdown(
                    f"<p style='text-align: center; color: white !important; font-size: 0.95rem; font-style: italic; margin: 0px 0px 12px 0px;'>{pacing}</p>",
                    unsafe_allow_html=True,
                )

            # 2. Message about test date
            st.markdown(
                "<p style='text-align: center; color: white !important; font-size: 0.95rem; font-weight: 500; margin: 0px 0px 12px 0px;'>"
                "Have a test date? Enter it here, and we'll build your study plan so you stay on track and cover everything before test day."
                "</p>",
                unsafe_allow_html=True,
            )

            # 3–5. Date input + buttons all on one row
            saved_date_str = st.session_state.student_profile.get("target_test_date") or ""
            saved_date_obj = datetime.date.today()
            if saved_date_str:
                try:
                    saved_date_obj = datetime.datetime.strptime(saved_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            row_col1, row_col2, row_col3 = st.columns([2, 1, 1], gap="small")
            with row_col1:
                test_date_input = st.date_input(
                    "Future Test Date",
                    value=saved_date_obj,
                    label_visibility="collapsed",
                )
            with row_col2:
                if st.button("💾 Save Date", use_container_width=True, key="save_test_date_btn"):
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
                ics_path = export_schedule_to_ics(st.session_state.schedule_df)
                with open(ics_path, "rb") as f:
                    st.download_button(
                        label="📅 Save to Calendar",
                        data=f,
                        file_name="schedule.ics",
                        mime="text/calendar",
                        use_container_width=True,
                        key="dl_ics_btn",
                    )


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
        st.subheader("Learning Strategy Tips")
        st.markdown('''
        * **Consistency is Key**: Study 30 minutes a day rather than cramming for 4 hours on Sunday.
        * **Review Mistakes**: Don't just check answers; understand *why* you got them wrong.
        * **Take Full Practice Tests**: Simulate testing conditions to build stamina.
        * **Focus on Weaknesses**: Don't just practice what you're already good at.
        * **Rest & Recover**: Your brain processes information during sleep. Don't pull all-nighters!
        ''')


# --- RIGHT COLUMN: INSIGHTS & SUPPORT ---
with right_col:
    # 1. Widgets Section
    
    # Calculate best score metrics
    best_total = analytics_data.get("best_score", 0)
    best_math = analytics_data.get("best_math", 0)
    best_rw = analytics_data.get("best_rw", 0)
    best_date = analytics_data.get("best_date", "No tests logged")
    
    # Render Best Score card
    st.markdown(f"""
    <div style="background-color: #15343f; border: 3px solid #e1ad01; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <div style="font-size: 1.1rem; font-weight: 700; color: white; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">🏆 Your Best Score</div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">Total</div>
                <div style="font-size: 1.8rem; font-weight: 700; color: #e1ad01;">{best_total if best_total > 0 else '-'}</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.15); height: 40px;"></div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">Math</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: white;">{best_math if best_math > 0 else '-'}</div>
            </div>
            <div style="border-left: 1px solid rgba(255,255,255,0.15); height: 40px;"></div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7);">R&W</div>
                <div style="font-size: 1.5rem; font-weight: 700; color: white;">{best_rw if best_rw > 0 else '-'}</div>
            </div>
        </div>
        <div style="font-size: 0.8rem; color: rgba(255,255,255,0.5); text-align: center;">
            Logged on: {best_date}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
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
    
    # Parse to int for comparison
    try:
        pred_val = int(pred_nmsi)
        cutoff_val = int(state_cutoff)
        is_passing = pred_val >= cutoff_val
    except:
        is_passing = False
 
    # Dynamic styling and messages
    bg_color = "#123b20" if is_passing else "#15343f"
    border_color = "#2ecc71" if is_passing else "#e1ad01"
    msg_color = "#2ecc71" if is_passing else "#f1c40f"
    
    if is_passing:
        message = "🎉 You are on the path to the National Merit Scholarship!"
    else:
        message = "Follow the preparation schedule, stay consistent, and believe in yourself. Your effort will add up, and your score will improve. 🌟."
 
    # Render custom combined card
    st.markdown(f"""
    <div style="background-color: {bg_color}; border: 3px solid {border_color}; border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
            <div>
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-bottom: -10px;">Predicted NMSI Score</div>
                <div style="font-size: 2.5rem; font-weight: 700; color: white;">{pred_nmsi}</div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-bottom: -10px;">State Cutoff</div>
                <div style="font-size: 2.5rem; font-weight: 700; color: white;">{state_cutoff}</div>
            </div>
        </div>
        <div style="font-size: 0.82rem; font-weight: 400; color: {msg_color}; line-height: 1.4;">
            {message}
        </div>
    </div>
    """, unsafe_allow_html=True)
   # ==========================================
# FLOATING CHAT WIDGET
# ==========================================

# 1. Inject CSS to glue the popover to the bottom right and style the gold button
floating_chat_css = """
<style>
    /* Pin the popover container to the bottom right corner */
    [data-testid="stPopover"] {
        position: fixed;
        bottom: 0px !important;
        right: 40px !important;
        left: auto !important;
        width: 350px !important; /* Matches the standard chat window width */
        z-index: 9999; /* Ensures it floats over everything else */
    }
    
    /* Style the button to look like a gold docked chat bar sitting flush on the bottom edge */
    [data-testid="stPopover"] > button {
        border-radius: 12px 12px 0px 0px !important; /* Rounded top corners, flat bottom */
        height: 45px;
        width: 100% !important; /* Expand to 350px */
        box-shadow: 0 -4px 15px rgba(0,0,0,0.15) !important;
        background-color: #e1ad01 !important; /* Brand gold button */
        color: #15343f !important; /* Dark text for readability on gold */
        font-weight: bold !important;
        border: none !important;
    }
    
    /* Button hover state */
    [data-testid="stPopover"] > button:hover {
        background-color: #cfa001 !important;
        color: #15343f !important;
    }
</style>
"""
st.markdown(floating_chat_css, unsafe_allow_html=True)     

with st.popover("💬 Ask SAT Tutor a question"):
    # 3. Tutor Chat Fragment
    @st.fragment
    def tutor_chat():
        chat_container = st.container(height=400, border=False)
        
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.container():
                    st.markdown(f'<div class="chat-message-marker-{msg["role"]}" style="display:none;"></div>', unsafe_allow_html=True)
                    st.markdown(msg["content"])
                    
        user_input = st.chat_input("Ask a question...", key="tutor_input")
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            # To update the UI within the fragment instantly:
            with chat_container:
                with st.container():
                    st.markdown('<div class="chat-message-marker-user" style="display:none;"></div>', unsafe_allow_html=True)
                    st.markdown(user_input)
                with st.spinner("Thinking..."):
                    recent_context = st.session_state.chat_history[-4:]
                    payload = {"message": user_input, "recent_context": recent_context}
                    response = process_secure_request("TUTOR_CHAT", CURRENT_STUDENT_ID, SESSION_TOKEN, ACTIVE_TOKEN, payload)
                    answer = response.get("data", "Error: Could not reach Tutor Agent.")
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun() # Reruns just this fragment!

    tutor_chat()