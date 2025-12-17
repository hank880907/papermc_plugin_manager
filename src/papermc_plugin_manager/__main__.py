from importlib.metadata import version as get_package_version
import typer
from logzero import logger
from typing import Annotated
from enum import Enum
from dataclasses import dataclass

from .console import console
from .logging import setup_logging
from .plugin_manager import get_plugin_manager, list_connectors
from .utils import get_papermc_version

app = typer.Typer(
    help="PaperMC Plugin Manager - Manage plugins for your PaperMC server.",
    no_args_is_help=True,
)

@dataclass
class CliContext:
    game_version: str
    default_source: str

Source = Enum("Source", list_connectors())

@app.command()
def connectors():
    """List available connectors."""
    pm = get_plugin_manager()
    for connector_name in pm.connectors.keys():
        console.print(f"{connector_name}")


@app.command()
def update(
    ctx: typer.Context
):
    """update command"""
    pm = get_plugin_manager()
    context: CliContext = ctx.obj
    with console.status("[bold green]Fetching plugin information...") as status:
        for message in pm.update(context.default_source):
            status.update(message)
    console.print("OK")


@app.command("list")
def list_installations(
    ctx: typer.Context,
):
    pm = get_plugin_manager()
    context: CliContext = ctx.obj
    installations, unrecognized = pm.get_installations()
    if not installations:
        console.print("[yellow]No installed plugins found.[/yellow]")
        console.print("Run [green]ppm update[/green] to scan for installed plugins.")
        raise typer.Exit()
    
    from .console import create_installed_plugins_table, create_unidentified_plugins_table
    console.print(create_installed_plugins_table(installations, context.game_version))
    if unrecognized:
        console.print(f"\n[bold]Unrecognized Plugins: {len(unrecognized)}[/bold]")
        console.print(f"Run [green]ppm update[/green] to attempt to identify them.")
        console.print(create_unidentified_plugins_table(unrecognized))
    

@app.callback(invoke_without_command=True)
def setup_app(
    ctx: typer.Context,
    default_source: Annotated[Source, typer.Option("--source", "-s", help="Default Connector source to use.", show_default=True)] = Source.Modrinth,
    show_version: bool = typer.Option(None, "--version", help="Show the application version and exit.", is_eager=True),
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0
):
    """Setup the application context."""
    setup_logging(verbose)

    ctx.obj = CliContext(
        game_version=get_papermc_version(),
        default_source=default_source.name,
    )

    logger.debug("Starting PaperMC Plugin Manager")
    if show_version:
        app_version = get_package_version("papermc_plugin_manager")
        console.print(f"[cyan]PaperMC Plugin Manager[/cyan] [green]v{app_version}[/green]")
        raise typer.Exit()


def main():
    app()
