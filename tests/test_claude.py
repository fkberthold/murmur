import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_run_claude_with_mcp_config():
    """MCP config path should be passed to claude CLI."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        mcp_config = Path("/tmp/test.mcp.json")
        run_claude("test prompt", mcp_config=mcp_config)

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--mcp-config" in cmd
        assert str(mcp_config) in cmd


def test_run_claude_without_mcp_config():
    """When no MCP config, --mcp-config should not be in command."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        run_claude("test prompt")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--mcp-config" not in cmd


def test_run_claude_with_mcp_tools():
    """MCP tools should be included in allowedTools."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        run_claude(
            "test prompt",
            allowed_tools=["mcp__slack__channels_list", "mcp__slack__conversations_history"],
            mcp_config=Path("/tmp/test.mcp.json")
        )

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        tools_arg = cmd[idx + 1]
        assert "mcp__slack__channels_list" in tools_arg
