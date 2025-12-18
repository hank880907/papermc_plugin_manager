from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Annotated

import logzero
import typer

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

@app.command()
def connectors():
    """List available connectors"""
    pm = get_plugin_manager()
    for connector_name in pm.connectors:
        console.print(f"{connector_name}")


@app.command()
def update(
    ctx: typer.Context
):
    """update information of the installed plugins"""
    pm = get_plugin_manager()
    with console.status("[bold green]Fetching plugin information...") as status:
        pm.update(lambda msg: status.update(msg))
    console.print("[green]✓[/green] [white]done[/white]")


@app.command("list")
def list_installations(
    ctx: typer.Context,
):
    """list installed plugins"""
    pm = get_plugin_manager()
    context: CliContext = ctx.obj

    console.print_info(f"PaperMC version: {context.game_version}")
    installations, unrecognized = pm.get_installations()
    if not installations:
        console.print_warning("No installed plugins found.")
        console.print("Run [green]ppm update[/green] to scan for installed plugins.")
        raise typer.Exit()

    if pm.needs_update():
        console.print_warning("Some installed plugins are not recognized in the database.")
        console.print("Run [green]ppm update[/green] to identify them.")

    console.print_installed_plugins_table(installations, context.game_version)
    if unrecognized:
        console.print(f"\n[bold]Unrecognized Plugins: {len(unrecognized)}[/bold]")
        console.print_unidentified_plugins_table(unrecognized)

def installed_plugin_names() -> list[str]:
    logzero.loglevel(logzero.logging.CRITICAL)
    return get_plugin_manager().get_installation_names()


@app.command()
def show(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name or ID of the plugin to show.", autocompletion=installed_plugin_names)],
    version: Annotated[str | None, typer.Option("--version", "-v", help="Specific version to show details for.")] = None,
    list_version_limit: Annotated[int, typer.Option("--limit", "-l", help="Limit the number of versions displayed.", show_default=True)] = 5,
    snapshot: Annotated[bool, typer.Option(help="Include snapshot versions in the version list.", is_flag=True)] = True,
):
    """show plugin details"""
    pm = get_plugin_manager()
    context: CliContext = ctx.obj

    exact_match, project = pm.fuzzy_find_project(name)
    if not project:
        console.print_error(f"Plugin '{name}' not found.")
        raise typer.Exit(code=1)

    if not exact_match:
        typer.confirm(f"Did you mean plugin '{project.name}' (ID: {project.project_id})?", abort=True, default=True)

    current_version = project.current_version
    filename = None
    if current_version:
        installation = pm.db.get_installation_by_sha1(current_version.sha1)
        if installation:
            filename = installation.filename

    console.print("")
    console.print_project_info_panel(project, filename, context.game_version)

    if version:
        file_info = project.get_version(version)
        if file_info is None:
            console.print_error(f"Version '{version}' not found for plugin '{project.name}'.")
        else:
            console.print_version_detail_panel(file_info)
    elif current_version:
        console.print_version_detail_panel(current_version, "Installed Version Details")

    count = 0
    versions_to_show = []
    for file_info in sorted(project.versions.values(), key=lambda fi: fi.release_date, reverse=True):
        if count >= list_version_limit:
            break
        if not snapshot and file_info.version_type.lower() != "release":
            continue
        versions_to_show.append(file_info)
        count += 1
    if versions_to_show:
        console.print_version_table(versions_to_show, "Available Versions", context.game_version)
    else:
        console.print_warning("No versions available")


@app.command()
def search(
    ctx: typer.Context,
    query: Annotated[str, typer.Argument(help="Search query for plugins.")],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Limit the number of search results.", show_default=True)] = 10,
):
    """search for plugins"""
    pm = get_plugin_manager()
    context: CliContext = ctx.obj

    with console.status("Searching..."):
        results = pm.search_projects(query, mc_version=context.game_version, limit=limit)

    if results:
        console.print_search_results_table(results)
    else:
        console.print_warning("No plugins found matching the query.")


@app.command()
def install(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name or ID of the plugin to install.", autocompletion=installed_plugin_names)],
    version: Annotated[str | None, typer.Option("--version", "-v", help="Specific version to install. If not specified, installs the latest compatible version.")] = None,
    snapshot: Annotated[bool, typer.Option(help="Allow installation of snapshot versions if no release version is found.", is_flag=True, show_default=True)] = False,
):
    """install or update a plugin"""
    from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn

    from .utils import download_file

    pm = get_plugin_manager()
    context: CliContext = ctx.obj

    exact_match, project = pm.fuzzy_find_project(name)
    if not project:
        console.print_error(f"Plugin '{name}' not found.")
        raise typer.Exit(code=1)

    if not exact_match:
        typer.confirm(f"Did you mean plugin '{project.name}' (ID: {project.project_id})?", abort=True, default=False)

    if version:
        version_info = project.get_version(version)
        if version_info is None:
            console.print_error(f"Version '{version}' not found for plugin '{project.name}'.")
            raise typer.Exit(code=1)
    elif project.current_version:
        current = project.current_version
        latest = project.get_latest_type(current.version_type)
        if latest and project.current_version.version_id != latest.version_id:
            console.print(f"Updating plugin {project.name} from version {current.version_name} to {latest.version_name}...")
            version_info = latest
        else:
            console.print(f"Plugin '{project.name}' is already up to date (version {current.version_name}).")
            raise typer.Exit()
    elif snapshot:
        version_info = project.get_latest()
    else:
        version_info = project.get_latest_type("release")
        if version_info is None:
            console.print_warning(f"No release version found for plugin '{project.name}'. Using latest version...")
            version_info = project.get_latest()

    if version_info is None:
        console.print_error(f"No suitable version found for plugin '{project.name}'.")
        raise typer.Exit(code=1)

    # remove existing installation if present
    if project.current_version:
        installation = pm.db.get_installation_by_sha1(project.current_version.sha1)
        if installation:
            plugin_path = Path("plugins") / installation.filename
            if plugin_path.exists():
                console.print(f"Removing existing installation '{installation.filename}'...")
                plugin_path.unlink()
            pm.db.remove_installation(installation.filename)

    filename = project.name.replace(" ", "_") + "-" + version_info.version_name + ".jar"
    url = pm.connectors[context.default_source].get_download_link(version_info)
    with Progress(
        "[progress.description]{task.description}",
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = None
        for bytes_downloaded, total_size in  download_file(url, dest=str(Path("plugins") / filename)):
            if task is None:
                task = progress.add_task(f"[cyan]Downloading {filename}...", total=total_size)
            progress.update(task, completed=bytes_downloaded)
    pm.db.save_project_info(project)
    pm.db.save_installation_info(filename, version_info.sha1, Path(Path("plugins") / filename).stat().st_size)
    console.print(f"[green]✓[/green] [white]{project.name} installed![/white]")
    
    
@app.command()
def remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Name or ID of the plugin to remove.", autocompletion=installed_plugin_names)],
):
    """remove an installed plugin"""
    pm = get_plugin_manager()
    context: CliContext = ctx.obj

    project = pm.get_project_info(name)
    if not project:
        console.print_error(f"Plugin '{name}' not found among installed plugins.")
        raise typer.Exit(code=1)
    
    typer.confirm(f"Are you sure you want to remove plugin '{project.name}' (ID: {project.project_id})?", abort=True, default=False)
    current_version = project.current_version
    if current_version is None:
        console.print_error(f"No installed version found for plugin '{project.name}'.")
        raise typer.Exit(code=1)
    
    installation = pm.db.get_installation_by_sha1(current_version.sha1)
    if installation is None:
        console.print_error(f"No installation record found for plugin '{project.name}'.")
        raise typer.Exit(code=1)
    plugin_path = Path("plugins") / installation.filename
    if plugin_path.exists():
        console.print(f"Removing plugin file '{installation.filename}'...")
        plugin_path.unlink()
        
    pm.db.remove_installation(installation.filename)
    console.print(f"[green]✓[/green] [white]{project.name} removed![/white]")
    


@app.callback(invoke_without_command=True)
def setup_app(
    ctx: typer.Context,
    default_source: Annotated[str, typer.Option("--source", "-s", help="Default Connector source to use.", show_default=True, autocompletion=list_connectors)] = "Modrinth",
    show_version: bool = typer.Option(None, "--version", help="Show the application version and exit.", is_eager=True),
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True)] = 0
):
    setup_logging(verbose)
    game_version = get_papermc_version()
    if game_version is None:
        console.print_warning("Could not determine PaperMC version from version_history.json. Please run this tool in the directory containing your PaperMC server.")
        raise typer.Exit(code=1)

    from .config import Config
    Config.DEFAULT_SOURCE = default_source

    ctx.obj = CliContext(
        game_version=game_version,
        default_source=default_source,
    )

    if show_version:
        app_version = version("papermc_plugin_manager")
        console.print(f"[cyan]PaperMC Plugin Manager[/cyan] [green]v{app_version}[/green]")
        raise typer.Exit()


def main():
    app()
