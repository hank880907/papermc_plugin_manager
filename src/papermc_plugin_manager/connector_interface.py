from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from semantic_version import Version
from logzero import logger


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

    def __str__(self) -> str:
        return f"{self.version_name} ({self.version_type}) - Released on {self.release_date.strftime('%Y-%m-%d')}"


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
            # Strip 'v' prefix if present before parsing
            info_version_str = info.version_name.lstrip('v') if info.version_name.lower().startswith('v') else info.version_name
            other_version_str = other.version_name.lstrip('v') if other.version_name.lower().startswith('v') else other.version_name
            
            info_version = Version.coerce(info_version_str)
            other_version = Version.coerce(other_version_str)
            
            return info_version > other_version
        except ValueError:
            # If version parsing fails, fall back to date comparison
            logger.warning(f"Version parsing failed for '{info.version_name}' or '{other.version_name}'. Falling back to date comparison.")
            return info.release_date > other.release_date

    def get_latest_type(self, release_type: str = "release") -> FileInfo | None:
        latest_release = None
        for file_info in self.versions.values():
            if file_info.version_type.lower() == release_type.lower():
                if latest_release is None or self.is_newer_than(file_info, latest_release):
                    latest_release = file_info
        return latest_release

    def get_latest(self) -> FileInfo | None:
        latest = None
        for file_info in self.versions.values():
            if latest is None or self.is_newer_than(file_info, latest):
                latest = file_info
        return latest
    

class ConnectorInterface(ABC):
    @abstractmethod
    def download(self, file: FileInfo, dest: str):
        """Download a file from the given id to the specified destination.

        Yields:
            tuple: (bytes_downloaded, total_size, chunk, filename) for each chunk downloaded
        """
        pass

    @abstractmethod
    def query(self, name: str, mc_version: str | None = None, limit: int = 5) -> dict[str, ProjectInfo]:
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
