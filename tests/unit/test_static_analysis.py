from pathlib import Path

from devlens.analysis.static.python_ast import analyze_python_file
from devlens.ingestion.file_scanner import FileScanResult


def test_analyze_python_file_detects_recursion_and_loop() -> None:
    scan_result = FileScanResult(
        project_root=Path("/tmp/project"),
        file_path=Path("/tmp/project/demo.py"),
        relative_path=Path("demo.py"),
        content_hash="abc123",
        size_bytes=10,
        content=(
            "def fact(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    for i in range(n):\n"
            "        pass\n"
            "    return n * fact(n - 1)\n"
        ),
    )

    result = analyze_python_file(scan_result)

    assert result.metrics.function_count == 1
    assert result.metrics.loop_count == 1
    assert result.metrics.recursion_detected is True
    assert "Recursion detected." in result.issues
