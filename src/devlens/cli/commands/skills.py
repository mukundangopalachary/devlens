import json

import typer

from devlens.cli.json_contract import emit_json_error, success_response
from devlens.storage.db import SessionLocal
from devlens.storage.repositories.skills import list_skills


def skills_command(
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    session = SessionLocal()
    try:
        skills = list_skills(session)
    except Exception as exc:
        if as_json:
            emit_json_error(
                "skills",
                "skills_failed",
                "Skills command failed.",
                details=str(exc),
            )
        raise
    finally:
        session.close()

    if as_json:
        payload = success_response(
            "skills",
            {
                "skills": [
                    {
                        "name": skill.name,
                        "score": skill.current_score,
                        "confidence": skill.confidence,
                        "category": skill.category,
                        "last_updated_at": skill.last_updated_at.isoformat(),
                    }
                    for skill in skills
                ]
            },
        )
        typer.echo(json.dumps(payload, sort_keys=True, indent=2))
        return

    if not skills:
        typer.echo("No skills recorded yet. Run `devlens analyze <path>` first.")
        return

    for skill in skills:
        typer.echo(
            f"- {skill.name}: score={skill.current_score:.2f}, "
            f"confidence={skill.confidence:.2f}, category={skill.category}"
        )
