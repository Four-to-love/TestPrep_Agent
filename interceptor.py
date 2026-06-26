import sqlite3

def verify_session(student_id, session_token, expected_token):
    """
    Zero-Trust Check: Verifies if the incoming request matches the active session token.
    """
    if not session_token or session_token != expected_token:
        return False
    return True

def process_secure_request(action_type, student_id, session_token, active_token, payload):
    """
    The Policy Interceptor: Validates tokens and forces strict data integrity constraints.
    """
    # 1. Identity Verification Check
    if not verify_session(student_id, session_token, active_token):
        return {"status": "error", "message": "Security Violation: Invalid or expired session token. Access Denied."}
    
    conn = sqlite3.connect('student_state.db')
    c = conn.cursor()
    
    try:
        # 2. Least-Privilege Action Routing
        if action_type == "SAVE_PROFILE":
            state_code = payload.get("state_code")
            
            # Simple sanitization validation
            if len(state_code) != 2 or not state_code.isalpha():
                return {"status": "error", "message": "Data Validation Error: Invalid State Code format."}
            
            c.execute("UPDATE students SET state_code = ? WHERE student_id = ?", (state_code.upper(), student_id))
            conn.commit()
            return {"status": "success", "message": f"Policy Interceptor approved and saved state profile: {state_code}"}
            
        elif action_type == "LOG_SCORES":
            math = payload.get("math_score", 0)
            rw = payload.get("reading_writing_score", 0)
            total = math + rw
            test_date = payload.get("test_date")
            
            # Strict boundary enforcement (mitigates Gamification Fraud / Hallucinations)
            if not (200 <= math <= 800) or not (200 <= rw <= 800):
                return {"status": "error", "message": "Data Validation Error: Section scores must be between 200 and 800."}
                
            c.execute('''
                INSERT INTO practice_scores (student_id, test_date, sat_total_score, math_score, reading_writing_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, str(test_date), total, math, rw))
            conn.commit()
            return {"status": "success", "message": f"Policy Interceptor validated and logged scores. Total: {total}"}
            
        else:
            return {"status": "error", "message": f"Unauthorized Action: {action_type} is not a permitted system command."}
            
    except Exception as e:
        return {"status": "error", "message": f"Database Error: {str(e)}"}
    finally:
        conn.close()