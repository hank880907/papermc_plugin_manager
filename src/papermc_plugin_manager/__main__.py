import typer
import os
from typing import Optional
from papermc_plugin_manager.connector_interface import get_connector, CliContext
from pathlib import Path
from requests import HTTPError

from .utils import get_papermc_version, get_sha1

app = typer.Typer()

DEFAULT_PLATFORM = os.getenv("PPM_DEFAULT_PLATFORM", "modrinth")

@app.command()
def search(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of the plugin to query"),
    ):
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    game_version = cli_ctx.game_version
    typer.echo(f"Querying for PaperMC version: {game_version}")
    result = connector.query(name, game_version)
    if not result:
        typer.echo("No results found.")
    else:
        typer.echo(f"found {len(result)} results.")
        for i, plugin_id in enumerate(result, start=1):
            typer.echo(f"\n{i}: {plugin_id}")
            typer.echo(f"{result[plugin_id].complete_description()}")


@app.command()
def show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name or ID of the plugin to show"),
    ):
    """Display information about the current PaperMC server version."""
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    try:
        info = connector.get_project_info(name)
    except HTTPError as e:
        typer.echo(f"Plugin {name} not found: {e}.")
        return
    typer.echo(info.complete_description())



@app.command()
def server_info(ctx: typer.Context):
    """Display information about the current CLI context."""
    cli_ctx: CliContext = ctx.obj
    for key, value in cli_ctx.__dict__.items():
        typer.echo(f"{key}: {value}")
        
@app.command()
def install(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name or ID of the plugin to install"),
    plugin_version: Optional[str] = typer.Option(None, help="Specific plugin version to install"),
    snapshot: bool = typer.Option(False, help="Install the latest snapshot version"),
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
    ):
    
    """Install a plugin for the current PaperMC version."""
    cli_ctx: CliContext = ctx.obj
    connector = get_connector(platform)
    typer.echo("Using connector: " + connector.__class__.__name__)
    results = connector.query(name, cli_ctx.game_version)
    for id, project in results.items():
        if project.name == name:
            typer.echo(f"Installing plugin: {project.name} (ID: {project.id})")
            if project.latest is None:
                typer.echo("No stable version available for installation.")
                return
            connector.download(project.latest_release.version_id, "./plugins")
            typer.echo("Installation complete.")
            return
    typer.echo(f"Plugin {name} not found, or cannot be uniquely identified.")
    



@app.command()
def status(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),):
    connector = get_connector(platform)
    files = os.listdir("./plugins")
    for file in files:
        path = Path("./plugins") / file
        if path.is_file():
            sha1 = get_sha1(path)
            file_info = connector.get_file_info(sha1)
            typer.echo(f"{file}: {sha1}")
            typer.echo(f"  Name: {file_info.version_name}")
            typer.echo(f"  Version ID: {file_info.version_id}")
            typer.echo(f"  Version Type: {file_info.version_type}")
            typer.echo(f"  Download URL: {file_info.release_date}")
            typer.echo("")
            
    
    
    
    
    


@app.callback()
def initialize_cli(ctx: typer.Context,
                   platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query")
                   ):
    """
    Manage users in the awesome CLI app.
    """
    game_version = get_papermc_version()
    if not game_version:
        typer.echo("Could not determine PaperMC version. Please run this command in a PaperMC server directory.")
        raise typer.Exit()
    
    ctx.obj = CliContext(
        game_version=game_version,
        default_platform=platform,
        connector=get_connector(platform)
    )
    
    


def main():
    app()