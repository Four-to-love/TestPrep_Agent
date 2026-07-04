# app.py
import streamlit as st
import pandas as pd
import json
import os
import datetime
from interceptor import process_secure_request
from constants import STATES_LIST

st.set_page_config(page_title="TestPrep_Agent", layout="wide", initial_sidebar_state="collapsed")



# --- MOCK AUTHENTICATION & ZERO-TRUST SECURITY CENTER ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "student_id" not in st.session_state:
    st.session_state.student_id = ""
if "session_token" not in st.session_state:
    st.session_state.session_token = ""
if "tamper_token" not in st.session_state:
    st.session_state.tamper_token = False
if "just_logged_in" not in st.session_state:
    st.session_state.just_logged_in = False



# Live token accessors — always read from session_state at call time to prevent stale snapshots
def _sid():    return st.session_state.get("student_id", "")
def _tok():    return st.session_state.get("session_token", "")

def show_friendly_error(message: str):
    """Displays user-friendly, kid-appropriate warnings or help boxes instead of raw red consoles."""
    if not message:
        return
    msg_lower = message.lower()
    if "session token" in msg_lower or "expired" in msg_lower or "unauthorized" in msg_lower:
        st.warning("🔑 **Please sign in to save your changes!**\n\nYour login session has expired. Please uncheck the 'Tamper' box in the Security Center (or refresh the page) to log back in.")
    elif "offline" in msg_lower or "connection" in msg_lower or "server" in msg_lower:
        st.info("☁️ **Database is taking a quick break!**\n\nWe couldn't reach the database server. Make sure `python3 mcp_server.py` is running in your terminal, then try again.")
    else:
        st.info(f"💡 **Tip:** {message}")

def clear_date_error():
    if "save_date_error" in st.session_state:
        del st.session_state.save_date_error

def invalidate_summaries():
    st.session_state.summaries_loaded = False
    st.session_state.schedule_summary = ""
    st.session_state.math_summary = ""
    st.session_state.rw_summary = ""
    st.session_state.tutor_summary = ""


def clear_all_state():
    """Clears all session state variables to ensure a clean slate on login/logout."""
    for key in list(st.session_state.keys()):
        if key not in ["logged_in", "student_id", "session_token", "tamper_token"]:
            del st.session_state[key]

def build_schedule_from_db():
    """Calls GENERATE_PLAN via the interceptor and writes the result into session state."""
    plan_resp = process_secure_request("GENERATE_PLAN", _sid(), _tok(), _tok(), {})
    if plan_resp["status"] == "success":
        plan_data = plan_resp.get("data", {})
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
                week_start_date = start_date + datetime.timedelta(days=(w_num - 1) * 7)
                math_tasks = weeks[w_num]['Math Tasks']
                math_str = "\n".join(f"{idx+1}. {task}" for idx, task in enumerate(math_tasks)) if math_tasks else "You finished the curriculum. Now practice the most hard parts."
                rw_tasks = weeks[w_num]['Reading & Writing Tasks']
                rw_str = "\n".join(f"{idx+1}. {task}" for idx, task in enumerate(rw_tasks)) if rw_tasks else "You finished the curriculum. Now practice the most hard parts."
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



# --- LOGIN SIGN-IN PAGE TRIGGER ---
if not st.session_state.logged_in:
    logo_file = "logo.webp" if os.path.exists("logo.webp") else None

    # --- HERO DEMO BUTTON (full-width, right under banner) ---
    col_a, col_b, col_c = st.columns([1, 3, 1])
    with col_b:
        st.image(logo_file, width="stretch")
        st.write("")
        st.caption("✦ No account needed · See your personalized SAT plan in seconds")
        if st.button("✨  Try the Interactive Demo", width="stretch", type="primary", key="guest_demo_btn"):
            guest_resp = process_secure_request(
                "AUTHENTICATE_GUEST", "guest_demo", "", "", {}
            )
            if guest_resp["status"] == "success":
                clear_all_state()
                st.session_state.student_id = "guest_demo"
                st.session_state.session_token = guest_resp["data"]["session_token"]
                st.session_state.logged_in = True
                st.session_state.is_guest = True
                st.session_state.just_logged_in = True
                st.rerun()
            else:
                show_friendly_error(guest_resp.get("message", "Demo initialization failed."))

        st.write("")
        st.divider()

        # --- SIGN IN / REGISTER FORM (below the demo hero) ---
        mode = st.radio("Choose Mode", ["Sign In", "Register"], horizontal=True, label_visibility="collapsed")

        if mode == "Sign In":
            st.subheader("🔑 Student Sign-In")
            login_id_input = st.text_input("Username", placeholder="e.g. smart_fox")
            pin_input = st.text_input("PIN", type="password", placeholder="e.g. 1234")

            st.write("")
            if st.button("Sign In", width="stretch", type="primary", key="sign_in_primary_btn"):
                auth_resp = process_secure_request(
                    "AUTHENTICATE",
                    login_id_input.strip(),
                    "", "",
                    {"student_id": login_id_input.strip(), "pin": pin_input.strip()}
                )
                if auth_resp["status"] == "success":
                    clear_all_state()
                    st.session_state.student_id = login_id_input.strip()
                    st.session_state.session_token = auth_resp["data"]["session_token"]
                    st.session_state.logged_in = True
                    st.session_state.just_logged_in = True
                    st.rerun()
                else:
                    show_friendly_error(auth_resp["message"])
        else:
                st.subheader("📝 Create Account")
                reg_name_input = st.text_input("Your Name", placeholder="e.g. Alex Smith")
                reg_id_input = st.text_input("Choose Username", placeholder="e.g. smart_fox")
                reg_pin_input = st.text_input("Choose PIN", type="password", placeholder="e.g. 4-digit code")

                reg_state = st.selectbox("State", STATES_LIST, index=STATES_LIST.index("WA") if "WA" in STATES_LIST else 0, key="reg_state_code")
                reg_grad_year = st.number_input("Grad Year", min_value=2027, max_value=2035, value=2028, key="reg_grad_year")

                st.write("")
                if st.button("Register & Login", width="stretch", type="primary", key="register_submit_btn"):
                    if not reg_id_input.strip() or not reg_pin_input.strip() or not reg_name_input.strip():
                        show_friendly_error("Please enter Your Name, Username, and PIN.")
                    else:
                        reg_resp = process_secure_request(
                            "REGISTER_STUDENT",
                            reg_id_input.strip(),
                            "", "",
                            {
                                "student_id": reg_id_input.strip(),
                                "pin": reg_pin_input.strip(),
                                "state_code": reg_state,
                                "graduation_year": reg_grad_year,
                                "target_test_date": "",
                                "student_name": reg_name_input.strip()
                            }
                        )
                        if reg_resp["status"] == "success":
                            clear_all_state()
                            st.session_state.student_id = reg_id_input.strip()
                            st.session_state.session_token = reg_resp["data"]["session_token"]
                            st.session_state.logged_in = True
                            st.session_state.just_logged_in = True
                            st.rerun()
                        else:
                            show_friendly_error(reg_resp["message"])
    st.stop()

# Initialize student profile when logged in
if "student_profile" not in st.session_state:
    resp = process_secure_request("GET_STUDENT", _sid(), _tok(), _tok(), {})
    if resp["status"] == "success":
        st.session_state.student_profile = resp["data"]
    else:
        st.session_state.student_profile = {
            "state_code": "WA",
            "graduation_year": 2028,
            "target_test_date": "",
            "student_name": "Student"
        }

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "schedule_summary" not in st.session_state:
    st.session_state.schedule_summary = ""
if "math_summary" not in st.session_state:
    st.session_state.math_summary = ""
if "rw_summary" not in st.session_state:
    st.session_state.rw_summary = ""
if "tutor_summary" not in st.session_state:
    st.session_state.tutor_summary = ""




@st.fragment
def render_narrator_summary(student_id, session_token, active_token, state_code, target_test_date, pacing_strategy, student_name):
    with st.container(border=True):
        with st.spinner("🤖 Writing study guide and practice problems..."):
            sum_resp = process_secure_request(
                "GET_SUMMARIES",
                student_id,
                session_token,
                active_token,
                {
                    "state_code": state_code,
                    "target_test_date": target_test_date,
                    "pacing_strategy": pacing_strategy,
                    "student_name": student_name
                }
            )
            if sum_resp["status"] == "success":
                sum_data = sum_resp.get("data", {})
                st.session_state.schedule_summary = sum_data.get("schedule_summary", "")
                st.session_state.math_summary = sum_data.get("math_summary", "")
                st.session_state.rw_summary = sum_data.get("rw_summary", "")
                st.session_state.tutor_summary = sum_data.get("tutor_summary", "")
                st.rerun()
            else:
                st.error("Could not load AI study guide.")

# --- HEADER ---


# Sidebar content moved to top of file to ensure initial_sidebar_state="collapsed" is respected

# --- MAIN LAYOUT ---
center_col, right_col = st.columns([2.5, 1], gap="large")

if "analytics_data" not in st.session_state:
    analytics_resp = process_secure_request("GET_ANALYTICS", _sid(), _tok(), _tok(), {})
    if analytics_resp["status"] == "success":
        st.session_state.analytics_data = analytics_resp.get("data", {})
    else:
        st.session_state.analytics_data = {}
analytics_data = st.session_state.analytics_data

# Auto-rebuild schedule when a mastery checkbox was just toggled
if st.session_state.get("syllabus_dirty"):
    build_schedule_from_db()
    # Invalidate the three progress-aware narrator summaries so they
    # regenerate with the updated mastered skill count and last/next skill names.
    # Tutor summary is left intact — it depends on time, not mastery.
    st.session_state.schedule_summary = ""
    st.session_state.math_summary     = ""
    st.session_state.rw_summary       = ""
    st.session_state.syllabus_dirty   = False

# Initialize Schedule Data in Session State for Interactive Editing
if "schedule_df" not in st.session_state:
    build_schedule_from_db()

# --- CENTER COLUMN: CORE INTERFACE ---
with center_col:
    logo_file = "logo.webp" if os.path.exists("logo.webp") else None
    st.image(logo_file, width="stretch")
    st.write("")

    s_name = st.session_state.student_profile.get("student_name", "Student")
    hdr_col, btn_col = st.columns([3, 1])
    with hdr_col:
        st.markdown(f"### 🎯 Welcome back, {s_name}!")
    with btn_col:
        with st.popover("👤 Student Profile", use_container_width=True):
            import time as _time
            st.subheader("👤 Student Profile")

            saved_name = st.session_state.student_profile.get("student_name", "Student")
            student_name_input = st.text_input("Name", value=saved_name, key="pop_name")

            col_prof1, col_prof2 = st.columns(2)
            with col_prof1:
                saved_state = st.session_state.student_profile.get("state_code", "WA")
                state_idx = STATES_LIST.index(saved_state) if saved_state in STATES_LIST else 0
                state_code = st.selectbox("State", STATES_LIST, index=state_idx, key="pop_state")
            with col_prof2:
                saved_grad_year = st.session_state.student_profile.get("graduation_year", 2028)
                graduation_year = st.number_input("Grad Year", min_value=2027, max_value=2035, value=int(saved_grad_year), key="pop_grad")

            if st.button("Update my profile", width="stretch", key="pop_update_profile"):
                payload = {
                    "state_code": state_code,
                    "graduation_year": graduation_year,
                    "student_name": student_name_input
                }
                resp = process_secure_request("SAVE_PROFILE", _sid(), _tok(), _tok(), payload)
                if resp["status"] == "success":
                    st.session_state.student_profile["state_code"] = state_code
                    st.session_state.student_profile["graduation_year"] = graduation_year
                    st.session_state.student_profile["student_name"] = student_name_input
                    if "analytics_data" in st.session_state:
                        del st.session_state.analytics_data
                    build_schedule_from_db()
                    st.rerun()
                else:
                    show_friendly_error(resp["message"])

            st.divider()
            st.subheader("📊 Log Test Results")

            date_test_taken = st.date_input("Date", key="pop_date")

            col_sc1, col_sc2 = st.columns(2)
            with col_sc1:
                math_score = st.number_input("Math Score", min_value=160, max_value=800, value=500, step=10, key="pop_math")
            with col_sc2:
                rw_score = st.number_input("RW Score", min_value=160, max_value=800, value=500, step=10, key="pop_rw")

            if st.button("Log Scores", width="stretch", key="pop_log_scores"):
                payload = {
                    "date_test_taken": date_test_taken.strftime("%Y-%m-%d"),
                    "math_score": math_score,
                    "reading_writing_score": rw_score
                }
                resp = process_secure_request("LOG_SCORES", _sid(), _tok(), _tok(), payload)
                if resp["status"] == "success":
                    st.cache_data.clear()
                    if "analytics_data" in st.session_state:
                        del st.session_state.analytics_data
                    build_schedule_from_db()
                    st.success("✅ Scores saved!")
                    _time.sleep(0.75)
                    st.rerun()
                else:
                    show_friendly_error(resp["message"])

            st.divider()
            if st.button("🚪 Sign Out", width="stretch", key="sign_out_btn"):
                if st.session_state.get("is_guest"):
                    process_secure_request("TEARDOWN_GUEST", "guest_demo", _tok(), _tok(), {})
                clear_all_state()
                st.session_state.logged_in = False
                st.session_state.student_id = ""
                st.session_state.session_token = ""
                st.session_state.tamper_token = False
                st.rerun()

    st.write("")


    # ---- 3. NARRATOR GENERATION ----
    # Deferred into tab1 as a fragment so the page and all tabs render
    # instantly.  The fragment runs asynchronously inside the tab and
    # calls st.rerun() when done, making the results available to tab2/tab3.

    # ---- 4. CENTRAL CONTENT AREA ----
    tab1, tab2, tab3, tab4 = st.tabs([
        "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0**🗓️ Test Prep Schedule**\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0|",
        "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0**📐 Mathematics Curriculum**\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0|",
        "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0**📚 Reading and Writing Curriculum**\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0|",
        "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0**💬 Chat with SAT Tutor**\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0"
    ])
    with tab1:
        # Center the control area inside tab1
        col_l, col_mid, col_r = st.columns([0.1, 4.0, 0.1])
        with col_mid:
            # 0. Executive Summary from Narrator Agent.
            # If any summary is missing, kick off the narrator fragment so it
            # loads asynchronously without blocking the rest of the page.
            if not st.session_state.get("schedule_summary") or \
               not st.session_state.get("math_summary") or \
               not st.session_state.get("rw_summary"):
                render_narrator_summary(
                    student_id=_sid(),
                    session_token=_tok(),
                    active_token=_tok(),
                    state_code=st.session_state.student_profile.get("state_code", "WA"),
                    target_test_date=st.session_state.student_profile.get("target_test_date", ""),
                    pacing_strategy=st.session_state.get("pacing_strategy", ""),
                    student_name=st.session_state.student_profile.get("student_name", "Student")
                )
            else:
                narrative = st.session_state.get("schedule_summary", "")
                with st.container(border=True):
                    st.markdown(narrative)

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
                    on_change=clear_date_error
                )
            with row_col2:
                if st.button("Save", width="stretch", key="save_test_date_btn"):
                    date_str = test_date_input.strftime("%Y-%m-%d") if test_date_input else ""
                    save_payload = {
                        "target_test_date": date_str,
                    }
                    save_resp = process_secure_request(
                        "SAVE_TARGET_DATE",
                        _sid(),
                        _tok(),
                        _tok(),
                        save_payload,
                    )
                    if save_resp["status"] == "success":
                        st.session_state.student_profile["target_test_date"] = date_str
                        if "analytics_data" in st.session_state:
                            del st.session_state.analytics_data
                        invalidate_summaries()
                        build_schedule_from_db()
                        st.rerun()
                    else:
                        st.session_state.save_date_error = save_resp["message"]
                        st.rerun()
            with row_col3:
                ics_resp = process_secure_request(
                    "EXPORT_ICS",
                    _sid(),
                    _tok(),
                    _tok(),
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
                            width="stretch",
                            key="dl_ics_btn",
                        )
                else:
                    show_friendly_error(ics_resp["message"])

            if "save_date_error" in st.session_state and st.session_state.save_date_error:
                st.write("")
                st.info(st.session_state.save_date_error)

            if "schedule_error" in st.session_state:
                show_friendly_error(st.session_state.schedule_error)
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
            math_text = st.session_state.get("math_summary", "")
            if not math_text:
                math_text = (
                    "Look through the Math concept list below and check off anything you have already mastered. "
                    "Once checked, that topic is automatically removed from your weekly schedule so you can focus on what is new. "
                    'Not sure whether you know a topic well enough? Click the question mark (?) button next to it for an instant AI explanation. '
                    "You can uncheck any topic at any time to bring it back into your plan."
                )
            st.markdown(math_text)
        process_secure_request(
            "RENDER_SYLLABUS",
            _sid(),
            _tok(),
            _tok(),
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
            rw_text = st.session_state.get("rw_summary", "")
            if not rw_text:
                rw_text = (
                    "Look through the Reading and Writing skill list below and check off anything you have already mastered. "
                    "Once checked, that skill is automatically removed from your weekly schedule so your prep time goes toward what is still new. "
                    'Not sure whether you have truly nailed a skill? Click the question mark (?) button next to it for an instant AI explanation. '
                    "You can uncheck any skill at any time to bring it back into your plan."
                )
            st.markdown(rw_text)
        process_secure_request(
            "RENDER_SYLLABUS",
            _sid(),
            _tok(),
            _tok(),
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
        tutor_text = st.session_state.get("tutor_summary", "")
        if not tutor_text:
            tutor_text = "Not sure how the PSAT or SAT works? In this chat, you can ask any question about the SAT or PSAT exam, rules, curriculum, and scoring. The tutor will answer your questions strictly using information from official College Board documents."
        st.markdown(tutor_text)
        @st.fragment
        def tutor_chat():
            col_input, col_btn = st.columns([5, 1])
            with col_input:
                user_input = st.text_input(
                    "Ask a question",
                    placeholder="Type your question here...",
                    label_visibility="collapsed",
                    key="tutor_input",
                )
            with col_btn:
                send_clicked = st.button("Send", key="tutor_send", use_container_width=True)

            if send_clicked and user_input:
                st.session_state.chat_history.append({"role": "user", "content": user_input})

                with st.spinner("Thinking..."):
                    recent_context = st.session_state.chat_history[-4:]
                    payload = {"message": user_input, "recent_context": recent_context}
                    response = process_secure_request(
                        "TUTOR_CHAT", _sid(), _tok(), _tok(), payload
                    )
                    answer = response.get("data", "Error: Could not reach Tutor Agent.")

                st.session_state.chat_history.append({"role": "assistant", "content": answer})
                st.rerun()

            with st.container(height=400):
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        
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
        header_img = "scr.webp" if os.path.exists("scr.webp") else ""
        if header_img:
            col_img_l, col_img_mid, col_img_r = st.columns([1, 2.5, 1])
            with col_img_mid:
                st.image(header_img, width="stretch")
        else:
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
        
    pred_resp = process_secure_request("CALCULATE_NMSI", _sid(), _tok(), _tok(), {"scores": {"rw": latest_rw, "math": latest_math}})
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
        message = "Follow the preparation schedule, stay consistent, and believe in yourself. Your effort will add up, and your score will improve."
 
    # Render custom combined card
    with st.container(border=True):
        col_pred, col_cut = st.columns(2)
        col_pred.metric("Predicted NMSI Index", f"{pred_nmsi}")
        col_cut.metric(f"{state_code} State Cutoff", f"{state_cutoff}")
        if is_passing:
            st.success(message)
        else:
            st.markdown(f"> **Prep Tip:** {message}")

    # Render Score Simulator
    with st.container(border=True):
        st.subheader("NMSI Index Simulator")
        sim_math = st.slider("Simulated Math Score", min_value=160, max_value=800, value=500, step=10, key="sim_math_slider")
        sim_rw = st.slider("Simulated RW Score", min_value=160, max_value=800, value=500, step=10, key="sim_rw_slider")
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
            st.success("With these scores, you would meet the cutoff!")
        else:
            st.markdown("> **Tip:** Slide the bar to see how PSAT scores affect NMSI Index.")

    # Official Study Resources
    with st.container(border=True):
        st.subheader("Official Study Resources")
        st.link_button(
            "Bluebook Practice",
            "https://bluebook.collegeboard.org/students/practice",
            use_container_width=True,
        )
        st.link_button(
            "Khan Academy SAT Prep",
            "https://www.khanacademy.org/test-prep/digital-sat",
            use_container_width=True,
        )

# All summaries are now loaded lazily inside their respective tabs via st.fragment.

if st.session_state.get("just_logged_in"):
    st.session_state.just_logged_in = False
    st.rerun()
