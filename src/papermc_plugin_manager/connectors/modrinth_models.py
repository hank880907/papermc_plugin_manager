"""
Pydantic models for Modrinth API responses.

Based on Modrinth API v2 documentation: https://docs.modrinth.com/api
"""

import contextlib
import json
from datetime import datetime
from enum import Enum
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field

# ============== API Configuration ==============


class ModrinthAPIConfig:
    """Configuration for Modrinth API requests."""

    BASE_URL: str = "https://api.modrinth.com/v2"
    HEADERS: dict[str, str] = {
        "User-Agent": "papermc-plugin-manager/1.0.0 (contact@example.com)",
    }
    TIMEOUT: int = 30

    @classmethod
    def set_user_agent(cls, user_agent: str) -> None:
        """Set a custom User-Agent header."""
        cls.HEADERS["User-Agent"] = user_agent

    @classmethod
    def api_get(cls, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
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
    url: str | None = None


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
    title: str | None = None
    description: str | None = None
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
    file_type: str | None = None


class VersionDependency(BaseModel):
    """Dependency information for a version."""

    version_id: str | None = None
    project_id: str | None = None
    file_name: str | None = None
    dependency_type: DependencyType


class Version(BaseModel):
    """Complete version information from the Modrinth API."""

    id: str
    project_id: str
    author_id: str
    featured: bool
    name: str
    version_number: str
    changelog: str | None = None
    changelog_url: str | None = None
    date_published: datetime
    downloads: int
    version_type: VersionType
    status: ProjectStatus
    requested_status: ProjectStatus | None = None
    files: list[VersionFile]
    dependencies: list[VersionDependency] = Field(default_factory=list)
    game_versions: list[str]
    loaders: list[str]

    @property
    def primary_file(self) -> VersionFile | None:
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
        loaders: list[str] | None = None,
        game_versions: list[str] | None = None,
        featured: bool | None = None,
    ) -> list["Version"]:
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
        Download the primary file of this version and verify its integrity.

        Args:
            dest_dir: Destination directory for the download

        Yields:
            tuple: (bytes_downloaded, total_size, chunk, filename) for each chunk

        Raises:
            ValueError: If no primary file is found or hash verification fails
            requests.HTTPError: If the download fails
        """
        import os

        from ..console import console
        from ..utils import verify_file_hash

        primary = self.primary_file
        if not primary:
            raise ValueError("No primary file found for this version")

        filepath = os.path.join(dest_dir, primary.filename)
        expected_sha1 = primary.hashes.sha1

        response = requests.get(primary.url, headers=ModrinthAPIConfig.HEADERS, stream=True, timeout=120)
        response.raise_for_status()

        # Get total file size
        total_size = int(response.headers.get("content-length", 0))
        bytes_downloaded = 0

        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bytes_downloaded += len(chunk)
                    yield (bytes_downloaded, total_size, chunk, primary.filename)

        # Verify the downloaded file's SHA1 hash
        if not verify_file_hash(filepath, expected_sha1):
            # Remove corrupted file
            with contextlib.suppress(Exception):
                os.remove(filepath)
            raise ValueError(f"Downloaded file failed SHA1 verification. Expected: {expected_sha1}")

        console.print("[dim]✓ File integrity verified[/dim]")
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
    body_url: str | None = None

    # Publication info
    published: datetime
    updated: datetime
    approved: datetime | None = None
    queued: datetime | None = None

    # Status and visibility
    status: ProjectStatus
    requested_status: ProjectStatus | None = None
    moderator_message: dict[str, Any] | None = None

    # License
    license: License

    # Download and version info
    client_side: str
    server_side: str
    downloads: int
    followers: int
    categories: list[str]
    additional_categories: list[str] = Field(default_factory=list)
    game_versions: list[str]
    loaders: list[str]
    versions: list[str]

    # Icon and gallery
    icon_url: str | None = None
    gallery: list[GalleryImage] = Field(default_factory=list)

    # Links
    issues_url: str | None = None
    source_url: str | None = None
    wiki_url: str | None = None
    discord_url: str | None = None
    donation_urls: list[DonationUrl] = Field(default_factory=list)

    # Color for theming
    color: int | None = None

    # Thread for comments/discussions
    thread_id: str | None = None

    # Monetization
    monetization_status: MonetizationStatus | None = None

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
    def get_multiple(cls, project_ids: list[str]) -> list["Project"]:
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
        self, loaders: list[str] | None = None, game_versions: list[str] | None = None, featured: bool | None = None
    ) -> list[Version]:
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

    def get_team_members(self) -> list["TeamMember"]:
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
    categories: list[str]
    display_categories: list[str] = Field(default_factory=list)
    versions: list[str]

    # Stats
    downloads: int
    follows: int

    # Icon
    icon_url: str | None = None

    # Dates
    date_created: datetime
    date_modified: datetime

    # Latest version info (optional, may not always be present)
    latest_version: str | None = None

    # License
    license: str

    # Gallery images
    gallery: list[str] = Field(default_factory=list)

    # Featured status
    featured_gallery: str | None = None

    # Color for theming
    color: int | None = None

    # Monetization
    monetization_status: MonetizationStatus | None = None

    # Server/client side requirements
    client_side: str
    server_side: str


class SearchResponse(BaseModel):
    """Response from the /search endpoint."""

    hits: list[SearchHit]
    offset: int
    limit: int
    total_hits: int

    @classmethod
    def search(
        cls,
        query: str = "",
        facets: list[list[str]] | None = None,
        index: str = "relevance",
        offset: int = 0,
        limit: int = 10,
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
            "limit": min(limit, 100),  # API max is 100
        }

        if facets:
            params["facets"] = json.dumps(facets)

        data = ModrinthAPIConfig.api_get("/search", params=params)
        return cls(**data)

    @classmethod
    def search_plugins(
        cls, query: str = "", loader: str = "paper", game_version: str | None = None, limit: int = 10, offset: int = 0
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
        facets = [["project_type:plugin"], [f"categories:{loader}"]]

        if game_version:
            facets.append([f"versions:{game_version}"])

        return cls.search(query=query, facets=facets, limit=limit, offset=offset)


# ============== Team Models ==============


class TeamMemberUser(BaseModel):
    """User information in team member."""

    id: str
    username: str
    name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created: datetime
    role: str


class TeamMember(BaseModel):
    """Team member information."""

    team_id: str
    user: TeamMemberUser
    role: str
    permissions: int | None = None
    accepted: bool
    payouts_split: int | None = None
    ordering: int

    @classmethod
    def list_for_project(cls, project_id: str) -> list["TeamMember"]:
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

    loaders: list[str] | None = None
    game_versions: list[str] | None = None
    featured: bool | None = None


class SearchFilters(BaseModel):
    """Filters for searching projects."""

    query: str = ""
    facets: list[list[str]] | None = None
    index: str = "relevance"  # or "downloads", "follows", "newest", "updated"
    offset: int = 0
    limit: int = 10

    def add_facet(self, facet: str) -> None:
        """Add a single facet to the facets list."""
        if self.facets is None:
            self.facets = []
        self.facets.append([facet])

    def to_api_params(self) -> dict[str, Any]:
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
