import typer

from devlens.storage.db import SessionLocal
from devlens.storage.repositories.skills import list_skills


def skills_command() -> None:
    session = SessionLocal()
    try:
        skills = list_skills(session)
    finally:
        session.close()

    if not skills:
        typer.echo("No skills recorded yet. Run `devlens analyze <path>` first.")
        return

    for skill in skills:
        typer.echo(
            f"- {skill.name}: score={skill.current_score:.2f}, "
            f"confidence={skill.confidence:.2f}, category={skill.category}"
        )
