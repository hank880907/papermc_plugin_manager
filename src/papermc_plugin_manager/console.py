"""Rich console utilities for the PaperMC Plugin Manager CLI."""


from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .connector_interface import FileInfo, ProjectInfo, SearchResult
from .database import InstallationTable


def get_key_value_table(data: list[tuple[str, str]]) -> Table:
    table = Table.grid(padding=(0, 3))
    table.add_column(justify="left", style="cyan", no_wrap=True)
    table.add_column(style="white", no_wrap=False)
    for key, value in data:
        table.add_row(key, value)
    return table

class PpmConsole(Console):

    def __init__(self):
        super().__init__()

    def print_success(self, message: str):
        self.print(f"[green]✓[/green] {message}")


    def print_error(self, message: str):
        self.print(f"[red]✗[/red] {message}", style="red")


    def print_warning(self, message: str):
        self.print(f"[yellow]⚠[/yellow] {message}", style="yellow")

    def print_info(self, message: str):
        self.print(f"[cyan]ℹ[/cyan] {message}")

    def print_project_info_panel(self, info: ProjectInfo, filename: str | None = None, game_version: str | None = None):

        latest_version = info.get_latest()
        latest_release_version = info.get_latest_type("release")

        name = info.name
        id = info.project_id
        author = info.author
        downloads = info.downloads
        latest_version_name = latest_version.version_name if latest_version else None
        latest_release_name = latest_release_version.version_name if latest_release_version else None
        description = info.description

        elements = []
        info_data = [
            ("Name", name),
            ("ID", id),
            ("Author", author),
            ("Downloads", f"{downloads:,}"),
            ("Latest Version", latest_version_name if latest_version_name else "N/A"),
            ("Latest Release", latest_release_name if latest_release_name else "N/A"),
            ("Source", info.source),
        ]

        elements.append(get_key_value_table(info_data))

        elements.append(Text(""))
        if info.current_version:
            elements.append(Text.from_markup(f"[green]✓ Installed:[/green] {info.current_version.version_name} [dim]({filename})[/dim]"))
            if game_version:
                elements.append(Text.from_markup(get_compatibility_info(game_version, info.current_version.game_versions, full=True)))
        else:
            elements.append(Text.from_markup("[dim]Not installed[/dim]"))

        if description:
            elements.append(Text(""))
            elements.append(Text.from_markup("[yellow]Description:[/yellow]"))
            elements.append(Text(description))

        self.print(
            Panel(
                Group(*elements),
                title=f"[bold green]{name}[/bold green]",
                border_style="green",
                box=box.ROUNDED,
            )
        )

    def print_installed_plugins_table(self, projects: list[ProjectInfo], game_version: str | None = None):
        table = Table(
            title="[bold cyan] Installed Plugins [/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("ID", style="dim", width=10)
        table.add_column("Plugin", style="bold green")
        table.add_column("Version", style="cyan")
        table.add_column("Type", style="white")
        table.add_column("Date", style="dim")
        table.add_column("Status", style="white", justify="center")

        for project in projects:
            # Style the version type
            file_info = project.current_version
            if file_info is None:
                continue

            latest_upgradable = project.get_latest_type(file_info.version_type)
            # show update status.
            if latest_upgradable:
                is_outdated = latest_upgradable.version_id != file_info.version_id
                if is_outdated and latest_upgradable.version_name:
                    status_display = f"[yellow]⚠ {latest_upgradable.version_name}[/yellow]"
                else:
                    status_display = "[green]✓ up-to-date[/green]"
            else:
                status_display = "[dim]? unknown[/dim]"

            compatibility_info = get_compatibility_info(game_version, file_info.game_versions)
            version_display = f"{compatibility_info} {file_info.version_name}"

            table.add_row(
                project.project_id,
                project.name,
                version_display,
                get_release_type_string(file_info.version_type),
                file_info.release_date.strftime("%Y-%m-%d"),
                status_display,
            )
        self.print(table)

    def print_unidentified_plugins_table(self, unidentified_data: list[InstallationTable]):

        table = Table(
            title="[bold yellow]Unidentified Plugins[/bold yellow]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("File Name", style="bold yellow")
        table.add_column("SHA1", style="dim")
        table.add_column("Size", style="cyan", justify="right")

        # for filename, sha1, file_size in unidentified_data:
        for installation in unidentified_data:
            filename = installation.filename
            sha1 = installation.sha1
            file_size = installation.filesize
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
        self.print(table)

    def print_version_detail_panel(self, file_info: FileInfo, title: str = "Version Details"):
        groups = []

        info = [("Version Name", file_info.version_name),
                ("Project ID", file_info.project_id),
                ("Version Type", get_release_type_string(file_info.version_type)),
                ("Release Date", file_info.release_date.strftime("%Y-%m-%d %H:%M:%S")),
                ("MC Versions", ", ".join(file_info.game_versions)),
                ("Download URL", file_info.url)]

        groups.append(get_key_value_table(info))

        if file_info.hashes:
            groups.append(Text.from_markup(""))
            groups.append(Text.from_markup("[yellow]Hashes:[/yellow]"))
            for hash_type, hash_value in file_info.hashes.items():
                groups.append(Text.from_markup(f"  {hash_type.upper()}: [dim]{hash_value[:16]}...[/dim]"))

        if file_info.description:
            groups.append(Text.from_markup(""))
            groups.append(Text.from_markup("[yellow]Description:[/yellow]"))
            groups.append(Text.from_markup(file_info.description))

        self.print(Panel(
            Group(*groups),
            title=f"[bold green]{title}[/bold green]",
            border_style="green",
            box=box.ROUNDED,
        ))

    def print_version_table(self, versions_data: list[FileInfo], title: str = "Available Versions", game_version: str | None = None):
        table = Table(
            title=f"[bold cyan]{title}[/bold cyan]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Veresion")
        table.add_column("Type", style="white")
        table.add_column("Release Date", style="white")
        table.add_column("PaperMC", style="dim")
        for file_info in versions_data:
            mc_versions = ", ".join(reversed(file_info.game_versions[-3:]))  # Show last 3 versions in reverse (newest first)
            if len(file_info.game_versions) > 3:
                mc_versions += f" +{len(file_info.game_versions) - 3} more"

            type_style = get_release_type_string(file_info.version_type)
            # Check compatibility with game version
            compatibility_icon = get_compatibility_info(game_version, file_info.game_versions)
            table.add_row(
                file_info.version_id,
                f"{compatibility_icon} {file_info.version_name}",
                type_style,
                file_info.release_date.strftime("%Y-%m-%d"),
                mc_versions,
            )
        self.print(table)

    def print_search_results_table(self, results: list[SearchResult]):
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

        for result in results:
            # Truncate description if too long
            desc = result.description or ""

            table.add_row(
                result.project_id,
                result.project_name,
                result.author,
                f"{result.downloads:,}",
                desc,
            )
        self.print(table)



console = PpmConsole()




def compute_compatibility_score(supported_versions: list[str], current_version: str | None) -> int:
    # Parse game version into parts

    if current_version and supported_versions:
        game_parts = current_version.split(".")

        # Check each supported version for best match
        best_match = 0  # 0 = no match, 2 = two digits, 3 = three digits
        for mc_version in supported_versions:
            mc_parts = mc_version.split(".")

            # Check for three-digit match
            if len(game_parts) >= 3 and len(mc_parts) >= 3 and game_parts[:3] == mc_parts[:3]:
                best_match = 3
                break

            # Check for two-digit match
            if len(game_parts) >= 2 and len(mc_parts) >= 2 and game_parts[:2] == mc_parts[:2]:
                best_match = max(best_match, 2)
        return best_match
    return -1

def get_compatibility_info(current_version: str | None, supported_versions: list[str], full: bool = False) -> str:
    score = compute_compatibility_score(supported_versions, current_version)
    if full:
        if score == 3:
            return f"[green]✓ Compatible[/green] with server version [cyan]{current_version}[/cyan]"
        if score == 2:
            return f"[yellow]⚠ Partially Compatible[/yellow] (supports [cyan]{', '.join(supported_versions)}[/cyan], server is [cyan]{current_version}[/cyan])"
        if score == 1:
            return f"[red]✗ Not Compatible[/red] (supports [cyan]{', '.join(supported_versions)}[/cyan], server is [cyan]{current_version}[/cyan])"
        return "[dim]? Compatibility Unknown[/dim]"
    if score == 3:
        return "[green]✓[/green]"
    if score == 2:
        return "[yellow]⚠[/yellow]"
    if score == 1:
        return "[red]✗[/red]"
    return "[dim]?[/dim]"

def get_release_type_string(version_type: str) -> str:
    if version_type == "RELEASE":
        return "[green]●[/green] RELEASE"
    if version_type == "BETA":
        return "[yellow]●[/yellow] BETA"
    if version_type == "ALPHA":
        return "[red]●[/red] ALPHA"
    return f"[dim]●[/dim] {version_type}"
