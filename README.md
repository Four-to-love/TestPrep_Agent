
# 🚀 TestPrep_Agent: Autonomous Academic Orchestrator

**TestPrep_Agent** is a multi-agent, Zero-Trust academic planning system designed for the competitive college admissions landscape. By leveraging a modular agentic architecture, it provides personalized, state-aware study timelines that adapt to individual student progress and performance.

---

## 🤖 System Orchestration: The Agentic Core

To achieve true autonomy, `TestPrep_Agent` utilizes a decoupled, three-agent architecture coordinated via a centralized security gateway.

| Agent | Capability | Orchestration Pattern |
| :--- | :--- | :--- |
| **Narrator** | Generates personalized, time-aware study guidance. | **Dynamic Injection:** Context-aware prompting; utilizes dynamic windowing. |
| **SyllabusTutor** | Provides authoritative responses on SAT/PSAT curriculum. | **RAG:** Document-loaded at runtime, token-budgeted, and conversation-history windowed. |
| **TopicExpander** | Creates structured, actionable mini-lessons on demand. | **Cached Generation:** "Cache-First" retrieval to minimize LLM overhead. |

---

## 🛠 Deterministic Skills Layer
Beyond the LLM agents, the system relies on six specialized, deterministic modules to ensure computational accuracy:

*   **Strategy Engine:** Multi-grade adaptive planner; maps grade-level to pacing, test cadence, and focus areas.
*   **Curriculum Mapper:** Dynamically distributes unmastered skills into a week-by-week timeline.
*   **Date Calculator:** Computes critical path milestones (defaults to Sept 15 of junior year).
*   **NMSI Calculator:** Implements state-specific cutoff lookups and proprietary scoring formulas.
*   **Syllabus Renderer:** Interactive state-management component that persists mastery to the DB.
*   **Calendar Export:** RFC 5545-compliant `.ics` generation using only Python standard libraries.

---

## 🛡 The Interceptor Gateway: True Decoupling
What makes this system a production-grade architecture is the **Zero-Trust Interceptor**. 

*   **Decoupled Execution:** Agents operate in total isolation—they do not import each other. 
*   **Centralized Routing:** All communication flows through the Interceptor gateway, which enforces rate limits and validates schema integrity.
*   **Validation & Control:** The Interceptor acts as the single point of truth for input sanitization and payload security.

This pattern mirrors **production-grade microservice architecture**, ensuring that individual agents can be updated, scaled, or replaced without impacting the stability of the core application.


---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Framework** | Streamlit |
| **LLM Orchestration** | Google GenAI SDK |
| **Tooling** | Model Context Protocol (MCP) |
| **Data Validation** | Pydantic / Pydantic-Settings |
| **Authentication** | Bcrypt (Secure Hashing) |
| **Resiliency** | Tenacity (Retry Logic) |


* **Ephemeral Guest Mode:** A secure sandbox environment for demonstration purposes with automated session teardown.


---

## 🚀 Deployment

Built for the Kaggle AI Agents Intensive, this application follows a **secure-first deployment strategy** using Streamlit Community Cloud with runtime secret injection to maintain environment integrity. Credentials are never hardcoded or stored in version control.

---

> *"Built for Precision: Every recommendation is grounded in the College Board Assessment Framework, processed through a Zero-Trust validation layer, and tailored to the student’s specific academic trajectory."*
