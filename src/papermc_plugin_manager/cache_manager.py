"""Cache management for PaperMC Plugin Manager."""

import os
from dataclasses import asdict, fields
from datetime import datetime, timedelta

import yaml
from logzero import logger

from .config import Config
from .connector_interface import FileInfo, ProjectInfo
from .exceptions import CacheException


def _serialize_file_info(file_info: FileInfo) -> dict:
    """Convert FileInfo to a cache-friendly dict.

    Args:
        file_info: FileInfo object to serialize

    Returns:
        Dictionary with serialized data
    """
    data = asdict(file_info)
    # Convert datetime to ISO format string
    if isinstance(data["release_date"], datetime):
        data["release_date"] = data["release_date"].isoformat()
    return data


def _deserialize_file_info(data: dict) -> FileInfo:
    """Convert cache dict back to FileInfo object.

    Args:
        data: Dictionary with cached file info

    Returns:
        FileInfo object
    """
    # Convert ISO format string back to datetime
    if isinstance(data.get("release_date"), str):
        data = data.copy()
        data["release_date"] = datetime.fromisoformat(data["release_date"])

    # Filter to only FileInfo fields (automatically from dataclass)
    file_info_fields = {f.name for f in fields(FileInfo)}
    filtered_data = {k: v for k, v in data.items() if k in file_info_fields}
    return FileInfo(**filtered_data)


def _serialize_project_info(project_info: ProjectInfo) -> dict:
    """Convert ProjectInfo to a cache-friendly dict.

    Args:
        project_info: ProjectInfo object to serialize

    Returns:
        Dictionary with serialized data
    """
    data = asdict(project_info)
    # Serialize nested FileInfo objects in versions dict
    data["versions"] = {
        version_id: _serialize_file_info(file_info) for version_id, file_info in project_info.versions.items()
    }
    return data


def _deserialize_project_info(data: dict) -> ProjectInfo:
    """Convert cache dict back to ProjectInfo object.

    Args:
        data: Dictionary with cached project info

    Returns:
        ProjectInfo object
    """
    data = data.copy()
    # Deserialize nested FileInfo objects in versions dict
    data["versions"] = {
        version_id: _deserialize_file_info(file_data) for version_id, file_data in data.get("versions", {}).items()
    }
    return ProjectInfo(**data)


class CacheManager:
    """Manages cache operations for plugins, projects, and unidentified files."""

    def __init__(self, cache_file_path: str = None):
        """Initialize cache manager.

        Args:
            cache_file_path: Path to cache file (defaults to Config.get_cache_file())
        """
        self.cache_file = cache_file_path or Config.get_cache_file()
        self.cache_data = self._load()
        logger.debug(f"CacheManager initialized with file: {self.cache_file}")

    def _load(self) -> dict:
        """Load cache from YAML file.

        Returns:
            Dictionary with 'plugins', 'projects', and 'unidentified' sections
        """
        if not os.path.exists(self.cache_file):
            logger.debug("Cache file not found, creating new cache")
            return {"plugins": {}, "projects": {}, "unidentified": {}}

        try:
            with open(self.cache_file) as f:
                cache = yaml.safe_load(f)
                if cache is None:
                    logger.warning("Cache file is empty, initializing new cache")
                    return {"plugins": {}, "projects": {}, "unidentified": {}}

                # Ensure all sections exist
                if "plugins" not in cache:
                    cache["plugins"] = {}
                if "projects" not in cache:
                    cache["projects"] = {}
                if "unidentified" not in cache:
                    cache["unidentified"] = {}

                logger.info(
                    f"Loaded cache: {len(cache['plugins'])} plugins, {len(cache['projects'])} projects, {len(cache['unidentified'])} unidentified"
                )
                return cache
        except Exception as e:
            logger.error(f"Failed to load cache: {e}", exc_info=True)
            raise CacheException("load", str(e))

    def save(self):
        """Save cache to YAML file."""
        try:
            # Create directory if it doesn't exist
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir)

            with open(self.cache_file, "w") as f:
                yaml.dump(self.cache_data, f, default_flow_style=False, sort_keys=False)
            logger.debug("Cache saved successfully")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}", exc_info=True)
            raise CacheException("save", str(e))

    def get_plugin_cache(self, filename: str) -> dict | None:
        """Get cached data for a plugin file.

        Args:
            filename: Name of the plugin file

        Returns:
            Cache entry dict or None if not found
        """
        return self.cache_data["plugins"].get(filename)

    def cache_plugin(
        self,
        filename: str,
        sha1: str,
        file_info: FileInfo,
        is_outdated: bool,
        project_name: str,
        latest_version: str = None,
    ):
        """Cache plugin file information.

        Args:
            filename: Name of the plugin file
            sha1: SHA1 hash of the file
            file_info: FileInfo object
            is_outdated: Whether plugin is outdated
            project_name: Name of the project
            latest_version: Latest version if outdated
        """
        # Serialize FileInfo using helper function
        cache_entry = _serialize_file_info(file_info)

        # Add plugin-specific metadata
        cache_entry["sha1"] = sha1
        cache_entry["project_name"] = project_name
        cache_entry["is_outdated"] = is_outdated
        cache_entry["last_checked"] = datetime.now().isoformat()

        if latest_version:
            cache_entry["latest_version"] = latest_version

        self.cache_data["plugins"][filename] = cache_entry
        logger.debug(f"Cached plugin: {filename} ({project_name})")

    def get_project_cache(self, project_id: str) -> dict | None:
        """Get cached data for a project.

        Args:
            project_id: Project ID

        Returns:
            Cache entry dict or None if not found
        """
        return self.cache_data["projects"].get(project_id)

    def cache_project(self, project_id: str, project_info: ProjectInfo):
        """Cache project information.

        Args:
            project_id: Project ID
            project_info: ProjectInfo object
        """
        # Serialize ProjectInfo using helper function (handles nested FileInfo objects)
        cache_entry = _serialize_project_info(project_info)
        cache_entry["last_checked"] = datetime.now().isoformat()

        self.cache_data["projects"][project_id] = cache_entry
        logger.debug(f"Cached project: {project_id} ({project_info.name})")

    def get_unidentified_cache(self, filename: str) -> dict | None:
        """Get cached data for an unidentified plugin.

        Args:
            filename: Name of the plugin file

        Returns:
            Cache entry dict or None if not found
        """
        return self.cache_data["unidentified"].get(filename)

    def cache_unidentified(self, filename: str, sha1: str, size: int):
        """Cache unidentified plugin information.

        Args:
            filename: Name of the plugin file
            sha1: SHA1 hash
            size: File size in bytes
        """
        cache_entry = {
            "sha1": sha1,
            "size": size,
            "last_checked": datetime.now().isoformat(),
        }
        self.cache_data["unidentified"][filename] = cache_entry
        logger.debug(f"Cached unidentified plugin: {filename}")

    def cleanup_stale_entries(self, current_files: set[str]):
        """Remove cache entries for files that no longer exist.

        Args:
            current_files: Set of currently existing filenames
        """
        # Clean plugins
        stale_plugins = [f for f in self.cache_data["plugins"] if f not in current_files]
        for filename in stale_plugins:
            del self.cache_data["plugins"][filename]
            logger.debug(f"Removed stale plugin cache: {filename}")

        # Clean unidentified
        stale_unidentified = [f for f in self.cache_data["unidentified"] if f not in current_files]
        for filename in stale_unidentified:
            del self.cache_data["unidentified"][filename]
            logger.debug(f"Removed stale unidentified cache: {filename}")

        if stale_plugins or stale_unidentified:
            logger.info(f"Cleaned {len(stale_plugins)} stale plugins, {len(stale_unidentified)} unidentified")

    def clear_expired_entries(self):
        """Remove expired cache entries based on Config expiry times."""
        now = datetime.now()
        removed_count = 0

        # Clear expired projects (24 hours)
        project_expiry = timedelta(hours=Config.CACHE_PROJECT_EXPIRY_HOURS)
        expired_projects = []
        for project_id, project_data in self.cache_data["projects"].items():
            try:
                last_checked = datetime.fromisoformat(project_data.get("last_checked", ""))
                if now - last_checked > project_expiry:
                    expired_projects.append(project_id)
            except (ValueError, KeyError):
                expired_projects.append(project_id)  # Remove corrupted entries

        for project_id in expired_projects:
            del self.cache_data["projects"][project_id]
            removed_count += 1

        # Clear expired unidentified (30 days)
        unidentified_expiry = timedelta(days=Config.CACHE_UNIDENTIFIED_EXPIRY_DAYS)
        expired_unidentified = []
        for filename, data in self.cache_data["unidentified"].items():
            try:
                last_checked = datetime.fromisoformat(data.get("last_checked", ""))
                if now - last_checked > unidentified_expiry:
                    expired_unidentified.append(filename)
            except (ValueError, KeyError):
                expired_unidentified.append(filename)

        for filename in expired_unidentified:
            del self.cache_data["unidentified"][filename]
            removed_count += 1

        if removed_count > 0:
            logger.info(f"Removed {removed_count} expired cache entries")

        return removed_count

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "plugins": len(self.cache_data["plugins"]),
            "projects": len(self.cache_data["projects"]),
            "unidentified": len(self.cache_data["unidentified"]),
            "cache_file": self.cache_file,
            "file_size": 0,
        }

        if os.path.exists(self.cache_file):
            stats["file_size"] = os.path.getsize(self.cache_file)

        return stats

    def clear_all(self):
        """Clear entire cache."""
        self.cache_data = {"plugins": {}, "projects": {}, "unidentified": {}}
        logger.info("Cache cleared")
