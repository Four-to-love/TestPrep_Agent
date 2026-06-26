import sqlite3

def check_database():
    print("Opening database vault...")
    # The timeout=5 ensures it throws an error instead of freezing if the DB is locked
    conn = sqlite3.connect('student_state.db', timeout=5)
    c = conn.cursor()

    print("\n--- STUDENT PROFILES ---")
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    for student in students:
        print(student)

    print("\n--- LOGGED SCORES ---")
    c.execute("SELECT * FROM practice_scores")
    scores = c.fetchall()
    for score in scores:
        print(score)

    conn.close()
    print("\nVault closed.")

if __name__ == "__main__":
    check_database()