---
name: syllabus-renderer
description: Renders interactive, styled grid-based syllabus tables in Streamlit, synchronizing checkbox progress with the sqlite database.
---
# Syllabus Renderer Skill

This skill provides an interactive timeline table component for displaying SAT syllabus materials (such as Math or Reading & Writing). It parses the syllabus JSON models, matches completed subtasks against user history in the database, and exposes them in a clean, fully responsive Streamlit grid.

## Core Features
1. **Dynamic JSON Schema Processing**: Automatically maps units, tasks, and granular subtasks.
2. **Database Syncing**: Monitors `GET_SYLLABUS` and `UPDATE_SYLLABUS` requests dynamically on click to update progress tables.
3. **Adaptive UI Layout**: Restructures standard Streamlit columns to support cell wrapping, preventing horizontal scrollbars on smaller screens.
