from streamlit.testing.v1 import AppTest

def test_app_loads_without_errors():
    print("Initializing Streamlit AppTest...")
    at = AppTest.from_file("app.py", default_timeout=15)
    print("Running app...")
    at.run()
    
    print("\n--- BUTTONS DETECTED ---")
    for idx, btn in enumerate(at.button):
        print(f"Index {idx}: {btn.label}")
    print("------------------------")
    
    if at.exception:
        print("\n--- EXCEPTIONS DETECTED ON INITIAL LOAD ---")
        for exc in at.exception:
            print(exc)
        print("---------------------------")
        assert False, "App threw exceptions during initial load!"
        
    print("\n--- SIMULATING USER ACTIONS ---")
    
    # 1. Type a valid custom test date
    import datetime
    print("Setting custom test date to 2027-05-15...")
    at.date_input[1].set_value(datetime.date(2027, 5, 15))
    
    # 2. Click '🔄' button (index 0)
    print("Clicking '🔄'...")
    at.button[0].click().run()
    
    print("UI ERRORS AFTER SAVE:", [err.value for err in at.error])
    print("UI SUCCESS AFTER SAVE:", [succ.value for succ in at.success])
    
    if at.exception:
        print("\n--- EXCEPTIONS DETECTED AFTER SAVE TEST DATE ---")
        for exc in at.exception:
            print(exc)
        print("---------------------------")
        assert False, "App threw exceptions after saving test date!"
        
    print("Test date saved successfully in test. Target test date is now:", at.session_state.student_profile.get("target_test_date"))
    
    # 3. Click 'Update my Schedule' button (now at index 1 for Math, index 2 for R&W)
    print("Clicking Math 'Update my Schedule'...")
    at.button[1].click().run()
    
    print("UI ERRORS AFTER UPDATE:", [err.value for err in at.error])
    
    if at.exception:
        print("\n--- EXCEPTIONS DETECTED AFTER UPDATE SCHEDULE ---")
        for exc in at.exception:
            print(exc)
        print("---------------------------")
        assert False, "App threw exceptions after updating schedule!"
        
    print("Schedule updated successfully!")
    print("--------------------------------")
    
    print("App ran successfully. No exceptions detected.")

if __name__ == "__main__":
    test_app_loads_without_errors()
