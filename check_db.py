# check_db.py
import sqlite3
import os

DB_PATH = 'student_state.db'

def inspect_database():
    print(f"\n{'='*50}")
    print(" DATABASE DIAGNOSTIC TOOL")
    print(f"{'='*50}")

    if not os.path.exists(DB_PATH):
        print(f"❌ Error: {DB_PATH} does not exist yet.")
        print("You need to run your db_setup.py script first to create it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Check the Schema (What tables and columns exist?)
        print("\n--- 🏗️  DATABASE SCHEMA (TABLE STRUCTURE) ---")
        cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("Database file exists, but it has no tables inside!")
        
        table_names = []
        for table_name, schema in tables:
            table_names.append(table_name)
            print(f"\nTable: {table_name}")
            # Clean up the SQL string for easier reading in the terminal
            clean_schema = schema.replace('\n', ' ').replace('  ', ' ')
            print(f"Blueprint: {clean_schema}")

        # 2. Check the Live Data (What is saved inside?)
        print("\n--- 📊 LIVE DATA ---")
        for table in table_names:
            print(f"\nData inside '{table}':")
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                print("  (Table is empty)")
            else:
                for row in rows:
                    print(f"  {row}")

    except sqlite3.Error as e:
        print(f"\n❌ SQLite Error: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    inspect_database()