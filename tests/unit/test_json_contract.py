from devlens.cli.json_contract import CONTRACT_VERSION, error_response, success_response


def test_success_response_shape() -> None:
    payload = success_response("doctor", {"status": "ok"})

    assert payload["ok"] is True
    assert payload["command"] == "doctor"
    assert payload["version"] == CONTRACT_VERSION
    assert payload["data"] == {"status": "ok"}
    assert payload["errors"] == []
    assert isinstance(payload["timestamp"], str)


def test_error_response_shape() -> None:
    payload = error_response("tasks", "task_not_found", "Task missing", details={"id": 99})

    assert payload["ok"] is False
    assert payload["command"] == "tasks"
    assert payload["version"] == CONTRACT_VERSION
    assert payload["data"] == {}
    assert payload["errors"][0]["code"] == "task_not_found"
    assert payload["errors"][0]["message"] == "Task missing"
    assert payload["errors"][0]["details"] == {"id": 99}
