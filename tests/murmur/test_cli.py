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


def test_cli_generate_dry_run(tmp_path):
    """CLI generate --dry-run should validate without executing."""
    # Create minimal config files
    config_dir = tmp_path / "config"
    graphs_dir = config_dir / "graphs"
    profiles_dir = config_dir / "profiles"
    graphs_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    (config_dir / "news_topics.yaml").write_text("""
topics:
  - name: test
    query: "test query"
    priority: high
""")

    (profiles_dir / "default.yaml").write_text("""
name: default
graph: full
config:
  news_topics_file: news_topics.yaml
""")

    (graphs_dir / "full.yaml").write_text("""
name: full
nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics
""")

    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["generate", "--dry-run"])
        assert result.exit_code == 0
        assert "Would execute" in result.stdout or "Validation" in result.stdout or "validated" in result.stdout.lower()
    finally:
        os.chdir(old_cwd)
