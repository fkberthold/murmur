import subprocess
from pathlib import Path


class ClaudeError(Exception):
    """Raised when Claude subprocess fails."""
    pass


def run_claude(
    prompt: str,
    allowed_tools: list[str] | None = None,
    cwd: Path | None = None,
    timeout: int = 600,
    mcp_config: Path | None = None,
) -> str:
    """
    Run Claude CLI in headless mode and return response.

    Args:
        prompt: The prompt to send to Claude
        allowed_tools: Optional list of tools to allow (e.g., ["WebSearch", "mcp__slack__channels_list"])
        cwd: Working directory for subprocess
        timeout: Timeout in seconds (default 10 minutes)
        mcp_config: Path to MCP configuration file (e.g., .mcp.json)

    Returns:
        Claude's response text

    Raises:
        ClaudeError: If subprocess fails
    """
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--setting-sources", "",  # Don't load user/project settings (avoids skills)
    ]

    # Add MCP config if provided
    if mcp_config:
        cmd.extend(["--mcp-config", str(mcp_config)])

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    else:
        # No tools needed - just generate text
        cmd.extend(["--tools", ""])

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise ClaudeError(result.stderr or f"Claude exited with code {result.returncode}")

    return result.stdout
