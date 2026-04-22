"""Tests for scoped retrieval path matching fixes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from devlens.chat.service import _normalize_file_scope


class TestNormalizeFileScope:
    """Test _normalize_file_scope returns valid partial path for matching."""

    def test_none_returns_none(self) -> None:
        assert _normalize_file_scope(None, Path("/project")) is None

    def test_empty_returns_none(self) -> None:
        assert _normalize_file_scope("", Path("/project")) is None

    def test_whitespace_returns_none(self) -> None:
        assert _normalize_file_scope("   ", Path("/project")) is None

    def test_at_prefix_stripped(self) -> None:
        result = _normalize_file_scope("@src/main.py", Path("/project"))
        assert result is not None
        assert "src/main.py" in result

    def test_relative_path(self) -> None:
        result = _normalize_file_scope("src/devlens/main.py", Path("/project"))
        assert result is not None
        assert "main.py" in result

    def test_basename_path(self) -> None:
        result = _normalize_file_scope("main.py", Path("/project"))
        assert result is not None
        assert "main.py" in result


class TestRetrievalSessionIdPreserved:
    """Test that session_id is not dropped when scope is set."""

    def test_session_id_kept_with_scope(self) -> None:
        """answer_question_scoped should pass session_id even when file_path is set."""
        from devlens.chat.service import answer_question_scoped

        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_session.execute.return_value.all.return_value = []

        with (
            patch(
                "devlens.chat.service.retrieve_relevant_chunks",
                return_value=[],
            ) as mock_retrieve,
            patch("devlens.chat.service.list_recent_messages", return_value=[]),
            patch(
                "devlens.chat.service.build_session_memory_summary",
                return_value="no context",
            ),
            patch("devlens.chat.service.get_cached_response", return_value=None),
            patch("devlens.chat.service.ollama") as mock_ollama,
            patch("devlens.chat.service.add_chat_message"),
            patch("devlens.chat.service._refresh_session_memory_summary"),
        ):
            mock_ollama.chat.return_value = {
                "message": {"content": "test reply"},
            }
            mock_session.commit = MagicMock()

            reply, debug = answer_question_scoped(
                mock_session,
                session_id=42,
                question="test",
                file_path="src/main.py",
                debug_retrieval=False,
            )

            # Verify session_id was passed (not None)
            call_kwargs = mock_retrieve.call_args
            assert call_kwargs is not None
            assert call_kwargs.kwargs.get("session_id") == 42
