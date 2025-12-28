from typer.testing import CliRunner
from murmur.cli import app

runner = CliRunner()


def test_cli_help():
    """CLI should show help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "murmur" in result.stdout.lower() or "generate" in result.stdout.lower()


def test_cli_list_transformers():
    """CLI should list available transformers."""
    result = runner.invoke(app, ["list", "transformers"])
    assert result.exit_code == 0
    assert "news-fetcher" in result.stdout
