import json
import os
from datetime import datetime

# Define the absolute path to ensure we always hit the right file
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(DIR_PATH, "rag_store.json")

def ingest_official_documents():
    print("Starting Multi-Grade Knowledge Base Ingestion Pipeline...")
    
    # The factual ground truth the agents will rely on for temporal reasoning
    knowledge_documents = {
        "metadata": {
            "last_updated": str(datetime.now()),
            "sources": ["College Board Guidelines", "Khan Academy Digital SAT", "Strategic Admissions Pacing"]
        },
        "facts": [
            {
                "topic": "Digital SAT Format",
                "content": "The Digital SAT is 2 hours and 14 minutes long, consisting of two main sections: Reading and Writing, and Math. Both sections are divided into two equal-length modules."
            },
            {
                "topic": "Timeline Calculation Rule",
                "content": "Always calculate the student's current grade and weeks remaining by comparing the current date to their Graduation Year. Spread the workload evenly across the remaining weeks."
            },
            {
                "topic": "Pacing: Grades 8 and 9 (Foundations)",
                "content": "For 8th and 9th graders, the timeline is long (100+ weeks). Focus strictly on foundational math (Heart of Algebra) and reading comprehension. Do not assign full-length SAT practice tests yet. Maximum 2 hours of prep per week."
            },
            {
                "topic": "Pacing: Grade 10 (PSAT/NMSQT Focus)",
                "content": "For 10th graders, the timeline is narrowing. Focus heavily on PSAT preparation. The PSAT/NMSQT serves as the qualifying test for the National Merit Scholarship Program. Assign one practice test every 6 weeks."
            },
            {
                "topic": "Pacing: Grade 11 (Primary SAT Year)",
                "content": "11th grade is the critical testing year. The schedule must be aggressive (3-5 hours per week). Target taking the first official SAT in the spring of 11th grade. Assign practice tests every 3-4 weeks."
            },
            {
                "topic": "Pacing: Grade 12 (Final Retakes)",
                "content": "For 12th graders, time is extremely limited (often less than 16 weeks until college apps are due). Switch to 'Acceleration Protocol'. Focus exclusively on weak areas identified in previous test scores. No foundational review."
            }
        ]
    }
    
    # Write the facts securely to the local JSON store
    with open(STORE_PATH, "w") as f:
        json.dump(knowledge_documents, f, indent=4)
        
    print(f"Success: Multi-Grade Knowledge Base updated and locked at {STORE_PATH}")

if __name__ == "__main__":
    ingest_official_documents()