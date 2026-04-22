from __future__ import annotations

from datetime import UTC, datetime

from devlens.storage.db import SessionLocal
from devlens.storage.repositories.reporting import build_report_snapshot
from devlens.storage.tables import AnalysisResult, CodeSubmission, FeedbackItem, ScheduledTask


def test_build_report_snapshot_has_useful_summary() -> None:
    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        submission = CodeSubmission(
            project_root="/tmp/project",
            file_path="src/app.py",
            content_hash="abc123",
            code_content="print('hello')",
            source_type="scan",
            created_at=now,
        )
        session.add(submission)
        session.flush()

        analysis = AnalysisResult(
            submission_id=submission.id,
            language="python",
            structural_json="{}",
            llm_json="{}",
            complexity_score=3.0,
            issues_json='{"issues": ["high complexity nesting"]}',
            analysis_version="v1",
            created_at=now,
        )
        session.add(analysis)
        session.flush()

        session.add(
            FeedbackItem(
                analysis_result_id=analysis.id,
                kind="task",
                content="Refactor branching and nesting in this file.",
            )
        )
        session.add(
            ScheduledTask(
                title="Reduce complexity",
                description="Refactor branching and nesting",
                related_file_path="src/app.py",
                priority="high",
                status="done",
                created_at=now,
            )
        )
        snapshot = build_report_snapshot(session, days=30, limit=5)
    finally:
        session.rollback()
        session.close()

    assert int(snapshot["analyses_total"]) >= 1
    assert len(snapshot["analyses_by_day"]) >= 1
    assert len(snapshot["recurring_issue_themes"]) >= 1
    assert len(snapshot["recurring_task_themes"]) >= 1
    task_summary = dict(snapshot["task_summary"])
    assert int(task_summary["total"]) >= 1
    assert "completion_rate" in task_summary
