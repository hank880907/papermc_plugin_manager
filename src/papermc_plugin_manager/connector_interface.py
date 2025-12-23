from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from logzero import logger
from semantic_version import Version


def sanitize_version_name(version_name: str) -> str:
    """sometimes version name could be prefixed with non-numeric charactors. This function removes it."""
    for c in version_name:
        if c.isdigit():
            index = version_name.index(c)
            return version_name[index:]
    return version_name


@dataclass
class FileInfo:
    version_id: str
    project_id: str
    version_name: str
    version_type: str
    release_date: datetime
    game_versions: list[str]
    sha1: str
    url: str
    description: str = ""
    hashes: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.version_name} ({self.version_type}) - Released on {self.release_date.strftime('%Y-%m-%d')}"


def release_type_weights(release_type: str) -> int:
    weights = {
        "release": 3,
        "beta": 2,
        "alpha": 1
    }
    return weights.get(release_type.lower(), 0)

@dataclass
class ProjectInfo:
    source: str
    project_id: str
    name: str
    author: str
    description: str | None
    downloads: int
    versions: dict[str, FileInfo] = field(default_factory=dict)
    current_version: FileInfo | None = None
    installation_type: str = "RELEASE"

    def __str__(self) -> str:
        return f"{self.name} by {self.author} (ID: {self.project_id})"

    @staticmethod
    def is_newer_than(info: FileInfo, other: FileInfo) -> bool:
        """Compare two FileInfo objects to determine if info is newer than other.

        Args:
            info: The FileInfo to check if newer
            other: The FileInfo to compare against

        Returns:
            bool: True if info is newer than other, False otherwise
        """

        try:
            info_version_str = sanitize_version_name(info.version_name)
            other_version_str = sanitize_version_name(other.version_name)

            info_version = Version.coerce(info_version_str)
            other_version = Version.coerce(other_version_str)

            return info_version > other_version
        except ValueError:
            # If version parsing fails, fall back to date comparison
            logger.debug(f"Version parsing failed for '{info.version_name}' or '{other.version_name}'. Falling back to date comparison.")
            return info.release_date > other.release_date

    def get_latest_type(self, release_type: str = "release") -> FileInfo | None:
        latest_release = None
        for file_info in self.versions.values():
            if file_info.version_type.lower() == release_type.lower() and (latest_release is None or self.is_newer_than(file_info, latest_release)):
                latest_release = file_info
        return latest_release

    def get_latest_type_weighted(self, min_release_type: str) -> FileInfo | None:
        latest = None
        min_weight = release_type_weights(min_release_type)
        for file_info in self.versions.values():
            if release_type_weights(file_info.version_type) >= min_weight:
                if latest is None or self.is_newer_than(file_info, latest):
                    latest = file_info
        return latest

    def get_latest(self) -> FileInfo | None:
        latest = None
        for file_info in self.versions.values():
            if latest is None or self.is_newer_than(file_info, latest):
                latest = file_info
        return latest

    def get_version(self, version: str) -> FileInfo | None:
        for file_info in self.versions.values():
            if file_info.version_name == version or file_info.version_id == version:
                return file_info
        return None
    
    def is_out_dated(self) -> Optional[FileInfo]:
        if not self.current_version:
            return None
        latest = self.get_latest_type_weighted(self.installation_type)
        if not latest:
            return None
        if latest.version_id != self.current_version.version_id:
            return latest
        return None


@dataclass
class SearchResult:
    project_id: str
    project_name: str
    author: str
    downloads: int
    description: str


class ConnectorInterface(ABC):
    @abstractmethod
    def get_download_link(self, file: FileInfo) -> str:
        """Get a download link for a given file"""
        pass

    @abstractmethod
    def query(self, name: str, mc_version: str | None = None, limit: int = 5) -> list[SearchResult]:
        """Query information about a plugin by its name."""
        pass

    @abstractmethod
    def get_project_info(self, id: str) -> ProjectInfo:
        """Get detailed information about a project by its ID."""
        pass

    @abstractmethod
    def get_file_info(self, id: str) -> FileInfo:
        """Get detailed information about a file by its ID."""
        pass

    def refresh_cache(self):
        """Refresh any internal caches if applicable."""
        raise NotImplementedError("Cache refresh not implemented for this connector.")


def get_connector(connector: str, **kwargs) -> ConnectorInterface:
    """Factory method to get the appropriate connector

    Args:
        connector (str): The name of the connector to retrieve.

    Raises:
        ValueError: If no connector is found for the given name.

    Returns:
        DownloadInterface: An instance of the appropriate connector.
    """

    # Factory method to get the appropriate connector
    # search the subclasses of ConnectorInterface recursively
    def all_subclasses(cls):
        return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in all_subclasses(c)])
    for subclass in all_subclasses(ConnectorInterface):
        if subclass.__name__.lower() == connector.lower():
            return subclass(**kwargs)
    raise ValueError(f"No connector found for {connector}")

def list_connectors() -> list[str]:
    """List all available connector names.

    Returns:
        list[str]: A list of available connector names.
    """
    connector_names = []
    def all_subclasses(cls):
        return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in all_subclasses(c)])
    for subclass in all_subclasses(ConnectorInterface):
        connector_names.append(subclass.__name__)
    return connector_names
