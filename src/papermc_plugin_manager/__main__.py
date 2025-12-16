import typer
from logzero import logger

from papermc_plugin_manager.connector_interface import CliContext, get_connector

from .cache_manager import CacheManager
from .config import Config
from .console import (
    console,
    create_installed_plugins_table,
    create_plugin_info_panel,
    create_search_results_table,
    create_unidentified_plugins_table,
    create_version_detail_panel,
    create_version_table,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from .exceptions import (
    PluginNotFoundException,
    ServerVersionException,
    VersionNotFoundException,
)
from .plugin_manager import PluginManager
from .utils import get_papermc_version, setup_logging

app = typer.Typer(
    help="PaperMC Plugin Manager - Manage plugins for your PaperMC server.",
    no_args_is_help=True,
)


def plugin_name_autocomplete(incomplete: str) -> list[str]:
    """Autocomplete function for plugin names from cache."""
    # Suppress all logging during autocomplete to avoid polluting terminal output
    import logzero
    original_level = logzero.logger.level
    logzero.loglevel(logzero.logging.CRITICAL)

    suggestions = []

    try:
        cache_mgr = CacheManager()
        for project_id, project_data in cache_mgr.cache_data.get("projects", {}).items():
            project_name = project_data.get("name", "")
            # Add both project name and ID as suggestions
            if incomplete.lower() in project_name.lower():
                suggestions.append(project_name)
            if incomplete.lower() in project_id.lower():
                suggestions.append(project_id)
    except Exception:
        pass
    finally:
        # Restore original log level
        logzero.loglevel(original_level)

    return suggestions


def version_autocomplete(ctx: typer.Context, incomplete: str) -> list[str]:
    """Autocomplete function for version names from cache.

    This extracts the plugin name from the command context and suggests
    versions for that specific plugin.
    """
    # Suppress all logging during autocomplete to avoid polluting terminal output
    import logzero
    original_level = logzero.logger.level
    logzero.loglevel(logzero.logging.CRITICAL)

    suggestions = []

    try:
        # Get the plugin name from the command line arguments
        # Parse from environment variable that Typer sets
        import os as os_module

        complete_args = os_module.environ.get("_TYPER_COMPLETE_ARGS", "")

        # Extract plugin name from the command line
        # Format is usually: "ppm <command> <plugin_name> --version <incomplete>"
        plugin_name = None
        if complete_args:
            parts = complete_args.split()
            # Find the position after the command name
            if len(parts) >= 3:
                # parts[0] = 'ppm', parts[1] = command (show/install), parts[2] = plugin name
                plugin_name = parts[2]

        if not plugin_name:
            return suggestions

        cache_mgr = CacheManager()

        # Find the project by name or ID
        project_data = None
        plugin_name_lower = plugin_name.lower()

        # First try direct ID match
        if plugin_name in cache_mgr.cache_data.get("projects", {}):
            project_data = cache_mgr.cache_data["projects"][plugin_name]
        else:
            # Try name match
            for _project_id, proj_data in cache_mgr.cache_data.get("projects", {}).items():
                if proj_data.get("name", "").lower() == plugin_name_lower:
                    project_data = proj_data
                    break

        if not project_data:
            return suggestions

        # Get versions from cache
        versions = project_data.get("versions", {})
        for _version_id, version_data in versions.items():
            version_name = version_data.get("version_name", "")
            if incomplete.lower() in version_name.lower():
                suggestions.append(version_name)
    except Exception:
        pass
    finally:
        # Restore original log level
        logzero.loglevel(original_level)

    return suggestions


@app.command()
def search(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name of the plugin to query"),
):
    """Search for plugins by name.

    Queries the plugin repository for plugins matching the given name.
    Results are displayed in a table with project information.
    """
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
    name: str = typer.Argument(..., help="Name or ID of the plugin to show", autocompletion=plugin_name_autocomplete),
    version: str | None = typer.Option(
        None, help="Specific plugin version to show", autocompletion=version_autocomplete
    ),
    snapshot: bool = typer.Option(True, help="Show the latest snapshot version"),
    limit: int = typer.Option(Config.DEFAULT_VERSION_LIMIT, help="Limit the number of version displayed"),
):
    """Display detailed information about a plugin.

    Shows comprehensive plugin details including name, author, download count,
    description, and installation status. If no specific version is provided,
    displays the installed version details (if any) followed by a table of
    available versions. Use --version to show details for a specific version.
    """
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    manager = PluginManager(connector, cli_ctx.game_version)
    try:
        result = manager.fuzzy_find_project(name)
        if not result:
            raise PluginNotFoundException(name)
        is_exact_match, project = result
    except PluginNotFoundException as e:
        print_error(str(e))
        raise typer.Exit(code=1)

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
        # If plugin is installed, show the installed version details first
        if installed_plugin:
            filename, file_info = installed_plugin
            # Find the version_id for the installed version
            installed_version_id = file_info.version_id

            console.print("[bold cyan]Installed Version Details[/bold cyan]\n")
            panel = create_version_detail_panel(installed_version_id, file_info)
            console.print(panel)
            console.print()

        # Show available versions in a table
        versions_data = []
        i = 0
        for version_id, file in project.versions.items():
            if not snapshot and file.version_type != "RELEASE":
                continue
            versions_data.append((version_id, file))
            if i + 1 >= limit:
                break
            i += 1

        if versions_data:
            table = create_version_table(versions_data, f"Available Versions (showing {len(versions_data)})")
            console.print(table)
    else:
        # Try to find version by version_id first, then by version_name
        file = None
        version_id = None

        if version in project.versions:
            # Direct match by version_id
            version_id = version
            file = project.versions[version]
        else:
            # Try to match by version_name
            for vid, vfile in project.versions.items():
                if vfile.version_name == version:
                    version_id = vid
                    file = vfile
                    break

        if file:
            panel = create_version_detail_panel(version_id, file)
            console.print(panel)
        else:
            raise VersionNotFoundException(project.name, version)


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
    name: str = typer.Argument(
        ..., help="Name or ID of the plugin to install", autocompletion=plugin_name_autocomplete
    ),
    version: str | None = typer.Option(
        None, help="Specific plugin version to install", autocompletion=version_autocomplete
    ),
    snapshot: bool = typer.Option(False, help="Install the latest snapshot version"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatic yes to prompts"),
):
    """Install a plugin from the repository.

    Downloads and installs a plugin to the plugins directory. By default,
    installs the latest release version. Use --version to install a specific
    version, or --snapshot to install the latest snapshot/beta version.
    Shows a progress bar during download. Requires confirmation for non-exact
    name matches unless --yes is specified.
    """
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    game_version = cli_ctx.game_version
    manager = PluginManager(connector, game_version)

    try:
        result = manager.fuzzy_find_project(name)
        if not result:
            raise PluginNotFoundException(name)
    except PluginNotFoundException as e:
        print_error(str(e))
        raise typer.Exit(code=1)

    is_exact_match, project = result
    if not is_exact_match and not yes:
        console.print(
            f"\n[yellow]⚠ Plugin name doesn't exactly match. Found:[/yellow] [bold green]{project.name}[/bold green] [dim](ID: {project.id})[/dim]"
        )
        typer.confirm(f"Do you want to install {project.name}?", abort=True)

    target: str = ""
    try:
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
                    raise VersionNotFoundException(project.name, version)
        else:
            if snapshot and project.latest:
                target = project.latest
            elif project.latest_release:
                target = project.latest_release
            elif project.latest:
                target = project.latest
    except VersionNotFoundException as e:
        print_error(str(e))
        raise typer.Exit(code=1)

    if target:
        file = project.versions[target]
        print_info(f"Installing [bold]{project.name}[/bold] [cyan]{file.version_name}[/cyan] ({file.version_type})")

        # Download with progress bar
        from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn

        downloaded = False
        # Allow downgrade when user specifies a specific version
        allow_replace = version is not None
        try:
            with Progress(
                "[progress.description]{task.description}",
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = None
                for bytes_downloaded, total_size, _chunk, filename in manager.install_plugin(
                    file, allow_replace=allow_replace
                ):
                    downloaded = True
                    if task is None:
                        task = progress.add_task(f"[cyan]Downloading {filename}...", total=total_size)
                    progress.update(task, completed=bytes_downloaded)

            if downloaded:
                print_success("Installation complete!")
        except Exception as e:
            print_error(f"Installation failed: {e}")
            raise typer.Exit(code=1)
    else:
        print_error("No available versions to install.")
        raise typer.Exit(code=1)


@app.command(name="list")
def list_plugins(
    ctx: typer.Context,
    platform: str = typer.Option(Config.DEFAULT_PLATFORM, help="Plugin platform to query"),
):
    """List all installed plugins with version and update status.

    Scans the plugins directory and displays identified plugins in a table
    showing name, version, type, update status, and game version compatibility.
    Uses cached data for fast listing. Outdated plugins are highlighted.
    Unidentified plugins (from non-Modrinth sources) are shown separately.
    """
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)

    with console.status("[bold green]Scanning plugins...") as status:
        plugins_data, unidentified_data = manager.get_installed_plugins(
            plugins_dir=Config.get_plugins_dir(), force_refresh=False, status_callback=status.update
        )

    console.print()  # Add blank line before table
    if plugins_data:
        table = create_installed_plugins_table(plugins_data, game_version=ctx.obj.game_version)
        console.print(table)
    else:
        print_warning("No identified plugins found in ./plugins directory.")

    # Display unidentified plugins if any
    if unidentified_data:
        console.print()  # Add spacing
        unidentified_table = create_unidentified_plugins_table(unidentified_data)
        console.print(unidentified_table)
        console.print()
        print_info(
            f"Found {len(unidentified_data)} unidentified plugin(s). These may be from sources other than Modrinth."
        )


@app.command()
def update(
    ctx: typer.Context,
    platform: str = typer.Option(Config.DEFAULT_PLATFORM, help="Plugin platform to query"),
):
    """Update the plugin cache with latest version information.

    Refreshes the local cache by fetching current plugin data from the repository.
    This checks for new versions of installed plugins and updates the cache with
    latest release information. Run this before 'upgrade' to ensure you get the
    most recent versions. Similar to 'apt update' in behavior.
    """
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)

    print_info("Updating plugin cache...")

    with console.status("[bold green]Fetching plugin information...") as status:
        plugins_data, unidentified_data = manager.get_installed_plugins(
            plugins_dir=Config.get_plugins_dir(), force_refresh=True, status_callback=status.update
        )

    console.print()
    if plugins_data:
        outdated_count = sum(1 for _, _, is_outdated, _, _, _ in plugins_data if is_outdated)
        print_success(f"Cache updated. Found {len(plugins_data)} plugin(s).")
        if outdated_count > 0:
            print_info(f"{outdated_count} plugin(s) can be upgraded. Run 'ppm upgrade' to upgrade them.")
    if unidentified_data:
        print_info(f"Found {len(unidentified_data)} unidentified plugin(s) from non-Modrinth sources.")
    if not plugins_data and not unidentified_data:
        print_warning("No plugins found.")


@app.command()
def rm(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name or ID of the plugin to remove", autocompletion=plugin_name_autocomplete),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Remove an installed plugin from the plugins directory.

    Deletes the specified plugin file after confirmation. Shows the plugin name,
    filename, and version before removal. Use --yes to skip the confirmation
    prompt for automated scripts. The plugin must be installed to be removed.
    """
    cli_ctx: CliContext = ctx.obj
    connector = cli_ctx.connector
    manager = PluginManager(connector, cli_ctx.game_version)

    # Find the plugin
    try:
        result = manager.fuzzy_find_project(name)
        if not result:
            raise PluginNotFoundException(name)
    except PluginNotFoundException as e:
        print_error(str(e))
        raise typer.Exit(code=1)

    _, project_info = result

    # Check if plugin is installed
    installed = manager.get_installed_plugin_by_project_id(project_info.id)
    if not installed:
        print_warning(f"Plugin '{project_info.name}' is not installed.")
        raise typer.Exit(code=1)

    filename, file_info = installed

    # Show plugin info and confirm
    console.print("\n[bold yellow]Plugin to remove:[/bold yellow]")
    console.print(f"  Name: [cyan]{project_info.name}[/cyan]")
    console.print(f"  File: [dim]{filename}[/dim]")
    console.print(f"  Version: {file_info.version_name}\n")

    if not yes and not typer.confirm("Are you sure you want to remove this plugin?"):
        print_warning("Removal cancelled.")
        return

    # Remove the plugin
    result = manager.remove_plugin(name)
    if result:
        removed_filename, removed_name = result
        print_success(f"Removed {removed_name} ({removed_filename})")
    else:
        print_error("Failed to remove plugin.")
        raise typer.Exit(code=1)


@app.command()
def upgrade(
    ctx: typer.Context,
    platform: str = typer.Option(Config.DEFAULT_PLATFORM, help="Plugin platform to query"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Automatic yes to prompts"),
):
    """Upgrade all outdated plugins to their latest versions.

    Checks cached data for outdated plugins and upgrades them to the latest
    available versions. Shows which plugins will be upgraded and requires
    confirmation unless --yes is specified. Each plugin is downloaded with a
    progress bar. Run 'ppm update' first to ensure cache is current.
    """
    connector = get_connector(platform)
    manager = PluginManager(connector, ctx.obj.game_version)

    # Get installed plugins with their status (from cache)
    with console.status("[bold green]Checking for outdated plugins...") as status:
        plugins_data, _ = manager.get_installed_plugins(
            plugins_dir=Config.get_plugins_dir(),
            force_refresh=False,  # Use cache only, like apt
            status_callback=status.update,
        )

    # Filter outdated plugins
    outdated_plugins = [
        (filename, file_info, project_name)
        for filename, file_info, is_outdated, project_name, project_id, latest_version in plugins_data
        if is_outdated
    ]

    if not outdated_plugins:
        print_success("All plugins are up to date!")
        return

    # Show what will be upgraded
    console.print(f"\n[bold yellow]Found {len(outdated_plugins)} outdated plugin(s):[/bold yellow]\n")
    for filename, file_info, project_name in outdated_plugins:
        console.print(f"  • [cyan]{project_name}[/cyan] [dim]({filename})[/dim]")
        console.print(f"    Current: {file_info.version_name}")

    console.print()

    if not yes and not typer.confirm("Do you want to upgrade these plugins?"):
        print_warning("Upgrade cancelled.")
        return

    # Upgrade each outdated plugin
    upgraded_count = 0
    failed_count = 0

    for _filename, file_info, project_name in outdated_plugins:
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
            from rich.progress import BarColumn, DownloadColumn, Progress, TimeRemainingColumn, TransferSpeedColumn

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
                for bytes_downloaded, total_size, _chunk, download_filename in manager.upgrade_plugin(latest_file):
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


@app.callback(invoke_without_command=True)
def initialize_cli(
    ctx: typer.Context,
    platform: str = typer.Option(Config.DEFAULT_PLATFORM, help="Plugin platform to query"),
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    PaperMC Plugin Manager - Manage plugins for your PaperMC server.
    """
    # Setup logging
    setup_logging(verbose=verbose)
    logger.debug("PPM starting")

    if version:
        console.print("[cyan]PaperMC Plugin Manager[/cyan] [green]v0.1.0[/green]")
        raise typer.Exit()

    # Only check for server version if we're running a command
    if ctx.invoked_subcommand is None:
        return

    try:
        game_version = get_papermc_version()
        if not game_version:
            raise ServerVersionException()
        logger.info(f"Detected PaperMC version: {game_version}")
    except ServerVersionException as e:
        logger.error(f"Server version detection failed: {e}")
        print_error(str(e))
        raise typer.Exit()
    print_info(f"PaperMC version: [bold green]{game_version}[/bold green]")
    ctx.obj = CliContext(
        game_version=game_version,
        default_platform=platform,
        connector=get_connector(platform),
    )


def main():
    app()
