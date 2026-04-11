# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

## Product Name

DevLens

------------------------------------------------------------------------

## 1. Introduction

### 1.1 Purpose

This document provides a detailed description of the requirements for
DevLens, a local system that analyzes developer-written code, evaluates
technical skills, and tracks progression over time.

### 1.2 Scope

DevLens operates entirely on a local machine. It ingests code, performs
analysis, extracts skill signals, and generates feedback and tasks.

### 1.3 Definitions

  Term              Definition
  ----------------- -------------------------------------------
  Skill Graph       Representation of skill levels over time
  Static Analysis   Code inspection without execution
  LLM Analysis      Semantic evaluation using language models
  Task              Generated exercise for improvement
  Feedback          Structured critique

------------------------------------------------------------------------

## 2. Overall Description

### 2.1 Product Perspective

DevLens is a modular system consisting of ingestion, analysis,
evaluation, and feedback components.

### 2.2 Product Functions

-   Code ingestion
-   Static code analysis
-   LLM-based evaluation
-   Skill tracking
-   Feedback generation

### 2.3 User Characteristics

  Attribute     Description
  ------------- ------------------
  User          Single developer
  Skill Level   Intermediate+
  Interface     CLI

### 2.4 Constraints

-   Local-only execution
-   6GB VRAM limit
-   No external APIs

### 2.5 Assumptions

-   Valid code input
-   Regular usage

------------------------------------------------------------------------

## 3. Functional Requirements

### FR1: Code Ingestion

-   FR1.1 System shall detect modified files
-   FR1.2 System shall support manual CLI trigger
-   FR1.3 System shall extract relevant logic

### FR2: Static Analysis

-   FR2.1 System shall parse code into AST
-   FR2.2 System shall detect loops, recursion, nesting
-   FR2.3 System shall estimate complexity indicators

### FR3: LLM Analysis

-   FR3.1 System shall detect algorithmic patterns
-   FR3.2 System shall evaluate optimization quality
-   FR3.3 System shall identify inefficiencies
-   FR3.4 System shall generate reasoning-based critique

### FR4: Skill Tracking

-   FR4.1 System shall map patterns to skills
-   FR4.2 System shall assign level and confidence
-   FR4.3 System shall track historical changes

### FR5: Feedback Generation

-   FR5.1 System shall generate critique
-   FR5.2 System shall generate questions
-   FR5.3 System shall generate tasks

------------------------------------------------------------------------

## 4. Non-Functional Requirements

### 4.1 Performance

-   System shall respond within 10 seconds

### 4.2 Reliability

-   Static analysis must be deterministic

### 4.3 Security

-   System shall not execute user code
-   System shall restrict file access

### 4.4 Maintainability

-   System shall be modular

### 4.5 Scalability

-   System shall support future extensions

------------------------------------------------------------------------

## 5. Data Requirements

### Entities

-   CodeSubmission
-   AnalysisResult
-   Skill
-   SkillHistory

------------------------------------------------------------------------

## 6. Skill Scoring Model

### Inputs

-   Correctness
-   Efficiency
-   Pattern Recognition
-   Code Quality

### Weights

-   Correctness: 0.4
-   Efficiency: 0.3
-   Pattern Recognition: 0.2
-   Code Quality: 0.1

### Update Formula

new_score = previous_score + (current_score - previous_score) \*
learning_rate

------------------------------------------------------------------------

## 7. System Workflow

1.  Trigger analysis
2.  Ingest code
3.  Analyze code
4.  Update skill graph
5.  Generate feedback

------------------------------------------------------------------------

## 8. Error Handling

-   Invalid files skipped
-   Parsing errors logged
-   LLM failures fallback

------------------------------------------------------------------------

## 9. Logging

-   Store analysis logs
-   Maintain audit trail

------------------------------------------------------------------------

## 10. Acceptance Criteria

-   Code analyzed successfully
-   Skills updated correctly
-   Feedback generated

------------------------------------------------------------------------

END OF DOCUMENT
