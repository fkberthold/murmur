import typer
from rich import print as rprint
from murmur.registry import TransformerRegistry
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer

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
    from pathlib import Path
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
    from pathlib import Path
    profiles_dir = Path("config/profiles")
    if not profiles_dir.exists():
        rprint("[yellow]No profiles directory found[/yellow]")
        return

    rprint("[bold]Available Profiles:[/bold]\n")
    for path in sorted(profiles_dir.glob("*.yaml")):
        rprint(f"  [cyan]{path.stem}[/cyan]")


if __name__ == "__main__":
    app()
