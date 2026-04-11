# SYSTEM DESIGN DOCUMENT

## Product Name

DevLens

---

## 1. Overview

DevLens is a local-first system designed to analyze developer-written code, evaluate technical skills, track progression over time, and generate structured feedback and tasks.

The system follows a modular architecture with clear separation between ingestion, analysis, evaluation, and feedback layers.

---

## 2. High-Level Architecture

Pipeline:

Code Input → Ingestion → Static Analysis → LLM Analysis → Skill Extraction → Skill Graph → Feedback Generation → Output

---

## 3. Component Design

### 3.1 Ingestion Service

**Responsibilities:**

- Detect modified or new files
- Support manual CLI trigger
- Extract relevant code segments (ignore boilerplate)

**Inputs:**

- File system / Git diff

**Outputs:**

- Cleaned code chunks

---

### 3.2 Static Analysis Service

**Responsibilities:**

- Parse code into AST
- Detect:
  - loops
  - recursion
  - nesting depth
- Estimate complexity indicators

**Tech Options:**

- Python: ast module
- Java: JavaParser

**Outputs:**

- Structural metadata

---

### 3.3 LLM Analysis Service

**Responsibilities:**

- Identify algorithmic patterns
- Evaluate optimization
- Detect inefficiencies
- Generate reasoning-based critique

**Model:**

- Qwen2.5-Coder via Ollama

**Outputs:**

- Semantic analysis

---

### 3.4 Skill Extraction Engine

**Responsibilities:**

- Map analysis results to skill categories
- Assign:
  - skill level
  - confidence score
- Detect recurring mistakes

**Output Format:**
JSON-like structured data

---

### 3.5 Skill Graph Manager

**Responsibilities:**

- Maintain skill state over time
- Track:
  - progression
  - regression
  - consistency

**Storage:**

- PostgreSQL

---

### 3.6 Feedback Generator

**Responsibilities:**

- Generate:
  - code critique
  - reasoning questions
  - targeted tasks
- Use:
  - current analysis
  - historical skill data

---

## 4. Data Design

### 4.1 Core Tables

#### CodeSubmissions

- id
- timestamp
- file_path
- code_content

#### AnalysisResults

- id
- submission_id
- patterns_detected
- complexity
- issues

#### Skills

- id
- name
- level
- confidence

#### SkillHistory

- id
- skill_id
- timestamp
- delta

#### Tasks

- id
- description
- related_skill
- difficulty

---

## 5. System Workflow

1. User triggers analysis (CLI)
2. Ingestion service collects new code
3. Static analysis extracts structure
4. LLM performs semantic evaluation
5. Skill extraction maps results to skills
6. Skill graph is updated
7. Feedback is generated
8. Results are stored

---

## 6. Agent Loop (Core Logic)

Observe → Analyze → Extract → Update → Generate → Store

---

## 7. Deployment Design

### 7.1 Local Setup

- Runs entirely on local machine
- Uses Docker Compose (optional)

### 7.2 Services

- LLM runtime (Ollama)
- Backend service (FastAPI)
- Database (PostgreSQL)

---

## 8. Security Design

- No execution of user code
- Restricted file access (project directory only)
- No arbitrary shell commands from LLM
- Input validation for all processing

---

## 9. Performance Considerations

- Use quantized models (Q4)
- Cache embeddings and results
- Avoid reprocessing unchanged files
- Batch operations where possible

---

## 10. Future Extensions

- Multi-agent system (planner, critic)
- Vector database integration (RAG)
- UI dashboard
- Multi-language support

---

END OF DOCUMENT
