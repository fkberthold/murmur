from pathlib import Path

import typer
import yaml
from rich import print as rprint

from murmur.executor import GraphExecutor
from murmur.graph import load_graph, validate_graph
from murmur.registry import TransformerRegistry
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.piper_synthesizer import PiperSynthesizer
from murmur.transformers.script_generator import ScriptGenerator

app = typer.Typer(help="Murmur: A personal intelligence briefing system")
list_app = typer.Typer(help="List available resources")
app.add_typer(list_app, name="list")


def get_registry() -> TransformerRegistry:
    """Build and return the transformer registry."""
    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)
    registry.register(ScriptGenerator)
    registry.register(PiperSynthesizer)
    return registry


def load_profile(name: str) -> dict:
    """Load a profile configuration."""
    profile_path = Path("config/profiles") / f"{name}.yaml"
    with open(profile_path) as f:
        return yaml.safe_load(f)


def load_config(profile: dict) -> dict:
    """Load and resolve config values from profile."""
    config = profile.get("config", {}).copy()

    # Load news topics if referenced
    if "news_topics_file" in config:
        topics_path = Path("config") / config["news_topics_file"]
        with open(topics_path) as f:
            topics_data = yaml.safe_load(f)
            config["news_topics"] = topics_data.get("topics", [])

    # Set defaults
    config.setdefault("output_dir", "output")

    return config


@list_app.command("transformers")
def list_transformers():
    """List available transformers."""
    registry = get_registry()
    rprint("[bold]Available Transformers:[/bold]\n")
    for name in sorted(registry.list_all()):
        transformer = registry.get(name)
        rprint(f"  [cyan]{name}[/cyan]")
        rprint(f"    inputs:  {transformer.inputs}")
        rprint(f"    outputs: {transformer.outputs}")
        rprint()


@list_app.command("graphs")
def list_graphs():
    """List available graphs."""
    graphs_dir = Path("config/graphs")
    if not graphs_dir.exists():
        rprint("[yellow]No graphs directory found[/yellow]")
        return

    rprint("[bold]Available Graphs:[/bold]\n")
    for path in sorted(graphs_dir.glob("*.yaml")):
        rprint(f"  [cyan]{path.stem}[/cyan]")


@list_app.command("profiles")
def list_profiles():
    """List available profiles."""
    profiles_dir = Path("config/profiles")
    if not profiles_dir.exists():
        rprint("[yellow]No profiles directory found[/yellow]")
        return

    rprint("[bold]Available Profiles:[/bold]\n")
    for path in sorted(profiles_dir.glob("*.yaml")):
        rprint(f"  [cyan]{path.stem}[/cyan]")


@app.command()
def generate(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile to use"),
    graph_override: str = typer.Option(None, "--graph", "-g", help="Override graph from profile"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Validate without executing"),
    cached: str = typer.Option(None, "--cached", help="Comma-separated nodes to load from cache"),
    run_id: str = typer.Option(None, "--run", help="Run ID for cached artifacts"),
):
    """Generate a briefing."""
    # Load profile and config
    profile_data = load_profile(profile)
    config = load_config(profile_data)

    # Determine graph
    graph_name = graph_override or profile_data.get("graph", "full")
    graph_path = Path("config/graphs") / f"{graph_name}.yaml"
    graph = load_graph(graph_path)

    # Build registry
    registry = get_registry()

    # Validate
    try:
        validate_graph(graph, registry)
        rprint(f"[green]✓[/green] Graph '{graph_name}' validated successfully")
    except Exception as e:
        rprint(f"[red]✗[/red] Validation failed: {e}")
        raise typer.Exit(1)

    if dry_run:
        rprint(f"\n[bold]Would execute graph:[/bold] {graph_name}")
        rprint(f"[bold]Nodes:[/bold] {[n['name'] for n in graph['nodes']]}")
        return

    # Parse cached nodes
    cached_nodes = cached.split(",") if cached else None

    # Execute
    artifact_dir = Path("data/generation")
    executor = GraphExecutor(
        graph,
        registry,
        artifact_dir=artifact_dir,
        cached_nodes=cached_nodes,
        run_id=run_id,
    )

    rprint(f"\n[bold]Executing graph:[/bold] {graph_name}\n")
    result = executor.execute(config)

    # Report results
    rprint("\n[bold]Artifacts:[/bold]")
    for name, path in result.artifacts.items():
        rprint(f"  {name}: [cyan]{path}[/cyan]")


if __name__ == "__main__":
    app()
