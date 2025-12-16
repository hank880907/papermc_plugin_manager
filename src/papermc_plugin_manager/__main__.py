import typer
import os
from typing import Optional
from papermc_plugin_manager.connector_interface import get_connector, CliContext
from pathlib import Path
from requests import HTTPError

from .utils import get_papermc_version
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
    """Display information about a plugin."""
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    manager = PluginManager(connector, cli_ctx.game_version)
    result = manager.fuzzy_find_project(name)
    if not result:
        print_error(f"Plugin {name} not found.")
        raise typer.Exit(code=1)
    is_exact_match, project = result
    
    # Check if plugin is installed
    installed_plugin = manager.get_installed_plugin_by_project_id(project.id)
    installed_info = None
    if installed_plugin:
        filename, file_info = installed_plugin
        installed_info = f"[green]✓ Installed:[/green] {file_info.version_name} [dim]({filename})[/dim]"
    else:
        installed_info = "[dim]Not installed[/dim]"
    
    # Convert version IDs to version names
    latest_name = None
    if project.latest and project.latest in project.versions:
        latest_name = project.versions[project.latest].version_name
    
    latest_release_name = None
    if project.latest_release and project.latest_release in project.versions:
        latest_release_name = project.versions[project.latest_release].version_name
    
    # Display project info in a panel
    panel = create_plugin_info_panel(
        name=project.name,
        id=project.id,
        author=project.author,
        downloads=project.downloads,
        latest=latest_name,
        latest_release=latest_release_name,
        description=project.description,
        installed_info=installed_info,
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
    if version:
        if version in project.versions:
            target = version
        else:
            # Check if version matches any FileInfo.version_name
            matched_version_id = None
            for version_id, file_info in project.versions.items():
                if file_info.version_name == version:
                    matched_version_id = version_id
                    break
            if matched_version_id:
                target = matched_version_id
            else:
                print_error(f"Version {version} not found for plugin {project.name}.")
                raise typer.Exit(code=1)
    else:
        if snapshot and project.latest:
            target = project.latest
        elif project.latest_release:
            target = project.latest_release
        elif project.latest:
            target = project.latest

    if target:
        file = project.versions[target]
        print_info(f"Installing [bold]{project.name}[/bold] [cyan]{file.version_name}[/cyan] ({file.version_type})")
        
        # Download with progress bar
        from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
        
        downloaded = False
        # Allow downgrade when user specifies a specific version
        allow_replace = version is not None
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = None
            for bytes_downloaded, total_size, chunk, filename in manager.install_plugin(file, allow_replace=allow_replace):
                downloaded = True
                if task is None:
                    task = progress.add_task(f"[cyan]Downloading {filename}...", total=total_size)
                progress.update(task, completed=bytes_downloaded)
        
        if downloaded:
            print_success("Installation complete!")
    else:
        print_error("No available versions to install.")
        raise typer.Exit(code=1)


@app.command(name="list")
def list_plugins(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
):
    """List all installed plugins."""
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)
    
    with console.status("[bold green]Scanning plugins...") as status:
        plugins_data = manager.get_installed_plugins(
            plugins_dir="./plugins",
            force_refresh=False,
            status_callback=status.update
        )
    
    console.print()  # Add blank line before table
    if plugins_data:
        table = create_installed_plugins_table(plugins_data)
        console.print(table)
    else:
        print_warning("No plugins found in ./plugins directory.")


@app.command()
def update(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
):
    """Update the plugin cache with latest version information."""
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)
    
    print_info("Updating plugin cache...")
    
    with console.status("[bold green]Fetching plugin information...") as status:
        plugins_data = manager.get_installed_plugins(
            plugins_dir="./plugins",
            force_refresh=True,
            status_callback=status.update
        )
    
    console.print()
    if plugins_data:
        outdated_count = sum(1 for _, _, is_outdated, _ in plugins_data if is_outdated)
        print_success(f"Cache updated. Found {len(plugins_data)} plugin(s).")
        if outdated_count > 0:
            print_info(f"{outdated_count} plugin(s) can be upgraded. Run 'ppm upgrade' to upgrade them.")
    else:
        print_warning("No plugins found.")


@app.command()
def upgrade(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatic yes to prompts"),
):
    """Upgrade all outdated plugins to their latest versions."""
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)
    
    # Get installed plugins with their status (from cache)
    with console.status("[bold green]Checking for outdated plugins...") as status:
        plugins_data = manager.get_installed_plugins(
            plugins_dir="./plugins",
            force_refresh=False,  # Use cache only, like apt
            status_callback=status.update
        )
    
    # Filter outdated plugins
    outdated_plugins = [(filename, file_info, project_name) for filename, file_info, is_outdated, project_name in plugins_data if is_outdated]
    
    if not outdated_plugins:
        print_success("All plugins are up to date!")
        return
    
    # Show what will be upgraded
    console.print(f"\n[bold yellow]Found {len(outdated_plugins)} outdated plugin(s):[/bold yellow]\n")
    for filename, file_info, project_name in outdated_plugins:
        console.print(f"  • [cyan]{project_name}[/cyan] [dim]({filename})[/dim]")
        console.print(f"    Current: {file_info.version_name}")
    
    console.print()
    
    if not yes:
        if not typer.confirm("Do you want to upgrade these plugins?"):
            print_warning("Upgrade cancelled.")
            return
    
    # Upgrade each outdated plugin
    upgraded_count = 0
    failed_count = 0
    
    for filename, file_info, project_name in outdated_plugins:
        try:
            console.print(f"\n[bold cyan]Upgrading {project_name}...[/bold cyan]")
            
            # Get project info to find latest version
            project_info = connector.get_project_info(file_info.project_id)
            
            # Find latest version of same type
            latest_version_id = None
            if file_info.version_type == "RELEASE" and project_info.latest_release:
                latest_version_id = project_info.latest_release
            elif file_info.version_type in ["BETA", "ALPHA"] and project_info.latest:
                latest_version_id = project_info.latest
            
            if not latest_version_id or latest_version_id not in project_info.versions:
                print_error(f"Could not find latest version for {project_name}")
                failed_count += 1
                continue
            
            latest_file = project_info.versions[latest_version_id]
            
            # Download with progress bar
            from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
            
            downloaded = False
            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = None
                for bytes_downloaded, total_size, chunk, download_filename in manager.upgrade_plugin(latest_file):
                    downloaded = True
                    if task is None:
                        task = progress.add_task(f"[cyan]Downloading {download_filename}...", total=total_size)
                    progress.update(task, completed=bytes_downloaded)
            
            if downloaded:
                print_success(f"Upgraded {project_name} to {latest_file.version_name}")
                upgraded_count += 1
            
        except Exception as e:
            print_error(f"Failed to upgrade {project_name}: {e}")
            failed_count += 1
    
    # Summary
    console.print()
    if upgraded_count > 0:
        print_success(f"Successfully upgraded {upgraded_count} plugin(s)")
    if failed_count > 0:
        print_warning(f"Failed to upgrade {failed_count} plugin(s)")


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