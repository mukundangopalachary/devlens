import json

import pytest
import typer

from devlens.cli.commands.feedback import feedback_command
from devlens.cli.commands.tasks import tasks_command


def test_tasks_json_invalid_argument_error_shape(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as exc_info:
        tasks_command(done=1, remove=2, as_json=True)

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["ok"] is False
    assert payload["command"] == "tasks"
    assert payload["errors"][0]["code"] == "invalid_arguments"


def test_feedback_json_invalid_argument_error_shape(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(typer.Exit) as exc_info:
        feedback_command(latest=False, as_json=True)

    assert exc_info.value.exit_code == 1
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["ok"] is False
    assert payload["command"] == "feedback"
    assert payload["errors"][0]["code"] == "invalid_arguments"
