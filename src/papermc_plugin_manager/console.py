"""Rich console utilities for the PaperMC Plugin Manager CLI."""

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Create a global console instance
console = Console()


def create_plugin_info_panel(
    name: str,
    id: str,
    author: str,
    downloads: int,
    latest: str | None,
    latest_release: str | None,
    description: str | None = None,
    installed_info: str | None = None,
    compatibility_info: str | None = None,
) -> Panel:
    """Create a Rich Panel for displaying plugin information."""

    # Create the content with aligned labels
    content = []
    content.append(f"[cyan]ID:[/cyan]              {id}")
    content.append(f"[cyan]Author:[/cyan]          {author}")
    content.append(f"[cyan]Downloads:[/cyan]       {downloads:,}")
    content.append(f"[cyan]Latest:[/cyan]          {latest if latest else '[dim]N/A[/dim]'}")
    content.append(f"[cyan]Latest Release:[/cyan]  {latest_release if latest_release else '[dim]N/A[/dim]'}")

    if installed_info:
        content.append("")
        content.append(installed_info)
        if compatibility_info:
            content.append(compatibility_info)

    if description:
        content.append("")
        content.append("[yellow]Description:[/yellow]")
        content.append(description)

    return Panel(
        "\n".join(content),
        title=f"[bold green]{name}[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )


def create_search_results_table(results: dict) -> Table:
    """Create a Rich Table for displaying search results."""

    table = Table(
        title="[bold cyan]Search Results[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title_style="bold cyan",
    )

    table.add_column("ID", style="dim", width=10, justify="left")
    table.add_column("Name", style="bold green", no_wrap=False)
    table.add_column("Author", style="cyan")
    table.add_column("Downloads", justify="right", style="yellow")
    table.add_column("Description", no_wrap=False, style="white")

    for plugin_id, project in results.items():
        # Truncate description if too long
        desc = project.description or ""
        if len(desc) > 60:
            desc = desc[:57] + "..."

        table.add_row(
            plugin_id,
            project.name,
            project.author,
            f"{project.downloads:,}",
            desc,
        )

    return table


def create_version_table(versions_data: list, title: str = "Available Versions", game_version: str = None) -> Table:
    """Create a Rich Table for displaying version information."""

    table = Table(
        title=f"[bold cyan]{title}[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Version ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold green")
    table.add_column("Type", style="white")
    table.add_column("Release Date", style="white")
    table.add_column("MC Versions", style="dim")

    for version_id, file_info in versions_data:
        # Format Minecraft versions (showing newest first)
        mc_versions = ", ".join(reversed(file_info.mc_versions[-3:]))  # Show last 3 versions in reverse (newest first)
        if len(file_info.mc_versions) > 3:
            mc_versions += f" +{len(file_info.mc_versions) - 3} more"

        # Style the version type
        version_type = file_info.version_type
        if version_type == "RELEASE":
            type_style = "[green]●[/green] RELEASE"
        elif version_type == "BETA":
            type_style = "[yellow]●[/yellow] BETA"
        else:
            type_style = "[red]●[/red] ALPHA"

        # Check compatibility with game version
        compatibility_icon = ""
        if game_version and file_info.mc_versions:
            # Parse game version into parts
            game_parts = game_version.split(".")

            # Check each supported version for best match
            best_match = 0  # 0 = no match, 2 = two digits, 3 = three digits
            for mc_version in file_info.mc_versions:
                mc_parts = mc_version.split(".")

                # Check for three-digit match
                if len(game_parts) >= 3 and len(mc_parts) >= 3 and game_parts[:3] == mc_parts[:3]:
                    best_match = 3
                    break

                # Check for two-digit match
                if len(game_parts) >= 2 and len(mc_parts) >= 2 and game_parts[:2] == mc_parts[:2]:
                    best_match = max(best_match, 2)

            # Set icon based on best match
            if best_match == 3:
                compatibility_icon = "[green]✓[/green] "
            elif best_match == 2:
                compatibility_icon = "[yellow]⚠[/yellow] "
            elif file_info.mc_versions:  # Has version info but no match
                compatibility_icon = "[red]✗[/red] "

        table.add_row(
            version_id,
            f"{compatibility_icon}{file_info.version_name}",
            type_style,
            file_info.release_date.strftime("%Y-%m-%d"),
            mc_versions,
        )

    return table


def create_version_detail_panel(version_id: str, file_info) -> Panel:
    """Create a Rich Panel for displaying detailed version information."""

    content = []
    content.append(f"[cyan]Version ID:[/cyan]     {file_info.version_id}")
    content.append(f"[cyan]Version Name:[/cyan]   {file_info.version_name}")
    content.append(f"[cyan]Release Type:[/cyan]   {file_info.version_type}")
    content.append(f"[cyan]Release Date:[/cyan]   {file_info.release_date.strftime('%Y-%m-%d %H:%M:%S')}")
    content.append(f"[cyan]MC Versions:[/cyan]    {', '.join(file_info.mc_versions)}")
    content.append(f"[cyan]Download URL:[/cyan]   {file_info.url}")

    if file_info.hashes:
        content.append("")
        content.append("[yellow]Hashes:[/yellow]")
        for hash_type, hash_value in file_info.hashes.items():
            content.append(f"  {hash_type.upper()}: [dim]{hash_value}[/dim]")

    if file_info.description:
        content.append("")
        content.append("[yellow]Description:[/yellow]")
        content.append(file_info.description)

    return Panel(
        "\n".join(content),
        title="[bold green]Version Details[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )


def create_installed_plugins_table(plugins_data: list, game_version: str = None) -> Table:
    """Create a Rich Table for displaying installed plugin status."""

    table = Table(
        title="[bold cyan]Installed Plugins[/bold cyan]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("Project ID", style="dim", width=10)
    table.add_column("Project", style="bold green")
    table.add_column("Version Name", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Release Date", style="dim")
    table.add_column("Status", style="white", justify="center")

    for _file_name, file_info, is_outdated, project_name, project_id, latest_version in plugins_data:
        # Style the version type
        version_type = file_info.version_type
        if version_type == "RELEASE":
            type_display = "[green]●[/green] RELEASE"
        elif version_type == "BETA":
            type_display = "[yellow]●[/yellow] BETA"
        else:
            type_display = "[red]●[/red] ALPHA"

        # Check compatibility with game version
        compatibility_icon = "[dim]?[/dim]"  # Unknown by default
        if game_version and file_info.mc_versions:
            # Parse game version into parts
            game_parts = game_version.split(".")

            # Check each supported version for best match
            best_match = 0  # 0 = no match, 2 = two digits, 3 = three digits
            for mc_version in file_info.mc_versions:
                mc_parts = mc_version.split(".")

                # Check for three-digit match
                if len(game_parts) >= 3 and len(mc_parts) >= 3 and game_parts[:3] == mc_parts[:3]:
                    best_match = 3
                    break

                # Check for two-digit match
                if len(game_parts) >= 2 and len(mc_parts) >= 2 and game_parts[:2] == mc_parts[:2]:
                    best_match = max(best_match, 2)

            # Set icon based on best match
            if best_match == 3:
                compatibility_icon = "[green]✓[/green]"
            elif best_match == 2:
                compatibility_icon = "[yellow]⚠[/yellow]"
            elif file_info.mc_versions:  # Has version info but no match
                compatibility_icon = "[red]✗[/red]"

        # Add compatibility icon to version name
        version_display = f"{compatibility_icon} {file_info.version_name}"

        # Status indicator - show latest version if outdated
        if is_outdated and latest_version:
            status_display = f"[yellow]⚠ {latest_version}[/yellow]"
        else:
            status_display = "[green]✓ Current[/green]"

        table.add_row(
            project_id,
            project_name,
            version_display,
            type_display,
            file_info.release_date.strftime("%Y-%m-%d"),
            status_display,
        )

    return table


def create_unidentified_plugins_table(unidentified_data: list) -> Table:
    """Create a Rich Table for displaying unidentified/unrecognized plugins."""

    table = Table(
        title="[bold yellow]Unidentified Plugins[/bold yellow]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    table.add_column("File Name", style="bold yellow")
    table.add_column("SHA1", style="dim")
    table.add_column("Size", style="cyan", justify="right")

    for filename, sha1, file_size in unidentified_data:
        # Format file size
        if file_size < 1024:
            size_str = f"{file_size} B"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"

        table.add_row(
            filename,
            sha1[:16] + "...",  # Truncate SHA1 for display
            size_str,
        )

    return table


def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}", style="red")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[cyan]ℹ[/cyan] {message}")
