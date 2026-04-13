from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from devlens.analysis.llm.client import analyze_with_llm
from devlens.analysis.static.python_ast import analyze_python_file
from devlens.core.schemas import AnalyzeSummary, FileAnalysisResult, GeneratedFeedback
from devlens.feedback.critique import build_critique
from devlens.feedback.questions import generate_questions
from devlens.feedback.tasks import generate_tasks
from devlens.ingestion.file_scanner import FileScanResult, scan_python_files, scan_specific_files
from devlens.ingestion.git_diff import get_changed_files
from devlens.skills.mistakes import infer_mistake_patterns
from devlens.skills.scorer import score_skills
from devlens.storage.repositories.analyses import (
    create_analysis_result,
    get_latest_analysis_for_submission,
)
from devlens.storage.repositories.feedback import create_feedback_item
from devlens.storage.repositories.knowledge import regenerate_tasks_for_file
from devlens.storage.repositories.skills import upsert_skill_assessment
from devlens.storage.repositories.submissions import (
    create_code_submission,
    get_submission_by_path_and_hash,
)


def run_static_analysis(
    target_path: Path,
    session: Session,
) -> tuple[AnalyzeSummary, list[FileAnalysisResult]]:
    scan_results = scan_python_files(target_path)
    return _run_analysis_for_scan_results(scan_results=scan_results, session=session)


def run_static_analysis_for_changed_files(
    target_path: Path,
    session: Session,
) -> tuple[AnalyzeSummary, list[FileAnalysisResult]]:
    changed_files = get_changed_files(target_path)
    scan_results = scan_specific_files(changed_files)
    return _run_analysis_for_scan_results(scan_results=scan_results, session=session)


def run_static_analysis_for_specific_files(
    file_paths: list[Path],
    session: Session,
) -> tuple[AnalyzeSummary, list[FileAnalysisResult]]:
    scan_results = scan_specific_files(file_paths)
    return _run_analysis_for_scan_results(scan_results=scan_results, session=session)


def _run_analysis_for_scan_results(
    scan_results: list[FileScanResult],
    session: Session,
) -> tuple[AnalyzeSummary, list[FileAnalysisResult]]:
    analyses: list[FileAnalysisResult] = []
    submissions_saved = 0
    analyses_saved = 0
    deduplicated_files = 0

    for scan_result in scan_results:
        existing_submission = get_submission_by_path_and_hash(
            session=session,
            file_path=str(scan_result.relative_path),
            content_hash=scan_result.content_hash,
        )
        if existing_submission is not None:
            existing_analysis = get_latest_analysis_for_submission(
                session=session,
                submission_id=existing_submission.id,
            )
            if existing_analysis is not None:
                deduplicated_files += 1
                continue

        submission = create_code_submission(
            session=session,
            project_root=str(scan_result.project_root),
            file_path=str(scan_result.relative_path),
            content_hash=scan_result.content_hash,
            code_content=scan_result.content,
            source_type=scan_result.source_type,
        )
        submissions_saved += 1

        analysis = analyze_python_file(scan_result)
        llm_result = analyze_with_llm(
            session=session,
            source=scan_result.content,
            metrics=analysis.metrics,
            issues=analysis.issues,
        )
        skill_assessments = score_skills(metrics=analysis.metrics, llm_result=llm_result)
        feedback = GeneratedFeedback(
            critique=build_critique(analysis.metrics, llm_result, analysis.issues),
            questions=generate_questions(analysis.metrics, skill_assessments),
            tasks=generate_tasks(analysis.metrics, skill_assessments),
        )
        analysis.llm_result = llm_result
        analysis.skill_assessments = skill_assessments
        analysis.feedback = feedback
        analyses.append(analysis)

        analysis_row = create_analysis_result(
            session=session,
            submission_id=submission.id,
            language=analysis.language,
            structural_json=json.dumps(analysis.metrics.model_dump(), sort_keys=True),
            llm_json=json.dumps(llm_result.model_dump(), sort_keys=True),
            complexity_score=analysis.metrics.cyclomatic_complexity,
            issues_json=json.dumps(
                {
                    "issues": analysis.issues,
                    "mistake_patterns": infer_mistake_patterns(analysis.metrics),
                },
                sort_keys=True,
            ),
            analysis_version="static-v1",
        )
        analyses_saved += 1

        for assessment in skill_assessments:
            upsert_skill_assessment(session, assessment)

        create_feedback_item(
            session=session,
            analysis_result_id=analysis_row.id,
            kind="critique",
            content=feedback.critique,
        )
        for question in feedback.questions:
            create_feedback_item(
                session=session,
                analysis_result_id=analysis_row.id,
                kind="question",
                content=question,
            )
        for task in feedback.tasks:
            create_feedback_item(
                session=session,
                analysis_result_id=analysis_row.id,
                kind="task",
                content=task,
            )

        regenerate_tasks_for_file(
            session=session,
            file_path=str(scan_result.relative_path),
            task_texts=feedback.tasks,
        )

    session.commit()

    summary = AnalyzeSummary(
        files_scanned=len(scan_results),
        files_analyzed=len(analyses),
        submissions_saved=submissions_saved,
        analyses_saved=analyses_saved,
        skipped_files=0,
        deduplicated_files=deduplicated_files,
        total_complexity=sum(item.metrics.cyclomatic_complexity for item in analyses),
        max_nesting_depth=max((item.metrics.max_nesting_depth for item in analyses), default=0),
        recursion_file_count=sum(1 for item in analyses if item.metrics.recursion_detected),
    )
    return summary, analyses
