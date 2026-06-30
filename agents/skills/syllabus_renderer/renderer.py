# agents/skills/syllabus_renderer/renderer.py
import streamlit as st
import pandas as pd
import json
import os

def build_syllabus_df(file_path, mastered_topics):
    """
    Parses a syllabus JSON file and builds a DataFrame formatted for the timeline,
    marking mastered tasks based on database state.
    """
    if not os.path.isabs(file_path):
        # Resolve relative to project root or skill directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        file_path = os.path.join(base_dir, file_path)

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Combined_Task", "Mastered", "_full_name"])

    rows = []
    for unit in data.get("units", []):
        unit_name = unit.get("domain", "")
        for topic in unit.get("topics", []):
            topic_name = topic.get("name", "")
            for skill in topic.get("granular_skills", []):
                full_name = f"{unit_name}: {topic_name} - {skill}"
                rows.append({
                    "Combined_Task": full_name,
                    "Mastered": full_name in mastered_topics,
                    "_full_name": full_name  # Hidden field for API
                })
    return pd.DataFrame(rows)

def render_syllabus_timeline(syllabus_file, marker_class, key_prefix, student_id, session_token, active_token, column_label="Task"):
    """
    Renders an interactive timeline grid for the syllabus, wrapping it in a bordered
    container styled via CSS class markers. Shows tasks in a hierarchical format.
    """
    from interceptor import process_secure_request
    
    if not os.path.isabs(syllabus_file):
        # Resolve relative to project root or skill directory
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        syllabus_file = os.path.join(base_dir, syllabus_file)

    try:
        with open(syllabus_file, "r") as f:
            data = json.load(f)
    except Exception:
        st.warning(f"Could not load syllabus data from {syllabus_file}")
        return

    # Fetch latest mastered topics from database
    progress_resp = process_secure_request("GET_SYLLABUS", student_id, session_token, active_token, {})
    mastered_topics = progress_resp.get("data", []) if progress_resp.get("status") == "success" else []
    
    ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

    # Render container
    with st.container(border=True):
        expanded_key = f"expanded_topic_{key_prefix}"

        # Row Iteration with hierarchy
        chk_idx = 0
        for u_idx, unit in enumerate(data.get("units", [])):
            domain_name = unit.get("domain", "")
            roman_num = ROMAN[u_idx + 1] if u_idx + 1 < len(ROMAN) else str(u_idx + 1)
            
            # 1. Collect all granular skill names under this Unit for cascading checks
            unit_skills = []
            for topic in unit.get("topics", []):
                for skill in topic.get("granular_skills", []):
                    unit_skills.append(f"{domain_name}: {topic.get('name', '')} - {skill}")
            unit_mastered = all(s in mastered_topics for s in unit_skills) if unit_skills else False
            
            # 1. Domain Row (Roman numeral) centered using columns
            c_l, c_mid, c_check = st.columns([1.5, 8.5, 2.0])
            with c_mid:
                st.markdown(f"### {roman_num}. {domain_name}")
            with c_check:
                # Unit checkmark button
                unit_icon = "✅" if unit_mastered else "⬜"
                if st.button(unit_icon, key=f"chk_unit_{key_prefix}_{u_idx}", help="Toggle entire unit"):
                    new_val = 0 if unit_mastered else 1
                    for s_name in unit_skills:
                        process_secure_request(
                            "UPDATE_SYLLABUS", 
                            student_id, 
                            session_token, 
                            active_token, 
                            {"topic": s_name, "is_completed": new_val}
                        )
                    st.rerun()
            
            for t_idx, topic in enumerate(unit.get("topics", [])):
                topic_name = topic.get("name", "")
                topic_num = t_idx + 1
                
                # 2. Collect all granular skill names under this Topic for cascading checks
                topic_skills = [f"{domain_name}: {topic_name} - {s}" for s in topic.get("granular_skills", [])]
                topic_mastered = all(s in mastered_topics for s in topic_skills) if topic_skills else False
                
                # 2. Topic Row (Arabic numeral, indented via column layout)
                c_indent, c_text, c_expand, c_check = st.columns([0.5, 8.5, 1.0, 2.0])
                c_text.markdown(f"**{topic_num}. {topic_name}**")
                
                topic_val = f"{domain_name}: {topic_name}"
                with c_expand:
                    if st.button("🔍", key=f"exp_top_{key_prefix}_{u_idx}_{t_idx}", help="Click to expand details"):
                        if st.session_state.get(expanded_key) == topic_val:
                            del st.session_state[expanded_key]
                        else:
                            st.session_state[expanded_key] = topic_val
                        st.rerun()
                with c_check:
                    # Topic checkmark button
                    topic_icon = "✅" if topic_mastered else "⬜"
                    if st.button(topic_icon, key=f"chk_top_{key_prefix}_{u_idx}_{t_idx}", help="Toggle entire topic"):
                        new_val = 0 if topic_mastered else 1
                        for s_name in topic_skills:
                            process_secure_request(
                                "UPDATE_SYLLABUS", 
                                student_id, 
                                session_token, 
                                active_token, 
                                {"topic": s_name, "is_completed": new_val}
                            )
                        st.rerun()
                
                # Render inline details card for Topic if active
                if st.session_state.get(expanded_key) == topic_val:
                    with st.container(border=True):
                        with st.chat_message("assistant", avatar="🔍"):
                            col_t, col_c = st.columns([10, 1])
                            if col_c.button("✖", key=f"close_top_{key_prefix}_{u_idx}_{t_idx}"):
                                del st.session_state[expanded_key]
                                st.rerun()
                            
                            resp = process_secure_request("EXPAND_TOPIC", student_id, session_token, active_token, {"topic_name": topic_val, "category": "math" if key_prefix == "math" else "rw"})
                            if resp["status"] == "success":
                                st.markdown(resp["data"])
                            else:
                                st.error("Could not load expansion details.")
                
                for s_idx, skill in enumerate(topic.get("granular_skills", [])):
                    skill_num = f"{topic_num}.{s_idx + 1}"
                    full_name = f"{domain_name}: {topic_name} - {skill}"
                    is_mastered = full_name in mastered_topics
                    
                    # 3. Granular Skill Row (Dotted decimal, further indented via column layout)
                    c_indent, c_text, c_expand, c_check = st.columns([1.0, 8.0, 1.0, 2.0])
                    if is_mastered:
                        c_text.markdown(f"~~{skill_num} {skill}~~")
                    else:
                        c_text.markdown(f"{skill_num} {skill}")
                    
                    with c_expand:
                        if st.button("🔍", key=f"exp_skill_{key_prefix}_{chk_idx}", help="Click to expand details"):
                            if st.session_state.get(expanded_key) == full_name:
                                del st.session_state[expanded_key]
                            else:
                                st.session_state[expanded_key] = full_name
                            st.rerun()
                            
                    with c_check:
                        # Granular Skill checkmark button
                        skill_icon = "✅" if is_mastered else "⬜"
                        if st.button(skill_icon, key=f"chk_skill_{key_prefix}_{chk_idx}", help="Toggle skill"):
                            new_val = 0 if is_mastered else 1
                            process_secure_request(
                                "UPDATE_SYLLABUS", 
                                student_id, 
                                session_token, 
                                active_token, 
                                {"topic": full_name, "is_completed": new_val}
                            )
                            st.rerun()
                        chk_idx += 1
                            
                    # Render inline details card for Subtopic if active
                    if st.session_state.get(expanded_key) == full_name:
                        with st.container(border=True):
                            with st.chat_message("assistant", avatar="🔍"):
                                col_t, col_c = st.columns([10, 1])
                                if col_c.button("✖", key=f"close_skill_{key_prefix}_{chk_idx}"):
                                    del st.session_state[expanded_key]
                                    st.rerun()
                                
                                resp = process_secure_request("EXPAND_TOPIC", student_id, session_token, active_token, {"topic_name": full_name, "category": "math" if key_prefix == "math" else "rw"})
                                if resp["status"] == "success":
                                    st.markdown(resp["data"])
                                else:
                                    st.error("Could not load expansion details.")

