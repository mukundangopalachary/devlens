# DEVLENS ARCHITECTURE + PRODUCT TECH BLUEPRINT

## 1. Goal

Build DevLens as local-first, single-user, CLI-first modular monolith optimized for:

- fully offline use
- low setup friction
- deterministic static analysis
- sub-10s analysis target for common flows
- future extension into API/UI without rewrite

---

## 2. Recommended Stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.12 |
| Package Manager | uv |
| CLI | Typer |
| Data Validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Database | SQLite |
| Static Analysis | ast, libcst, radon |
| LLM Runtime | Ollama |
| LLM Class | quantized 7B coder/instruct model |
| Testing | Pytest |
| Lint/Format | Ruff |
| Typing | MyPy |
| Logging | structlog or stdlib logging |
| Optional Later | FastAPI, tree-sitter, Docker, vector store |

---

## 3. Architecture Shape

Use modular monolith.

Flow:

`Typer CLI -> Ingestion -> Static Analysis -> LLM Analysis -> Skill Extraction -> Skill Graph Update -> Feedback Generation -> SQLite`

Rules:

- no HTTP layer in Phase 1
- no multi-service split
- no vector DB in early versions
- no code execution
- file access restricted to allowed project paths

---

## 4. Project Structure

```text
devlens/
  pyproject.toml
  README.md
  .env.example
  alembic.ini
  src/devlens/
    __init__.py
    main.py
    config.py
    logging.py
    cli/
      __init__.py
      app.py
      commands/
        analyze.py
        history.py
        skills.py
        feedback.py
    core/
      models.py
      schemas.py
      enums.py
      errors.py
    ingestion/
      file_scanner.py
      git_diff.py
      boilerplate_filter.py
      chunker.py
    analysis/
      static/
        python_ast.py
        metrics.py
        detectors.py
      llm/
        client.py
        prompts.py
        parser.py
      pipeline.py
    skills/
      taxonomy.py
      scorer.py
      history.py
      mistakes.py
    feedback/
      critique.py
      questions.py
      tasks.py
      formatter.py
    storage/
      db.py
      tables.py
      repositories/
        submissions.py
        analyses.py
        skills.py
        feedback.py
    security/
      path_guard.py
      input_validation.py
    cache/
      result_cache.py
      prompt_cache.py
    observability/
      audit.py
      timers.py
  alembic/
    versions/
  tests/
    unit/
    integration/
    fixtures/
  docs/
```

---

## 5. Core Modules

### 5.1 CLI Layer

Responsibilities:

- manual trigger for analysis
- select target path or git diff scope
- print structured output
- expose history and skills commands

Commands:

- `devlens analyze <path>`
- `devlens analyze --changed`
- `devlens skills`
- `devlens history`
- `devlens feedback --latest`

### 5.2 Ingestion

Responsibilities:

- detect changed files
- filter unsupported files
- restrict analysis to allowed paths
- extract relevant code regions

Inputs:

- filesystem path
- git diff

Outputs:

- normalized code chunks with metadata

### 5.3 Static Analysis

Phase 1 target:

- Python-first support

Signals:

- loops
- recursion
- nesting depth
- branch count
- cyclomatic complexity
- function length
- obvious anti-patterns

Tools:

- `ast` for structure
- `libcst` when source-preserving transforms or exact spans matter
- `radon` for complexity metrics

### 5.4 LLM Analysis

Responsibilities:

- infer algorithmic pattern
- judge optimization quality
- detect reasoning gaps
- produce structured critique

Constraints:

- use small quantized local model
- prefer JSON output contract
- cap prompt size
- fall back gracefully when model fails

### 5.5 Skill Engine

Responsibilities:

- map analysis outputs to skill taxonomy
- compute skill score and confidence
- track repeated mistakes
- update history using smoothing formula

Suggested formula:

`new_score = previous_score + (current_score - previous_score) * learning_rate`

### 5.6 Feedback Generator

Responsibilities:

- generate critique
- generate reasoning questions
- generate targeted tasks

Inputs:

- latest analysis
- historical skill state
- repeated mistake patterns

### 5.7 Storage

Use SQLite first.

Reason:

- single-user local app
- zero external service setup
- enough for current workload
- easy backup and inspection

Use SQLAlchemy repositories so later move to PostgreSQL possible without full rewrite.

---

## 6. Database Blueprint

### 6.1 Tables

#### code_submissions

- `id`
- `created_at`
- `project_root`
- `file_path`
- `content_hash`
- `code_content`
- `source_type` (`filesystem` or `git`)

#### analysis_results

- `id`
- `submission_id`
- `created_at`
- `language`
- `structural_json`
- `llm_json`
- `complexity_score`
- `issues_json`
- `analysis_version`

#### skills

- `id`
- `name`
- `category`
- `current_score`
- `confidence`
- `last_updated_at`

#### skill_history

- `id`
- `skill_id`
- `recorded_at`
- `previous_score`
- `new_score`
- `delta`
- `reason`

#### feedback_items

- `id`
- `analysis_result_id`
- `kind` (`critique`, `question`, `task`)
- `content`
- `difficulty`
- `related_skill`

#### mistake_patterns

- `id`
- `name`
- `description`
- `occurrence_count`
- `last_seen_at`

### 6.2 Indexes

- `code_submissions(file_path, created_at)`
- `analysis_results(submission_id, created_at)`
- `skills(name)`
- `skill_history(skill_id, recorded_at)`
- `feedback_items(analysis_result_id, kind)`

---

## 7. Config Blueprint

Config source order:

1. defaults
2. `.env`
3. CLI flags

Suggested config keys:

- `DEVLENS_DB_URL`
- `DEVLENS_OLLAMA_MODEL`
- `DEVLENS_PROJECT_ROOT`
- `DEVLENS_MAX_FILE_SIZE_KB`
- `DEVLENS_ALLOWED_EXTENSIONS`
- `DEVLENS_LLM_TIMEOUT_SECONDS`
- `DEVLENS_CACHE_ENABLED`
- `DEVLENS_LOG_LEVEL`

---

## 8. Performance Plan

To hit sub-10s target:

- analyze only changed files by default
- hash file contents, skip unchanged work
- split static analysis and LLM pass cleanly
- cache prior LLM outputs by content hash + prompt version
- cap prompt context aggressively
- batch DB writes
- use quantized model only

Target breakdown:

- ingestion: `<1s`
- static analysis: `1-2s`
- LLM pass: `4-6s`
- scoring + storage + feedback: `1-2s`

---

## 9. Security Blueprint

- no execution of user code
- no arbitrary shell generation/execution
- path allowlist around project root
- max file size limit
- extension allowlist
- parse failures logged, not fatal
- LLM output validated before storage

---

## 10. Testing Strategy

### Unit

- AST detectors
- scoring logic
- feedback shaping
- path restrictions

### Integration

- analyze changed files flow
- store and retrieve skill history
- LLM JSON parse fallback path

### Golden Tests

- fixed code snippets map to expected skill signals
- repeated regressions detectable over time

---

## 11. Delivery Phases

### Phase 1

- Python-only ingestion
- manual CLI trigger
- static analysis
- local LLM critique
- SQLite persistence
- skill scoring
- basic feedback output

### Phase 2

- richer task generation
- mistake pattern tracking
- better caching
- history and trends commands

### Phase 3

- multi-language parser adapters
- optional FastAPI layer
- optional dashboard
- optional Docker packaging

---

## 12. Decisions Deferred

Do not decide yet:

- vector DB vendor
- multi-agent architecture
- PostgreSQL migration
- remote sync/cloud features
- real-time file watchers by default

Defer until real bottleneck appears.

---

## 13. Final Recommendation

Build Phase 1 as Python modular monolith with Typer, SQLite, SQLAlchemy, ast/libcst/radon, and Ollama.

This fits product constraints better than FastAPI + PostgreSQL + Docker baseline.

