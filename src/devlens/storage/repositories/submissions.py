from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from devlens.storage.tables import CodeSubmission


def create_code_submission(
    session: Session,
    project_root: str,
    file_path: str,
    content_hash: str,
    code_content: str,
    source_type: str,
) -> CodeSubmission:
    submission = CodeSubmission(
        project_root=project_root,
        file_path=file_path,
        content_hash=content_hash,
        code_content=code_content,
        source_type=source_type,
    )
    session.add(submission)
    session.flush()
    return submission


def get_submission_by_path_and_hash(
    session: Session,
    file_path: str,
    content_hash: str,
) -> CodeSubmission | None:
    statement = (
        select(CodeSubmission)
        .where(
            CodeSubmission.file_path == file_path,
            CodeSubmission.content_hash == content_hash,
        )
        .order_by(CodeSubmission.created_at.desc())
    )
    return session.execute(statement).scalars().first()
