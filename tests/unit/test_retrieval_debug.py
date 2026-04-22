from __future__ import annotations

from devlens.storage.repositories.knowledge import _debug_reason
from devlens.storage.repositories.reporting import _extract_text_themes


def test_debug_reason_includes_matched_terms_when_present() -> None:
    reason = _debug_reason(["complex", "nesting"], 0.81, "src/a.py", 2)
    assert "matched terms" in reason
    assert "src/a.py#chunk2" in reason


def test_extract_text_themes_has_keyword_groups() -> None:
    themes = _extract_text_themes("Please refactor this long function and reduce nesting")
    assert "complexity" in themes or "function_size" in themes
