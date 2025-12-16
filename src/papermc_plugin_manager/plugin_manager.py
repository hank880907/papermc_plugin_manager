from requests import HTTPError
import os
import yaml
from typing import Tuple, List
from pathlib import Path
from datetime import datetime

from .connector_interface import ConnectorInterface, ProjectInfo, FileInfo
from .console import console
from .utils import get_sha1


class PluginManager:
    CACHE_FILE = "papermc_plugin_manager.yaml"

    def __init__(self, connector: ConnectorInterface, game_version: str):
        self.connector = connector
        self.game_version = game_version
        self.cache = self._load_cache()

        if os.path.exists("plugins") is False:
            os.makedirs("plugins")

    def _load_cache(self) -> dict:
        """Load cache from YAML file."""
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    cache = yaml.safe_load(f)
                    if cache is None:
                        return {'plugins': {}, 'projects': {}}
                    # Ensure both sections exist
                    if 'plugins' not in cache:
                        cache['plugins'] = {}
                    if 'projects' not in cache:
                        cache['projects'] = {}
                    return cache
            except Exception:
                return {'plugins': {}, 'projects': {}}
        return {'plugins': {}, 'projects': {}}

    def _save_cache(self):
        """Save cache to YAML file."""
        try:
            with open(self.CACHE_FILE, 'w') as f:
                yaml.dump(self.cache, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            console.print(f"[yellow]⚠ Failed to save cache: {e}[/yellow]")

    def _cache_file_info(self, file_name: str, sha1: str, file_info: FileInfo, is_outdated: bool, project_name: str) -> dict:
        """Create cache entry for a file."""
        return {
            'sha1': sha1,
            'version_id': file_info.version_id,
            'project_id': file_info.project_id,
            'project_name': project_name,
            'version_name': file_info.version_name,
            'version_type': file_info.version_type,
            'release_date': file_info.release_date.isoformat(),
            'mc_versions': file_info.mc_versions,
            'url': file_info.url,
            'description': file_info.description,
            'hashes': file_info.hashes,
            'is_outdated': is_outdated,
            'last_checked': datetime.now().isoformat(),
        }

    def _file_info_from_cache(self, cache_entry: dict) -> FileInfo:
        """Reconstruct FileInfo from cache entry."""
        return FileInfo(
            version_id=cache_entry['version_id'],
            project_id=cache_entry['project_id'],
            version_name=cache_entry['version_name'],
            version_type=cache_entry['version_type'],
            release_date=datetime.fromisoformat(cache_entry['release_date']),
            mc_versions=cache_entry['mc_versions'],
            hashes=cache_entry['hashes'],
            url=cache_entry['url'],
            description=cache_entry.get('description', ''),
        )

    def _cache_project_info(self, project_id: str, project_info: ProjectInfo) -> dict:
        """Create cache entry for a project."""
        # Serialize versions dict
        versions_cache = {}
        for version_id, file_info in project_info.versions.items():
            versions_cache[version_id] = {
                'version_id': file_info.version_id,
                'project_id': file_info.project_id,
                'version_name': file_info.version_name,
                'version_type': file_info.version_type,
                'release_date': file_info.release_date.isoformat(),
                'mc_versions': file_info.mc_versions,
                'url': file_info.url,
                'description': file_info.description,
                'hashes': file_info.hashes,
            }
        
        return {
            'name': project_info.name,
            'id': project_info.id,
            'author': project_info.author,
            'description': project_info.description,
            'downloads': project_info.downloads,
            'latest': project_info.latest,
            'latest_release': project_info.latest_release,
            'versions': versions_cache,
            'last_checked': datetime.now().isoformat(),
        }

    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare semantic versions. Returns True if current is older than latest."""
        try:
            # Clean version strings (remove 'v' prefix, handle special cases)
            current_clean = current.lstrip('v').split('-')[0].split('+')[0]
            latest_clean = latest.lstrip('v').split('-')[0].split('+')[0]
            
            # Split into parts
            current_parts = [int(x) for x in current_clean.split('.') if x.isdigit()]
            latest_parts = [int(x) for x in latest_clean.split('.') if x.isdigit()]
            
            # Pad with zeros to make same length
            max_len = max(len(current_parts), len(latest_parts))
            current_parts += [0] * (max_len - len(current_parts))
            latest_parts += [0] * (max_len - len(latest_parts))
            
            # Compare
            return current_parts < latest_parts
        except (ValueError, IndexError):
            # If we can't parse versions, assume it's not outdated
            return False

    def fuzzy_find_project(self, name: str) -> Tuple[bool, ProjectInfo] | None:
        """Fuzzy find a project by its name or ID.
        
        First checks local cache (by ID and name), then queries the connector.
        returns a tuple (is_exact_match, ProjectInfo) if found, else None.
        """
        def reconstruct_project_from_cache(cached_project: dict) -> ProjectInfo:
            """Helper to reconstruct ProjectInfo from cache entry."""
            # Reconstruct versions dict
            versions = {}
            for version_id, version_data in cached_project.get('versions', {}).items():
                versions[version_id] = FileInfo(
                    version_id=version_data['version_id'],
                    project_id=version_data['project_id'],
                    version_name=version_data['version_name'],
                    version_type=version_data['version_type'],
                    release_date=datetime.fromisoformat(version_data['release_date']),
                    mc_versions=version_data['mc_versions'],
                    hashes=version_data['hashes'],
                    url=version_data['url'],
                    description=version_data.get('description', ''),
                )
            
            return ProjectInfo(
                name=cached_project['name'],
                id=cached_project['id'],
                author=cached_project['author'],
                description=cached_project.get('description', ''),
                downloads=cached_project.get('downloads', 0),
                latest=cached_project.get('latest'),
                latest_release=cached_project.get('latest_release'),
                versions=versions,
            )
        
        # First try to find in cache by project_id
        if name in self.cache.get('projects', {}):
            console.print(f"[dim]Found {name} in cache[/dim]")
            try:
                cached_project = self.cache['projects'][name]
                project_info = reconstruct_project_from_cache(cached_project)
                return True, project_info
            except Exception:
                # Cache corrupted, fall through to network lookup
                pass
        
        # Try to find in cache by project name (case-insensitive)
        name_lower = name.lower()
        for project_id, cached_project in self.cache.get('projects', {}).items():
            try:
                if cached_project.get('name', '').lower() == name_lower:
                    console.print(f"[dim]Found {name} in cache (by name)[/dim]")
                    project_info = reconstruct_project_from_cache(cached_project)
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
        for project_id, project_info in results.items():
            return False, project_info
        
        console.print(f"[yellow]No results found for plugin {name}.[/yellow]")
        return None
    
    def get_installed_plugin_by_project_id(self, project_id: str) -> Tuple[str, FileInfo] | None:
        """Check if a plugin with given project_id is installed.
        
        Returns:
            Tuple of (filename, FileInfo) if found, None otherwise
        """
        plugins_dir = Path("./plugins")
        if not plugins_dir.exists():
            return None
        
        for file in plugins_dir.iterdir():
            if not file.is_file():
                continue
            
            # Check cache first
            if file.name in self.cache.get('plugins', {}):
                cache_entry = self.cache['plugins'][file.name]
                if cache_entry.get('project_id') == project_id:
                    try:
                        file_info = self._file_info_from_cache(cache_entry)
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
        plugins_dir = Path("./plugins")
        old_file_to_remove = None
        
        if not plugins_dir.exists():
            console.print(f"[red]✗ Plugins directory not found[/red]")
            return
        
        # Find existing version of this plugin
        for file in plugins_dir.iterdir():
            if not file.is_file():
                continue
            
            file_sha1 = get_sha1(file)
            target_sha1 = plugin.hashes.get('sha1', '')
            
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
                        console.print(f"[cyan]ℹ Found older version: {file.name} ({existing_file_info.version_name})[/cyan]")
                        console.print(f"[green]→ Upgrading to {plugin.version_name}[/green]")
                        old_file_to_remove = file
                        break
                    else:
                        # Existing version is same or newer
                        console.print(f"[yellow]⚠ Plugin already at version {existing_file_info.version_name}: {file.name}[/yellow]")
                        console.print(f"[dim]Target version {plugin.version_name} is not newer[/dim]")
                        return
            except Exception:
                # If we can't get file info, continue checking other files
                pass
        
        # No existing version found
        if not old_file_to_remove:
            console.print(f"[yellow]⚠ Plugin not currently installed. Use 'install' command instead.[/yellow]")
            return
        
        # Remove old version
        if old_file_to_remove.exists():
            try:
                old_file_to_remove.unlink()
                console.print(f"[dim]✓ Removed old version: {old_file_to_remove.name}[/dim]")
                # Remove from cache too
                if old_file_to_remove.name in self.cache['plugins']:
                    del self.cache['plugins'][old_file_to_remove.name]
                    self._save_cache()
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
        plugins_dir = Path("./plugins")
        target_sha1 = plugin.hashes.get('sha1', '')
        
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
                            version_compare = self._compare_versions(existing_file_info.version_name, plugin.version_name)
                            if version_compare:
                                action = "Upgrading"
                            else:
                                action = "Downgrading" if self._compare_versions(plugin.version_name, existing_file_info.version_name) else "Replacing"
                            
                            console.print(f"[cyan]ℹ Found existing version: {file.name} ({existing_file_info.version_name})[/cyan]")
                            console.print(f"[green]→ {action} to {plugin.version_name}[/green]")
                            
                            # Remove old file
                            try:
                                file.unlink()
                                console.print(f"[dim]✓ Removed old version: {file.name}[/dim]")
                                if file.name in self.cache['plugins']:
                                    del self.cache['plugins'][file.name]
                                    self._save_cache()
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
                            console.print(f"[yellow]⚠ Plugin already installed: {file.name} ({existing_file_info.version_name})[/yellow]")
                            console.print(f"[dim]Use --version flag to replace with a specific version[/dim]")
                            return
                except Exception:
                    # If we can't get file info, continue with normal install
                    pass
        
        # Proceed with download (new installation or after replacement)
        yield from self.connector.download(plugin, "plugins")

    def get_installed_plugins(self, plugins_dir: str = "./plugins", force_refresh: bool = False, status_callback=None) -> List[Tuple[str, FileInfo, bool, str]]:
        """Get list of installed plugins with their information.
        
        This method handles all caching transparently. It will:
        - Check cache for each plugin file (by SHA1)
        - Fetch fresh data if cache miss or force_refresh=True
        - Check if plugins are outdated
        - Update cache automatically
        - Clean up stale cache entries
        
        Args:
            plugins_dir: Directory containing plugin files
            force_refresh: If True, bypass cache and fetch fresh data
            status_callback: Optional callback function for status updates (e.g., status.update)
        
        Returns:
            List of tuples: (filename, FileInfo, is_outdated, project_name)
        """
        files = os.listdir(plugins_dir)
        plugins_data = []
        cache_updated = False
        
        for file in files:
            path = Path(plugins_dir) / file
            if not path.is_file():
                continue
            
            if status_callback:
                status_callback(f"[bold cyan]Analyzing {file}...")
            
            sha1 = get_sha1(path)
            
            # Check if we have cached data with matching SHA
            use_cache = (
                not force_refresh and
                file in self.cache['plugins'] and
                self.cache['plugins'][file].get('sha1') == sha1
            )
            
            if use_cache:
                # Use cached data
                if status_callback:
                    status_callback(f"[dim]Using cached data for {file}...[/dim]")
                try:
                    cache_entry = self.cache['plugins'][file]
                    file_info = self._file_info_from_cache(cache_entry)
                    is_outdated = cache_entry.get('is_outdated', False)
                    project_name = cache_entry.get('project_name', file)
                    plugins_data.append((file, file_info, is_outdated, project_name))
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
                    
                    try:
                        project_info = self.connector.get_project_info(file_info.project_id)
                        project_name = project_info.name  # Get the actual project name
                        
                        # Cache the project info
                        self.cache['projects'][file_info.project_id] = self._cache_project_info(file_info.project_id, project_info)
                        
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
                    except Exception:
                        # If we can't check for updates, assume it's not outdated
                        pass
                    
                    plugins_data.append((file, file_info, is_outdated, project_name))
                    
                    # Update cache
                    self.cache['plugins'][file] = self._cache_file_info(file, sha1, file_info, is_outdated, project_name)
                    cache_updated = True
                    
                except Exception as e:
                    console.print(f"[yellow]⚠ Could not fetch info for {file}: {e}[/yellow]")
        
        # Remove stale entries from cache (files that no longer exist)
        files_set = set(files)
        stale_files = [cached_file for cached_file in self.cache['plugins'].keys() if cached_file not in files_set]
        for cached_file in stale_files:
            del self.cache['plugins'][cached_file]
            cache_updated = True
        
        # Save cache if it was updated
        if cache_updated:
            self._save_cache()
        
        return plugins_data
