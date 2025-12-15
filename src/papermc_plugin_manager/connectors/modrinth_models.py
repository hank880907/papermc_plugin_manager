"""
Pydantic models for Modrinth API responses.

Based on Modrinth API v2 documentation: https://docs.modrinth.com/api
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
import requests
import json


# ============== API Configuration ==============

class ModrinthAPIConfig:
    """Configuration for Modrinth API requests."""
    BASE_URL: str = "https://api.modrinth.com/v2"
    HEADERS: Dict[str, str] = {
        "User-Agent": "papermc-plugin-manager/1.0.0 (contact@example.com)",
    }
    TIMEOUT: int = 30
    
    @classmethod
    def set_user_agent(cls, user_agent: str) -> None:
        """Set a custom User-Agent header."""
        cls.HEADERS["User-Agent"] = user_agent
    
    @classmethod
    def api_get(cls, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request to the Modrinth API."""
        url = f"{cls.BASE_URL}{path}"
        response = requests.get(url, params=params, headers=cls.HEADERS, timeout=cls.TIMEOUT)
        
        # Handle rate limiting
        if response.status_code == 429:
            reset = response.headers.get("X-Ratelimit-Reset", "?")
            raise RuntimeError(f"Rate limited by Modrinth API. Retry after ~{reset} seconds.")
        
        response.raise_for_status()
        return response.json()


class ProjectType(str, Enum):
    """Type of project on Modrinth."""
    MOD = "mod"
    MODPACK = "modpack"
    RESOURCEPACK = "resourcepack"
    SHADER = "shader"
    PLUGIN = "plugin"
    DATAPACK = "datapack"


class ProjectStatus(str, Enum):
    """Current status of a project."""
    APPROVED = "approved"
    ARCHIVED = "archived"
    REJECTED = "rejected"
    DRAFT = "draft"
    UNLISTED = "unlisted"
    LISTED = "listed"
    PROCESSING = "processing"
    WITHHELD = "withheld"
    SCHEDULED = "scheduled"
    PRIVATE = "private"
    UNKNOWN = "unknown"


class VersionType(str, Enum):
    """Type of version release."""
    RELEASE = "release"
    BETA = "beta"
    ALPHA = "alpha"


class DependencyType(str, Enum):
    """Type of dependency relationship."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    INCOMPATIBLE = "incompatible"
    EMBEDDED = "embedded"


class MonetizationStatus(str, Enum):
    """Monetization status of a project."""
    MONETIZED = "monetized"
    DEMONETIZED = "demonetized"
    FORCE_DEMONETIZED = "force-demonetized"


# ============== License Models ==============

class License(BaseModel):
    """License information for a project."""
    id: str
    name: str
    url: Optional[str] = None


# ============== Donation Models ==============

class DonationUrl(BaseModel):
    """Donation platform information."""
    id: str
    platform: str
    url: str


# ============== Gallery Models ==============

class GalleryImage(BaseModel):
    """Gallery image information."""
    url: str
    featured: bool
    title: Optional[str] = None
    description: Optional[str] = None
    created: datetime
    ordering: int


# ============== Version Models ==============

class VersionFileHash(BaseModel):
    """File hash information."""
    sha512: str
    sha1: str


class VersionFile(BaseModel):
    """File information in a version."""
    hashes: VersionFileHash
    url: str
    filename: str
    primary: bool
    size: int
    file_type: Optional[str] = None


class VersionDependency(BaseModel):
    """Dependency information for a version."""
    version_id: Optional[str] = None
    project_id: Optional[str] = None
    file_name: Optional[str] = None
    dependency_type: DependencyType


class Version(BaseModel):
    """Complete version information from the Modrinth API."""
    id: str
    project_id: str
    author_id: str
    featured: bool
    name: str
    version_number: str
    changelog: Optional[str] = None
    changelog_url: Optional[str] = None
    date_published: datetime
    downloads: int
    version_type: VersionType
    status: ProjectStatus
    requested_status: Optional[ProjectStatus] = None
    files: List[VersionFile]
    dependencies: List[VersionDependency] = Field(default_factory=list)
    game_versions: List[str]
    loaders: List[str]

    @property
    def primary_file(self) -> Optional[VersionFile]:
        """Get the primary file from the version."""
        for file in self.files:
            if file.primary:
                return file
        return self.files[0] if self.files else None
    

    @classmethod
    def get(cls, version_id: str) -> "Version":
        """
        Get a specific version by its ID.
        
        Args:
            version_id: The ID of the version to fetch
            
        Returns:
            Version object with complete information
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        data = ModrinthAPIConfig.api_get(f"/version/{version_id}")
        return cls(**data)
    

    @classmethod
    def get_by_hash(cls, hash: str, algorithm: str = "sha1") -> "Version":
        """
        Get a version by its file hash.
        
        Args:
            hash: The file hash
            algorithm: Hash algorithm used (sha1 or sha512)
            
        Returns:
            Version object
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        data = ModrinthAPIConfig.api_get(f"/version_file/{hash}", params={"algorithm": algorithm})
        return cls(**data)

    @classmethod
    def list_for_project(
        cls,
        project_id: str,
        loaders: Optional[List[str]] = None,
        game_versions: Optional[List[str]] = None,
        featured: Optional[bool] = None
    ) -> List["Version"]:
        """
        List all versions for a project with optional filters.
        
        Args:
            project_id: The project ID or slug
            loaders: Filter by loaders (e.g., ["paper", "spigot"])
            game_versions: Filter by game versions (e.g., ["1.20.1"])
            featured: Filter by featured status
            
        Returns:
            List of Version objects
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {}
        if loaders:
            params["loaders"] = json.dumps(loaders)
        if game_versions:
            params["game_versions"] = json.dumps(game_versions)
        if featured is not None:
            params["featured"] = str(featured).lower()
        
        data = ModrinthAPIConfig.api_get(f"/project/{project_id}/version", params=params)
        return [cls(**version_data) for version_data in data]
    
    def download_primary_file(self, dest_dir: str = "."):
        """
        Download the primary file of this version.
        
        Args:
            dest_dir: Destination directory for the download
            
        Yields:
            tuple: (bytes_downloaded, total_size, chunk, filename) for each chunk
            
        Raises:
            ValueError: If no primary file is found
            requests.HTTPError: If the download fails
        """
        import os
        
        primary = self.primary_file
        if not primary:
            raise ValueError("No primary file found for this version")
        
        filepath = os.path.join(dest_dir, primary.filename)
        
        response = requests.get(
            primary.url,
            headers=ModrinthAPIConfig.HEADERS,
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        bytes_downloaded = 0
        
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    yield (bytes_downloaded, total_size, chunk, primary.filename)
        
        return filepath


# ============== Project Models ==============

class Project(BaseModel):
    """Complete project information from GET /project/{id} endpoint."""
    
    # Basic identification
    id: str = Field(alias="id")
    slug: str
    project_type: ProjectType
    team: str
    
    # Display information
    title: str
    description: str
    body: str
    body_url: Optional[str] = None
    
    # Publication info
    published: datetime
    updated: datetime
    approved: Optional[datetime] = None
    queued: Optional[datetime] = None
    
    # Status and visibility
    status: ProjectStatus
    requested_status: Optional[ProjectStatus] = None
    moderator_message: Optional[Dict[str, Any]] = None
    
    # License
    license: License
    
    # Download and version info
    client_side: str
    server_side: str
    downloads: int
    followers: int
    categories: List[str]
    additional_categories: List[str] = Field(default_factory=list)
    game_versions: List[str]
    loaders: List[str]
    versions: List[str]
    
    # Icon and gallery
    icon_url: Optional[str] = None
    gallery: List[GalleryImage] = Field(default_factory=list)
    
    # Links
    issues_url: Optional[str] = None
    source_url: Optional[str] = None
    wiki_url: Optional[str] = None
    discord_url: Optional[str] = None
    donation_urls: List[DonationUrl] = Field(default_factory=list)
    
    # Color for theming
    color: Optional[int] = None
    
    # Thread for comments/discussions
    thread_id: Optional[str] = None
    
    # Monetization
    monetization_status: Optional[MonetizationStatus] = None
    
    model_config = ConfigDict(populate_by_name=True, use_enum_values=False)
    
    @classmethod
    def get(cls, project_id_or_slug: str) -> "Project":
        """
        Get a project by its ID or slug.
        
        Args:
            project_id_or_slug: The project ID or slug
            
        Returns:
            Project object with complete information
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        data = ModrinthAPIConfig.api_get(f"/project/{project_id_or_slug}")
        return cls(**data)
    
    @classmethod
    def get_multiple(cls, project_ids: List[str]) -> List["Project"]:
        """
        Get multiple projects by their IDs.
        
        Args:
            project_ids: List of project IDs
            
        Returns:
            List of Project objects
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        params = {"ids": json.dumps(project_ids)}
        data = ModrinthAPIConfig.api_get("/projects", params=params)
        return [cls(**project_data) for project_data in data]
    
    def get_versions(
        self,
        loaders: Optional[List[str]] = None,
        game_versions: Optional[List[str]] = None,
        featured: Optional[bool] = None
    ) -> List[Version]:
        """
        Get all versions for this project.
        
        Args:
            loaders: Filter by loaders
            game_versions: Filter by game versions
            featured: Filter by featured status
            
        Returns:
            List of Version objects
        """
        return Version.list_for_project(self.id, loaders, game_versions, featured)
    
    def get_team_members(self) -> List["TeamMember"]:
        """
        Get team members for this project.
        
        Returns:
            List of TeamMember objects
        """
        return TeamMember.list_for_project(self.id)


# ============== Search Models ==============

class SearchHit(BaseModel):
    """Single search result from the search endpoint."""
    
    # Identification
    project_id: str
    slug: str
    project_type: ProjectType
    
    # Display info
    title: str
    description: str
    author: str
    
    # Categories and compatibility
    categories: List[str]
    display_categories: List[str] = Field(default_factory=list)
    versions: List[str]
    
    # Stats
    downloads: int
    follows: int
    
    # Icon
    icon_url: Optional[str] = None
    
    # Dates
    date_created: datetime
    date_modified: datetime
    
    # Latest version info (optional, may not always be present)
    latest_version: Optional[str] = None
    
    # License
    license: str
    
    # Gallery images
    gallery: List[str] = Field(default_factory=list)
    
    # Featured status
    featured_gallery: Optional[str] = None
    
    # Color for theming
    color: Optional[int] = None
    
    # Monetization
    monetization_status: Optional[MonetizationStatus] = None
    
    # Server/client side requirements
    client_side: str
    server_side: str


class SearchResponse(BaseModel):
    """Response from the /search endpoint."""
    hits: List[SearchHit]
    offset: int
    limit: int
    total_hits: int
    
    @classmethod
    def search(
        cls,
        query: str = "",
        facets: Optional[List[List[str]]] = None,
        index: str = "relevance",
        offset: int = 0,
        limit: int = 10
    ) -> "SearchResponse":
        """
        Search for projects on Modrinth.
        
        Args:
            query: Search query string
            facets: List of facet filters (e.g., [["categories:paper"], ["project_type:plugin"]])
            index: Sort index - "relevance", "downloads", "follows", "newest", or "updated"
            offset: Pagination offset
            limit: Number of results to return (max 100)
            
        Returns:
            SearchResponse object with hits and pagination info
            
        Raises:
            requests.HTTPError: If the API request fails
            
        Example:
            >>> results = SearchResponse.search(
            ...     query="worldedit",
            ...     facets=[["categories:paper"], ["project_type:plugin"]],
            ...     limit=5
            ... )
        """
        params = {
            "query": query,
            "index": index,
            "offset": offset,
            "limit": min(limit, 100)  # API max is 100
        }
        
        if facets:
            params["facets"] = json.dumps(facets)
        
        data = ModrinthAPIConfig.api_get("/search", params=params)
        return cls(**data)
    
    @classmethod
    def search_plugins(
        cls,
        query: str = "",
        loader: str = "paper",
        game_version: Optional[str] = None,
        limit: int = 10,
        offset: int = 0
    ) -> "SearchResponse":
        """
        Search specifically for plugins with common filters.
        
        Args:
            query: Search query string
            loader: Server loader (paper, spigot, bukkit, etc.)
            game_version: Minecraft version filter (e.g., "1.20.1")
            limit: Number of results
            offset: Pagination offset
            
        Returns:
            SearchResponse object
        """
        facets = [
            ["project_type:plugin"],
            [f"categories:{loader}"]
        ]
        
        if game_version:
            facets.append([f"versions:{game_version}"])
        
        return cls.search(query=query, facets=facets, limit=limit, offset=offset)


# ============== Team Models ==============

class TeamMemberUser(BaseModel):
    """User information in team member."""
    id: str
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created: datetime
    role: str


class TeamMember(BaseModel):
    """Team member information."""
    team_id: str
    user: TeamMemberUser
    role: str
    permissions: Optional[int] = None
    accepted: bool
    payouts_split: Optional[int] = None
    ordering: int
    
    @classmethod
    def list_for_project(cls, project_id: str) -> List["TeamMember"]:
        """
        Get all team members for a project.
        
        Args:
            project_id: The project ID or slug
            
        Returns:
            List of TeamMember objects
            
        Raises:
            requests.HTTPError: If the API request fails
        """
        data = ModrinthAPIConfig.api_get(f"/project/{project_id}/members")
        return [cls(**member_data) for member_data in data]
    
    @property
    def is_owner(self) -> bool:
        """Check if this team member is the project owner."""
        return self.role.lower() == "owner"


# ============== Helper Models ==============

class VersionFilters(BaseModel):
    """Filters for querying project versions."""
    loaders: Optional[List[str]] = None
    game_versions: Optional[List[str]] = None
    featured: Optional[bool] = None


class SearchFilters(BaseModel):
    """Filters for searching projects."""
    query: str = ""
    facets: Optional[List[List[str]]] = None
    index: str = "relevance"  # or "downloads", "follows", "newest", "updated"
    offset: int = 0
    limit: int = 10
    
    def add_facet(self, facet: str) -> None:
        """Add a single facet to the facets list."""
        if self.facets is None:
            self.facets = []
        self.facets.append([facet])
    
    def to_api_params(self) -> Dict[str, Any]:
        """Convert filters to API query parameters."""
        import json
        params = {
            "query": self.query,
            "index": self.index,
            "offset": self.offset,
            "limit": self.limit,
        }
        if self.facets:
            params["facets"] = json.dumps(self.facets)
        return params
