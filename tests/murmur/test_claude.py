import pytest
from unittest.mock import patch, MagicMock
from murmur.claude import run_claude, ClaudeError


def test_run_claude_returns_stdout():
    """run_claude should return stdout from subprocess."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Hello from Claude"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_claude("Say hello")
        assert result == "Hello from Claude"

        # Verify subprocess was called correctly
        call_args = mock_run.call_args
        assert "claude" in call_args[0][0]
        assert "--print" in call_args[0][0]


def test_run_claude_raises_on_failure():
    """run_claude should raise ClaudeError on non-zero exit."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error message"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeError, match="Error message"):
            run_claude("Bad prompt")
