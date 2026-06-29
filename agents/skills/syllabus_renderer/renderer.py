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
    container styled via CSS class markers.
    """
    from interceptor import process_secure_request
    # 1. Fetch latest mastered topics from database
    progress_resp = process_secure_request("GET_SYLLABUS", student_id, session_token, active_token, {})
    mastered_topics = progress_resp.get("data", []) if progress_resp.get("status") == "success" else []
    
    # 2. Build syllabus DataFrame
    df = build_syllabus_df(syllabus_file, mastered_topics)
    
    if df.empty:
        st.warning(f"Could not load syllabus data from {syllabus_file}")
        return

    # 3. Render container
    with st.container(border=True):
        st.markdown(f'<div class="{marker_class}" style="display:none;">{key_prefix}</div>', unsafe_allow_html=True)
        
        # Header Row (2 columns: Task and Checkbox)
        h1, h2 = st.columns([10, 2])
        h1.markdown(f"<div class='timeline-header'>{column_label}</div>", unsafe_allow_html=True)
        h2.markdown("<div class='timeline-header'>Mastered</div>", unsafe_allow_html=True)
        
        # Row Iteration
        for idx, row in df.iterrows():
            c1, c2 = st.columns([10, 2])
            style = "color: black; text-decoration: line-through;" if row['Mastered'] else "color: black;"
            
            c1.markdown(f"<div class='timeline-grid' data-mastered='{'true' if row['Mastered'] else 'false'}'><span style='{style}'>{row['Combined_Task']}</span></div>", unsafe_allow_html=True)
            
            with c2:
                is_checked = st.checkbox("Mastered", value=row['Mastered'], key=f"{key_prefix}_{idx}", label_visibility="collapsed")
                if is_checked != row['Mastered']:
                    topic_val = row['_full_name']
                    process_secure_request(
                        "UPDATE_SYLLABUS", 
                        student_id, 
                        session_token, 
                        active_token, 
                        {"topic": topic_val, "is_completed": 1 if is_checked else 0}
                    )
                    st.rerun()
