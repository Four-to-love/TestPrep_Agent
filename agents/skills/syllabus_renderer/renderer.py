# agents/skills/syllabus_renderer/renderer.py
import streamlit as st
import pandas as pd
import json
import os

@st.fragment
def render_expanded_content(topic_val, category, student_id, session_token, active_token):
    with st.spinner("🤖 Writing study guide and practice problems..."):
        from interceptor import process_secure_request
        resp = process_secure_request(
            "EXPAND_TOPIC", 
            student_id, 
            session_token, 
            active_token, 
            {"topic_name": topic_val, "category": category}
        )
    if resp["status"] == "success":
        content = resp["data"] or ""
        # Strip any leading H1/H2/H3 heading the LLM may have added (defensive pass for cached responses)
        lines = content.splitlines()
        while lines and lines[0].lstrip().startswith("#"):
            lines.pop(0)
        while lines and not lines[0].strip():
            lines.pop(0)
        st.markdown("\n".join(lines))
    else:
        st.error("Could not load expansion details.")

@st.fragment
def render_topic_row_fragment(domain_name, topic_name, topic_num, topic_skills, topic_mastered, u_idx, t_idx, key_prefix, student_id, session_token, active_token):
    topic_val = f"{domain_name}: {topic_name}"
    expanded_key = f"exp_state_top_{key_prefix}_{u_idx}_{t_idx}"
    
    if expanded_key not in st.session_state:
        st.session_state[expanded_key] = False
        
    c_indent, c_text, c_expand, c_check = st.columns([0.5, 8.5, 1.0, 2.0])
    with c_text:
        st.markdown(f"**{topic_num}. {topic_name}**")
        if st.session_state[expanded_key]:
            with st.container(border=True):
                with st.chat_message("assistant"):
                    st.markdown(f"**Unit:** {domain_name} &nbsp;|&nbsp; **Topic:** {topic_name}")
                    st.write("")
                    render_expanded_content(
                        topic_val=topic_val,
                        category="math" if key_prefix == "math" else "rw",
                        student_id=student_id,
                        session_token=session_token,
                        active_token=active_token
                    )
                    if st.button("Got it!", key=f"close_top_{key_prefix}_{u_idx}_{t_idx}"):
                        st.session_state[expanded_key] = False
                        st.rerun(scope="fragment")
                        
    with c_expand:
        if st.button("?", key=f"exp_top_{key_prefix}_{u_idx}_{t_idx}", help="Click to get an AI explanation of this topic"):
            st.session_state[expanded_key] = not st.session_state[expanded_key]
            st.rerun(scope="fragment")
            
    with c_check:
        topic_icon = "✅" if topic_mastered else "⬜"
        if st.button(topic_icon, key=f"chk_top_{key_prefix}_{u_idx}_{t_idx}", help="Mastered entire topic"):
            from interceptor import process_secure_request
            new_val = 0 if topic_mastered else 1
            for s_name in topic_skills:
                process_secure_request(
                    "UPDATE_SYLLABUS",
                    student_id,
                    session_token,
                    active_token,
                    {"topic": s_name, "is_completed": new_val}
                )
            st.session_state.syllabus_dirty = True
            st.rerun()

@st.fragment
def render_subtopic_row_fragment(domain_name, topic_name, skill, skill_num, is_mastered, chk_idx, key_prefix, student_id, session_token, active_token):
    full_name = f"{domain_name}: {topic_name} - {skill}"
    expanded_key = f"exp_state_sub_{key_prefix}_{chk_idx}"
    
    if expanded_key not in st.session_state:
        st.session_state[expanded_key] = False
        
    c_indent, c_text, c_expand, c_check = st.columns([1.0, 8.0, 1.0, 2.0])
    with c_text:
        if is_mastered:
            st.markdown(f"~~{skill_num} {skill}~~")
        else:
            st.markdown(f"{skill_num} {skill}")
            
        if st.session_state[expanded_key]:
            with st.container(border=True):
                with st.chat_message("assistant"):
                    st.markdown(f"**Unit:** {domain_name} &nbsp;|&nbsp; **Topic:** {topic_name} &nbsp;|&nbsp; **Subtopic:** {skill}")
                    st.write("")
                    render_expanded_content(
                        topic_val=full_name,
                        category="math" if key_prefix == "math" else "rw",
                        student_id=student_id,
                        session_token=session_token,
                        active_token=active_token
                    )
                    if st.button("Got it!", key=f"close_skill_{key_prefix}_{chk_idx}"):
                        st.session_state[expanded_key] = False
                        st.rerun(scope="fragment")
                        
    with c_expand:
        if st.button("?", key=f"exp_skill_{key_prefix}_{chk_idx}", help="Click to get an AI explanation of this skill"):
            st.session_state[expanded_key] = not st.session_state[expanded_key]
            st.rerun(scope="fragment")
            
    with c_check:
        skill_icon = "✅" if is_mastered else "⬜"
        if st.button(skill_icon, key=f"chk_skill_{key_prefix}_{chk_idx}", help="Mastered skill"):
            from interceptor import process_secure_request
            new_val = 0 if is_mastered else 1
            process_secure_request(
                "UPDATE_SYLLABUS",
                student_id,
                session_token,
                active_token,
                {"topic": full_name, "is_completed": new_val}
            )
            st.session_state.syllabus_dirty = True
            st.rerun()


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
            
            if u_idx > 0:
                st.divider()

            # 1. Domain Row (Roman numeral) centered using columns
            c_l, c_mid, c_check = st.columns([1.5, 8.5, 2.0])
            with c_mid:
                st.markdown(f"### {roman_num}. {domain_name}")
            with c_check:
                # Unit checkmark button
                unit_icon = "✅" if unit_mastered else "⬜"
                if st.button(unit_icon, key=f"chk_unit_{key_prefix}_{u_idx}", help="Mastered entire unit"):
                    new_val = 0 if unit_mastered else 1
                    for s_name in unit_skills:
                        process_secure_request(
                            "UPDATE_SYLLABUS",
                            student_id,
                            session_token,
                            active_token,
                            {"topic": s_name, "is_completed": new_val}
                        )
                    st.session_state.syllabus_dirty = True
                    st.rerun()
            
            for t_idx, topic in enumerate(unit.get("topics", [])):
                topic_name = topic.get("name", "")
                topic_num = t_idx + 1
                topic_val = f"{domain_name}: {topic_name}"
                
                # 2. Collect all granular skill names under this Topic for cascading checks
                topic_skills = [f"{domain_name}: {topic_name} - {s}" for s in topic.get("granular_skills", [])]
                topic_mastered = all(s in mastered_topics for s in topic_skills) if topic_skills else False
                


                # 2. Topic Row (Arabic numeral, indented via column layout)
                render_topic_row_fragment(
                    domain_name=domain_name,
                    topic_name=topic_name,
                    topic_num=topic_num,
                    topic_skills=topic_skills,
                    topic_mastered=topic_mastered,
                    u_idx=u_idx,
                    t_idx=t_idx,
                    key_prefix=key_prefix,
                    student_id=student_id,
                    session_token=session_token,
                    active_token=active_token
                )
                
                for s_idx, skill in enumerate(topic.get("granular_skills", [])):
                    skill_num = f"{topic_num}.{s_idx + 1}"
                    full_name = f"{domain_name}: {topic_name} - {skill}"
                    is_mastered = full_name in mastered_topics
                    
                    # 3. Granular Skill Row (Dotted decimal, further indented via column layout)
                    render_subtopic_row_fragment(
                        domain_name=domain_name,
                        topic_name=topic_name,
                        skill=skill,
                        skill_num=skill_num,
                        is_mastered=is_mastered,
                        chk_idx=chk_idx,
                        key_prefix=key_prefix,
                        student_id=student_id,
                        session_token=session_token,
                        active_token=active_token
                    )
                    chk_idx += 1

