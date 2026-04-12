from __future__ import annotations

from devlens.health import collect_health_report


def doctor_command() -> None:
    report = collect_health_report()
    for line in report:
        print(line)
