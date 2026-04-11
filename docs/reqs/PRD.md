# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Product Name

**DevLens**

---

## 1. Overview

### 1.1 Purpose

DevLens is a fully local application designed designed to analyze a developer’s daily coding activity, evaluate technical competency, track skill progression over time, and generate targeted feedback, questions, and tasks.

### 1.2 Vision

To build a self-evolving AI system that models a developer’s technical abilities and actively improves them through continuous evaluation and adaptive task generation.

### 1.3 Goals

* Accurately analyze user-written code
* Identify patterns, mistakes, and optimization gaps
* Maintain a structured skill graph
* Generate actionable feedback and learning tasks
* Operate entirely on local infrastructure

---

## 2. Scope

### 2.1 In Scope

* Local code ingestion (files / Git)
* Static + LLM-based code analysis
* Skill extraction and tracking
* Feedback generation (critique, questions, tasks)
* Local database storage
* CLI-based interaction

### 2.2 Out of Scope (Phase 1–3)

* Multi-user support
* Cloud deployment
* Real-time monitoring
* UI dashboards
* Code execution sandboxing

---

## 3. Users

| User Type    | Description                           |
| ------------ | ------------------------------------- |
| Primary User | Single developer (local system owner) |

---

## 4. Functional Requirements

### FR1 — Code Ingestion

| ID    | Description                                 | Priority |
| ----- | ------------------------------------------- | -------- |
| FR1.1 | Detect new or modified files                | High     |
| FR1.2 | Support manual trigger via CLI              | High     |
| FR1.3 | Extract relevant logic (ignore boilerplate) | Medium   |

---

### FR2 — Static Code Analysis

| ID    | Description                       | Priority |
| ----- | --------------------------------- | -------- |
| FR2.1 | Parse AST for supported languages | High     |
| FR2.2 | Detect loops, recursion, nesting  | High     |
| FR2.3 | Estimate complexity indicators    | Medium   |

---

### FR3 — LLM-Based Analysis

| ID    | Description                          | Priority |
| ----- | ------------------------------------ | -------- |
| FR3.1 | Detect algorithmic patterns          | High     |
| FR3.2 | Evaluate optimization quality        | High     |
| FR3.3 | Identify mistakes and inefficiencies | High     |
| FR3.4 | Provide reasoning-based critique     | High     |

---

### FR4 — Skill Extraction

| ID    | Description                           | Priority |
| ----- | ------------------------------------- | -------- |
| FR4.1 | Map code patterns to skill categories | High     |
| FR4.2 | Assign skill level and confidence     | High     |
| FR4.3 | Track recurring mistakes              | High     |

---

### FR5 — Skill Graph Management

| ID    | Description                       | Priority |
| ----- | --------------------------------- | -------- |
| FR5.1 | Maintain skill levels over time   | High     |
| FR5.2 | Track improvement trends          | High     |
| FR5.3 | Store historical performance data | High     |

---

### FR6 — Feedback Generation

| ID    | Description                  | Priority |
| ----- | ---------------------------- | -------- |
| FR6.1 | Generate code critique       | High     |
| FR6.2 | Generate reasoning questions | High     |
| FR6.3 | Generate targeted tasks      | High     |

---

### FR7 — Data Storage

| ID    | Description            | Priority |
| ----- | ---------------------- | -------- |
| FR7.1 | Store code submissions | High     |
| FR7.2 | Store analysis results | High     |
| FR7.3 | Store skill graph data | High     |

---

## 5. Non-Functional Requirements

| Category    | Requirement                               |
| ----------- | ----------------------------------------- |
| Performance | Response time < 10 seconds per analysis   |
| Reliability | Deterministic static analysis             |
| Scalability | Modular architecture for future expansion |
| Security    | No arbitrary code execution               |
| Privacy     | Fully local, no external API calls        |

---

## 6. Skill Taxonomy (Initial)

### 6.1 DSA Skills

* Arrays
* Sliding Window
* Two Pointers
* Prefix Sum
* Recursion
* Backtracking
* Dynamic Programming
* Graphs
* Greedy

### 6.2 Engineering Skills

* Code Readability
* Modularity
* Edge Case Handling
* Optimization Thinking
* Debugging Approach

---

## 7. System Workflow

1. User triggers analysis
2. System ingests new code
3. Static analyzer extracts structural features
4. LLM analyzes semantic quality
5. Skill extraction engine updates skill graph
6. Feedback generator produces output
7. Data stored for future reference

---

## 8. Success Metrics

| Metric      | Description                    |
| ----------- | ------------------------------ |
| Accuracy    | Correct pattern detection rate |
| Consistency | Reduction in repeated mistakes |
| Improvement | Skill progression over time    |
| Engagement  | Daily usage consistency        |

---

## 9. Risks & Mitigations

| Risk                    | Mitigation                       |
| ----------------------- | -------------------------------- |
| LLM hallucination       | Combine with static analysis     |
| Poor embeddings         | Use tested embedding models      |
| Overfitting to patterns | Maintain diverse task generation |

---

## 10. Future Enhancements

* Multi-agent architecture (planner, critic)
* UI dashboard
* Advanced RAG with vector DB
* Multi-language support
* Code execution validation

---

## 11. Tech Stack (Initial)

| Layer         | Technology                                |
| ------------- | ----------------------------------------- |
| Runtime       | Python 3.12                               |
| CLI           | Typer                                     |
| LLM           | Ollama + quantized coder model (7B class) |
| Database      | SQLite + SQLAlchemy                       |
| Migrations    | Alembic                                   |
| Static Analysis | ast / libcst / radon                    |
| Tooling       | uv + Ruff + Pytest + MyPy                 |
| Orchestration | None for Phase 1 (Docker optional later)  |

---

## 12. Assumptions

* User writes code daily
* System runs on a machine with GPU support
* User interacts via CLI initially

---

## 13. Constraints

* Limited GPU memory (6GB VRAM)
* Fully offline operation
* Single-user environment

---

## 14. Definition of Done

* System successfully analyzes code
* Skill graph updates correctly
* Feedback is generated consistently
* Runs locally without external dependencies

---

END OF DOCUMENT
