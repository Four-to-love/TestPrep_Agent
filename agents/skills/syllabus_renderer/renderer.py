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
        # Header Row (2 columns: Task and Checkbox)
        h1, h2 = st.columns([10, 2])
        h1.markdown(f"### {column_label}")
        h2.markdown("### Mastered")
        st.divider()
        
        # Row Iteration with hierarchy
        chk_idx = 0
        for u_idx, unit in enumerate(data.get("units", [])):
            domain_name = unit.get("domain", "")
            roman_num = ROMAN[u_idx + 1] if u_idx + 1 < len(ROMAN) else str(u_idx + 1)
            # 1. Domain Row (Roman numeral) centered using columns
            col_l, col_mid, col_r = st.columns([2, 8, 2])
            with col_mid:
                st.markdown(f"#### {roman_num}. {domain_name}")
            
            for t_idx, topic in enumerate(unit.get("topics", [])):
                topic_name = topic.get("name", "")
                topic_num = t_idx + 1
                
                # 2. Topic Row (Arabic numeral, indented)
                c1, c2 = st.columns([10, 2])
                indent_topic = "\u00a0\u00a0\u00a0"
                c1.markdown(f"**{indent_topic}{topic_num}. {topic_name}**")
                c2.write("")  # No checkbox for topic header
                
                for s_idx, skill in enumerate(topic.get("granular_skills", [])):
                    skill_num = f"{topic_num}.{s_idx + 1}"
                    full_name = f"{domain_name}: {topic_name} - {skill}"
                    is_mastered = full_name in mastered_topics
                    
                    # 3. Granular Skill Row (Dotted decimal, further indented)
                    c1, c2 = st.columns([10, 2])
                    indent_skill = "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0"
                    if is_mastered:
                        c1.markdown(f"{indent_skill}~~{skill_num} {skill}~~")
                    else:
                        c1.markdown(f"{indent_skill}{skill_num} {skill}")
                    with c2:
                        is_checked = st.checkbox("Mastered", value=is_mastered, key=f"{key_prefix}_{chk_idx}", label_visibility="collapsed")
                        chk_idx += 1
                        if is_checked != is_mastered:
                            process_secure_request(
                                "UPDATE_SYLLABUS", 
                                student_id, 
                                session_token, 
                                active_token, 
                                {"topic": full_name, "is_completed": 1 if is_checked else 0}
                            )
                            st.rerun()

