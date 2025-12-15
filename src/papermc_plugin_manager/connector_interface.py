from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict
from colorama import Fore, Style, init
from datetime import datetime


@dataclass
class PluginVersionInfo:
    version_id: str
    project_id: str
    version_name: str
    version_type: str
    release_date: datetime
    mc_versions: list[str]
    hashes: dict[str, str]
    download_url: str
    
    def __str__(self) -> str:
        return f"{self.version_name}"
    

@dataclass
class PluginInfo:
    name: str
    id: str
    author: str
    description: Optional[str]
    downloads: int
    supported_versions: list[str]
    stable_version: Optional[PluginVersionInfo] = None
    latest_version: Optional[PluginVersionInfo] = None
    
    
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
            f"{Fore.YELLOW}{'Stable Version:':<{max_label_len}} {Fore.WHITE}{self.stable_version if self.stable_version else 'N/A'}",
            f"{Fore.YELLOW}{'Latest Version:':<{max_label_len}} {Fore.WHITE}{self.latest_version if self.latest_version else 'N/A'}"
        ]
        if self.description:
            lines.append(f"{Fore.YELLOW}Description:")
            lines.append(f"{Fore.WHITE}{self.description}")
        lines.append(f"{Fore.YELLOW}{'Supported Versions:':<{max_label_len}} {Fore.WHITE}{', '.join(self.supported_versions)}")        
        return "\n".join(lines)
    

@dataclass
class CliContext:
    game_version: str


class ConnectorInterface(ABC):
    
    @abstractmethod
    def download(self, id) -> None:
        """Download a file from the given URL to the specified destination."""
        pass
    
    @abstractmethod
    def query(self, name: str, byid: bool = False) -> Dict[str, PluginInfo]:
        """Query information about a plugin by its name."""
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