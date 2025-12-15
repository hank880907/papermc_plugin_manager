from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict
from colorama import Fore, Style, init
from datetime import datetime


@dataclass
class FileInfo:
    version_id: str
    project_id: str
    version_name: str
    version_type: str
    release_date: datetime
    mc_versions: list[str]
    hashes: Dict[str, str]
    url: str
    description: str = ""
    
    def __str__(self) -> str:
        return f"{self.version_name} ({self.version_type}) - Released on {self.release_date.strftime('%Y-%m-%d')}"


@dataclass
class ProjectInfo:
    name: str
    id: str
    author: str
    description: Optional[str]
    downloads: int
    latest: Optional[str] = None
    latest_release: Optional[str] = None
    versions: Dict[str, FileInfo] = field(default_factory=dict)
    
    
    def __str__(self) -> str:
        return f"{self.name} by {self.author} (ID: {self.id})"
    
    def complete_description(self) -> str:
        init(autoreset=True)
        
        # Calculate the longest label for alignment
        labels = ["ID:", "Author:", "Downloads:", "Supported Versions:"]
        max_label_len = max(len(label) for label in labels)
        
        lines = [
            f"{Fore.GREEN}{Style.BRIGHT}{self.name}",
            f"{Fore.YELLOW}{'ID:':<{max_label_len}} {Fore.WHITE}{self.id}",
            f"{Fore.YELLOW}{'Author:':<{max_label_len}} {Fore.WHITE}{self.author}",
            f"{Fore.YELLOW}{'Downloads:':<{max_label_len}} {Fore.WHITE}{self.downloads:,}",
            f"{Fore.YELLOW}{'latest:':<{max_label_len}} {Fore.WHITE}{self.latest if self.latest else 'N/A'}",
            f"{Fore.YELLOW}{'latest release:':<{max_label_len}} {Fore.WHITE}{self.latest_release if self.latest_release else 'N/A'}"
        ]
        if self.description:
            lines.append(f"{Fore.YELLOW}Description:")
            lines.append(f"{Fore.WHITE}{self.description}")
        return "\n".join(lines)
    




class ConnectorInterface(ABC):
    
    @abstractmethod
    def download(self, file: FileInfo, dest: str) -> None:
        """Download a file from the given id to the specified destination."""
        pass
    
    @abstractmethod
    def query(self, name: str, mc_version: Optional[str] = None, limit: int = 5) -> Dict[str, ProjectInfo]:
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
        return set(cls.__subclasses__()).union(
            [s for c in cls.__subclasses__() for s in all_subclasses(c)])
    for subclass in all_subclasses(ConnectorInterface):
        if subclass.__name__.lower() == connector.lower():
            return subclass(**kwargs)
    raise ValueError(f"No connector found for {connector}")


@dataclass
class CliContext:
    game_version: str
    default_platform: str
    connector: ConnectorInterface