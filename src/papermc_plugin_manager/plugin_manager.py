import os
from pathlib import Path

from logzero import logger
from requests import HTTPError

from .cache_manager import CacheManager, _deserialize_file_info, _deserialize_project_info
from .config import Config
from .connector_interface import ConnectorInterface, FileInfo, ProjectInfo
from .console import console
from .utils import get_sha1
from .version_utils import is_newer_version


class PluginManager:
    def __init__(self, connector: ConnectorInterface, game_version: str):
        self.connector = connector
        self.game_version = game_version
        self.cache_manager = CacheManager()

        logger.debug(f"PluginManager initialized for game version: {game_version}")

        plugins_dir = Config.get_plugins_dir()
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)
            logger.info(f"Created plugins directory: {plugins_dir}")

    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare semantic versions. Returns True if current is older than latest.

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            True if current < latest, False otherwise
        """
        return is_newer_version(current, latest)

    def fuzzy_find_project(self, name: str) -> tuple[bool, ProjectInfo] | None:
        """Fuzzy find a project by its name or ID.

        First checks local cache (by ID and name), then queries the connector.
        returns a tuple (is_exact_match, ProjectInfo) if found, else None.
        """

        # First try to find in cache by project_id
        if name in self.cache_manager.cache_data.get("projects", {}):
            console.print(f"[dim]Found {name} in cache[/dim]")
            try:
                cached_project = self.cache_manager.cache_data["projects"][name]
                project_info = _deserialize_project_info(cached_project)
                return True, project_info
            except Exception:
                # Cache corrupted, fall through to network lookup
                pass

        # Try to find in cache by project name (case-insensitive)
        name_lower = name.lower()
        for _project_id, cached_project in self.cache_manager.cache_data.get("projects", {}).items():
            try:
                if cached_project.get("name", "").lower() == name_lower:
                    console.print(f"[dim]Found {name} in cache (by name)[/dim]")
                    project_info = _deserialize_project_info(cached_project)
                    return True, project_info
            except Exception:
                # Skip corrupted cache entry
                continue

        try:
            result = self.connector.get_project_info(name)
            return True, result
        except HTTPError:
            pass

        console.print(f"[dim]Plugin {name} not found by ID, searching by name...[/dim]")
        results = self.connector.query(name, self.game_version)
        for _project_id, project_info in results.items():
            return False, project_info

        console.print(f"[yellow]No results found for plugin {name}.[/yellow]")
        return None

    def get_installed_plugin_by_project_id(self, project_id: str) -> tuple[str, FileInfo] | None:
        """Check if a plugin with given project_id is installed.

        Returns:
            Tuple of (filename, FileInfo) if found, None otherwise
        """
        plugins_dir = Path(Config.get_plugins_dir())
        if not plugins_dir.exists():
            return None

        for file in plugins_dir.iterdir():
            if not file.is_file():
                continue

            # Check cache first
            cache_entry = self.cache_manager.get_plugin_cache(file.name)
            if cache_entry and cache_entry.get("project_id") == project_id:
                try:
                    file_info = _deserialize_file_info(cache_entry)
                    return (file.name, file_info)
                except Exception:
                    pass

        return None

    def upgrade_plugin(self, plugin: FileInfo):
        """Upgrade an existing plugin to a new version.

        Finds the existing plugin by project_id and updates it if the new version is newer.
        Removes the old file and downloads the new one.

        Yields:
            tuple: (bytes_downloaded, total_size, chunk, filename) for each chunk
        """
        plugins_dir = Path(Config.get_plugins_dir())
        old_file_to_remove = None

        if not plugins_dir.exists():
            console.print("[red]✗ Plugins directory not found[/red]")
            return

        # Find existing version of this plugin
        for file in plugins_dir.iterdir():
            if not file.is_file():
                continue

            file_sha1 = get_sha1(file)
            target_sha1 = plugin.hashes.get("sha1", "")

            # Check if exact same version is already installed
            if target_sha1 and file_sha1 == target_sha1:
                console.print(f"[yellow]⚠ Plugin already up-to-date: {file.name} ({plugin.version_name})[/yellow]")
                return

            # Check if this is the same plugin (different version)
            try:
                existing_file_info = self.connector.get_file_info(file_sha1)
                if existing_file_info.project_id == plugin.project_id:
                    # Same plugin found
                    if self._compare_versions(existing_file_info.version_name, plugin.version_name):
                        # Existing version is older, update it
                        console.print(
                            f"[cyan]ℹ Found older version: {file.name} ({existing_file_info.version_name})[/cyan]"
                        )
                        console.print(f"[green]→ Upgrading to {plugin.version_name}[/green]")
                        old_file_to_remove = file
                        break
                    else:
                        # Existing version is same or newer
                        console.print(
                            f"[yellow]⚠ Plugin already at version {existing_file_info.version_name}: {file.name}[/yellow]"
                        )
                        console.print(f"[dim]Target version {plugin.version_name} is not newer[/dim]")
                        return
            except Exception:
                # If we can't get file info, continue checking other files
                pass

        # No existing version found
        if not old_file_to_remove:
            console.print("[yellow]⚠ Plugin not currently installed. Use 'install' command instead.[/yellow]")
            return

        # Remove old version
        if old_file_to_remove.exists():
            try:
                old_file_to_remove.unlink()
                console.print(f"[dim]✓ Removed old version: {old_file_to_remove.name}[/dim]")
                # Remove from cache too
                if old_file_to_remove.name in self.cache_manager.cache_data["plugins"]:
                    del self.cache_manager.cache_data["plugins"][old_file_to_remove.name]
                    self.cache_manager.save()
            except Exception as e:
                console.print(f"[yellow]⚠ Could not remove old file: {e}[/yellow]")
                return

        # Download new version
        yield from self.connector.download(plugin, "plugins")

    def install_plugin(self, plugin: FileInfo, auto_upgrade: bool = True, allow_replace: bool = False):
        """Install a plugin and yield download progress.

        Checks if the plugin is already installed by comparing SHA1 hashes.
        If same version exists, skips installation.
        If different version exists:
          - If allow_replace=True, replaces with the specified version (allows downgrades)
          - If auto_upgrade=True, upgrades to newer version only

        Args:
            plugin: FileInfo object for the plugin to install
            auto_upgrade: If True, automatically upgrade existing older versions
            allow_replace: If True, replace any existing version with the specified one (enables downgrades)

        Yields:
            tuple: (bytes_downloaded, total_size, chunk, filename) for each chunk
        """
        plugins_dir = Path(Config.get_plugins_dir())
        target_sha1 = plugin.hashes.get("sha1", "")

        if plugins_dir.exists():
            for file in plugins_dir.iterdir():
                if not file.is_file():
                    continue

                file_sha1 = get_sha1(file)

                # Check if exact same version is already installed
                if target_sha1 and file_sha1 == target_sha1:
                    console.print(f"[yellow]⚠ Plugin already installed: {file.name}[/yellow]")
                    console.print(f"[dim]SHA1: {file_sha1}[/dim]")
                    return  # Don't yield anything, just return

                # Check if this is the same plugin (different version)
                try:
                    existing_file_info = self.connector.get_file_info(file_sha1)
                    if existing_file_info.project_id == plugin.project_id:
                        # Same plugin found
                        if allow_replace:
                            # User specified a specific version, allow replace (including downgrade)
                            version_compare = self._compare_versions(
                                existing_file_info.version_name, plugin.version_name
                            )
                            if version_compare:
                                action = "Upgrading"
                            else:
                                action = (
                                    "Downgrading"
                                    if self._compare_versions(plugin.version_name, existing_file_info.version_name)
                                    else "Replacing"
                                )

                            console.print(
                                f"[cyan]ℹ Found existing version: {file.name} ({existing_file_info.version_name})[/cyan]"
                            )
                            console.print(f"[green]→ {action} to {plugin.version_name}[/green]")

                            # Remove old file
                            try:
                                file.unlink()
                                console.print(f"[dim]✓ Removed old version: {file.name}[/dim]")
                                if file.name in self.cache_manager.cache_data["plugins"]:
                                    del self.cache_manager.cache_data["plugins"][file.name]
                                    self.cache_manager.save()
                            except Exception as e:
                                console.print(f"[yellow]⚠ Could not remove old file: {e}[/yellow]")
                                return
                            break
                        elif auto_upgrade:
                            # Auto-upgrade mode, use upgrade logic
                            yield from self.upgrade_plugin(plugin)
                            return
                        else:
                            # Neither replace nor upgrade allowed
                            console.print(
                                f"[yellow]⚠ Plugin already installed: {file.name} ({existing_file_info.version_name})[/yellow]"
                            )
                            console.print("[dim]Use --version flag to replace with a specific version[/dim]")
                            return
                except Exception:
                    # If we can't get file info, continue with normal install
                    pass

        # Proceed with download (new installation or after replacement)
        yield from self.connector.download(plugin, "plugins")

    def get_installed_plugins(
        self, plugins_dir: str = None, force_refresh: bool = False, status_callback=None
    ) -> tuple[list[tuple[str, FileInfo, bool, str, str, str | None]], list[tuple[str, str, int]]]:
        """Get list of installed plugins with their information.

        This method handles all caching transparently. It will:
        - Check cache for each plugin file (by SHA1)
        - Fetch fresh data if cache miss or force_refresh=True
        - Check if plugins are outdated
        - Update cache automatically
        - Clean up stale cache entries
        - Track unidentified plugins separately

        Args:
            plugins_dir: Directory containing plugin files (defaults to Config.get_plugins_dir())
            force_refresh: If True, bypass cache and fetch fresh data
            status_callback: Optional callback function for status updates (e.g., status.update)

        Returns:
            Tuple of (identified_plugins, unidentified_plugins):
            - identified_plugins: List of tuples (filename, FileInfo, is_outdated, project_name, project_id, latest_version)
            - unidentified_plugins: List of tuples (filename, sha1, file_size)
        """
        if plugins_dir is None:
            plugins_dir = Config.get_plugins_dir()
        files = os.listdir(plugins_dir)
        plugins_data = []
        unidentified_plugins = []
        cache_updated = False

        # Initialize unidentified section in cache if not exists
        if "unidentified" not in self.cache_manager.cache_data:
            self.cache_manager.cache_data["unidentified"] = {}

        for file in files:
            path = Path(plugins_dir) / file
            if not path.is_file():
                continue

            if status_callback:
                status_callback(f"[bold cyan]Analyzing {file}...")

            sha1 = get_sha1(path)

            # Check if we have cached data with matching SHA
            cache_entry = self.cache_manager.get_plugin_cache(file)
            use_cache = not force_refresh and cache_entry is not None and cache_entry.get("sha1") == sha1

            # Check if this is an unidentified plugin in cache
            unidentified_entry = self.cache_manager.get_unidentified_cache(file)
            if unidentified_entry:
                if status_callback:
                    status_callback(f"[dim]Using cached data for unidentified {file}...[/dim]")
                file_size = unidentified_entry.get("size", 0)
                unidentified_plugins.append((file, sha1, file_size))
                continue

            if use_cache:
                # Use cached data
                if status_callback:
                    status_callback(f"[dim]Using cached data for {file}...[/dim]")
                try:
                    file_info = _deserialize_file_info(cache_entry)
                    is_outdated = cache_entry.get("is_outdated", False)
                    project_name = cache_entry.get("project_name", file)
                    project_id = cache_entry.get("project_id", "")
                    latest_version = cache_entry.get("latest_version")
                    plugins_data.append((file, file_info, is_outdated, project_name, project_id, latest_version))
                    continue
                except Exception:
                    # If cache read fails, fetch fresh data
                    use_cache = False

            if not use_cache:
                # Fetch fresh data
                try:
                    if status_callback:
                        status_callback(f"[bold yellow]Fetching info for {file}...")
                    file_info = self.connector.get_file_info(sha1)

                    # Check if outdated by comparing with latest version of same type
                    if status_callback:
                        status_callback(f"[bold magenta]Checking for updates for {file}...")
                    is_outdated = False
                    project_name = file  # Default to filename
                    latest_version = None

                    try:
                        project_info = self.connector.get_project_info(file_info.project_id)
                        project_name = project_info.name  # Get the actual project name

                        # Cache the project info using cache_manager
                        self.cache_manager.cache_project(
                            project_id=file_info.project_id, project_info=project_info
                        )

                        # Find latest version of the same type
                        latest_version_id = None
                        if file_info.version_type == "RELEASE" and project_info.latest_release:
                            latest_version_id = project_info.latest_release
                        elif file_info.version_type in ["BETA", "ALPHA"] and project_info.latest:
                            # For non-release types, compare with latest overall
                            latest_version_id = project_info.latest

                        if latest_version_id and latest_version_id != file_info.version_id:
                            latest_file = project_info.versions.get(latest_version_id)
                            if latest_file and latest_file.version_type == file_info.version_type:
                                is_outdated = self._compare_versions(file_info.version_name, latest_file.version_name)
                                if is_outdated:
                                    latest_version = latest_file.version_name
                    except Exception:
                        # If we can't check for updates, assume it's not outdated
                        pass

                    plugins_data.append(
                        (file, file_info, is_outdated, project_name, file_info.project_id, latest_version)
                    )

                    # Update cache using cache_manager
                    self.cache_manager.cache_plugin(
                        filename=file,
                        sha1=sha1,
                        file_info=file_info,
                        is_outdated=is_outdated,
                        project_name=project_name,
                        latest_version=latest_version,
                    )
                    cache_updated = True

                except Exception:
                    # Plugin not found in Modrinth - add to unidentified list
                    if status_callback:
                        status_callback(f"[dim]Plugin {file} not found in Modrinth[/dim]")
                    file_size = path.stat().st_size
                    unidentified_plugins.append((file, sha1, file_size))
                    # Cache as unidentified using cache_manager
                    self.cache_manager.cache_unidentified(filename=file, sha1=sha1, size=file_size)
                    cache_updated = True

        # Remove stale entries from cache (files that no longer exist)
        files_set = set(files)
        if self.cache_manager.cleanup_stale_entries(files_set):
            cache_updated = True

        # Save cache if it was updated
        if cache_updated:
            self.cache_manager.save()

        return plugins_data, unidentified_plugins

    def remove_plugin(self, name: str) -> tuple[str, str] | None:
        """Remove a plugin by project ID or name.

        Args:
            name: Project ID or project name to search for

        Returns:
            Tuple of (filename, project_name) if found, None if not found
        """
        # First try to find the plugin by project ID or name
        result = self.fuzzy_find_project(name)
        if not result:
            return None

        _, project_info = result

        # Find installed plugin with this project ID
        installed = self.get_installed_plugin_by_project_id(project_info.id)
        if not installed:
            return None

        filename, file_info = installed

        # Delete the file
        plugin_path = Path(Config.get_plugins_dir()) / filename
        if plugin_path.exists():
            plugin_path.unlink()

            # Remove from cache
            if filename in self.cache_manager.cache_data.get("plugins", {}):
                del self.cache_manager.cache_data["plugins"][filename]
                self.cache_manager.save()

            return (filename, project_info.name)

        return None
