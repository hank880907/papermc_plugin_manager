import typer
import os
from typing import Optional
from papermc_plugin_manager.connector_interface import get_connector, CliContext
from pathlib import Path
from requests import HTTPError

from .utils import get_papermc_version, get_sha1
from .plugin_manager import PluginManager
from .connector_interface import ProjectInfo, FileInfo

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
    version: Optional[str] = typer.Option(None, help="Specific plugin version to show"),
    snapshot: bool = typer.Option(True, help="Show the latest snapshot version"),
    limit: int = typer.Option(5, help="Limit the number of version displayed")
    ):
    """Display information about the current PaperMC server version."""
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    manager = PluginManager(connector, cli_ctx.game_version)
    result = manager.fuzzy_find_project(name)
    if not result:
        typer.echo(f"Plugin {name} not found.")
        raise typer.Exit(code=1)
    is_exact_match, project = result
    typer.echo(project.complete_description())

    if not version:
        i = 0
        for id, file in project.versions.items():
            if not snapshot and file.version_type != "RELEASE":
                continue
            typer.echo(f"{id}: {file}")
            if i+1 >= limit:
                break
            i += 1
    else:
        if version in project.versions:
            file = project.versions[version]
            typer.echo(f"{version}: {file}")
            typer.echo(f"Minecraft Versions: {', '.join(file.mc_versions)}")
            typer.echo(f"Release Type: {file.version_type}")
            typer.echo(f"Download URL: {file.url}")
            typer.echo(f"Hashes: {file.hashes}")
            typer.echo(f"Release Date: {file.release_date}")
        else:
            typer.echo(f"Version {version} not found for plugin {project.name}.")
            raise typer.Exit(code=1)


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
    version: Optional[str] = typer.Option(None, help="Specific plugin version to install"),
    snapshot: bool = typer.Option(False, help="Install the latest snapshot version"),
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatic yes to prompts"),
    ):
    
    """Install a plugin for the current PaperMC version."""
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    game_version = cli_ctx.game_version
    manager = PluginManager(connector, game_version)
    result = manager.fuzzy_find_project(name)

    if not result:
        typer.echo(f"Plugin {name} not found.")
        raise typer.Exit(code=1)
    
    is_exact_match, project = result
    if not is_exact_match and not yes:
        typer.confirm(f"Do you want to install {project.name} (ID: {project.id})?", abort=True)

    target: str = ""
    if snapshot and project.latest:
        target = project.latest
    elif project.latest_release:
        target = project.latest_release
    elif project.latest:
        target = project.latest

    if target:
        file = project.versions[target]
        typer.echo(f"Installing latest {file.version_type}: {project.name}-{file.version_name} (ID: {file.version_id})")
        manager.install_plugin(file)
        typer.echo("Installation complete.")
    else:
        typer.echo("No available versions to install.")
        raise typer.Exit(code=1)


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
    typer.echo(f"PaperMC version: {game_version}")
    ctx.obj = CliContext(
        game_version=game_version,
        default_platform=platform,
        connector=get_connector(platform),
    )
    
    


def main():
    app()