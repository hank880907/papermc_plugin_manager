import typer
import os
from typing import Optional
from papermc_plugin_manager.connector_interface import get_connector, CliContext
from pathlib import Path
from requests import HTTPError

from .utils import get_papermc_version, get_sha1
from .plugin_manager import PluginManager
from .connector_interface import ProjectInfo, FileInfo
from .console import (
    console,
    create_plugin_info_panel,
    create_search_results_table,
    create_version_table,
    create_version_detail_panel,
    create_installed_plugins_table,
    print_success,
    print_error,
    print_warning,
    print_info,
)

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
        print_warning("No results found.")
    else:
        console.print(f"\n[bold green]Found {len(result)} results[/bold green]\n")
        table = create_search_results_table(result)
        console.print(table)
        console.print()  # Add extra line for spacing


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
        print_error(f"Plugin {name} not found.")
        raise typer.Exit(code=1)
    is_exact_match, project = result
    
    # Display project info in a panel
    panel = create_plugin_info_panel(
        name=project.name,
        id=project.id,
        author=project.author,
        downloads=project.downloads,
        latest=project.latest,
        latest_release=project.latest_release,
        description=project.description,
    )
    console.print(panel)
    console.print()

    if not version:
        # Show available versions in a table
        versions_data = []
        i = 0
        for version_id, file in project.versions.items():
            if not snapshot and file.version_type != "RELEASE":
                continue
            versions_data.append((version_id, file))
            if i+1 >= limit:
                break
            i += 1
        
        if versions_data:
            table = create_version_table(versions_data, f"Available Versions (showing {len(versions_data)})")
            console.print(table)
    else:
        if version in project.versions:
            file = project.versions[version]
            panel = create_version_detail_panel(version, file)
            console.print(panel)
        else:
            print_error(f"Version {version} not found for plugin {project.name}.")
            raise typer.Exit(code=1)


@app.command()
def server_info(ctx: typer.Context):
    """Display information about the current CLI context."""
    cli_ctx: CliContext = ctx.obj
    
    from rich.table import Table
    table = Table(title="[bold cyan]Server Information[/bold cyan]", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")
    
    for key, value in cli_ctx.__dict__.items():
        # Skip the connector object as it's not useful to display
        if key != "connector":
            table.add_row(key, str(value))
    
    console.print(table)
        
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
        print_error(f"Plugin {name} not found.")
        raise typer.Exit(code=1)
    
    is_exact_match, project = result
    if not is_exact_match and not yes:
        console.print(f"\n[yellow]⚠ Plugin name doesn't exactly match. Found:[/yellow] [bold green]{project.name}[/bold green] [dim](ID: {project.id})[/dim]")
        typer.confirm(f"Do you want to install {project.name}?", abort=True)

    target: str = ""
    if snapshot and project.latest:
        target = project.latest
    elif project.latest_release:
        target = project.latest_release
    elif project.latest:
        target = project.latest

    if target:
        file = project.versions[target]
        print_info(f"Installing [bold]{project.name}[/bold] [cyan]{file.version_name}[/cyan] ({file.version_type})")
        manager.install_plugin(file)
        print_success("Installation complete!")
    else:
        print_error("No available versions to install.")
        raise typer.Exit(code=1)


@app.command()
def status(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),):
    connector = get_connector(platform)
    files = os.listdir("./plugins")
    
    plugins_data = []
    for file in files:
        path = Path("./plugins") / file
        if path.is_file():
            sha1 = get_sha1(path)
            try:
                file_info = connector.get_file_info(sha1)
                plugins_data.append((file, file_info))
            except Exception as e:
                print_warning(f"Could not fetch info for {file}: {e}")
    
    if plugins_data:
        table = create_installed_plugins_table(plugins_data)
        console.print(table)
    else:
        print_warning("No plugins found in ./plugins directory.")


@app.callback()
def initialize_cli(ctx: typer.Context,
                   platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query")
                   ):
    """
    PaperMC Plugin Manager - Manage plugins for your PaperMC server.
    """
    game_version = get_papermc_version()
    if not game_version:
        print_error("Could not determine PaperMC version. Please run this command in a PaperMC server directory.")
        raise typer.Exit()
    print_info(f"PaperMC version: [bold green]{game_version}[/bold green]")
    ctx.obj = CliContext(
        game_version=game_version,
        default_platform=platform,
        connector=get_connector(platform),
    )
    
    


def main():
    app()