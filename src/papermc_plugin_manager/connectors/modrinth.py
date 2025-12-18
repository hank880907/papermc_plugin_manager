from functools import lru_cache
from requests import HTTPError
from importlib.metadata import version
from typing import Callable, Optional


from ..connector_interface import ConnectorInterface, FileInfo, ProjectInfo, SearchResult
from ..exceptions import PluginNotFoundException
from ..utils import default_feedback_cb
from .modrinth_models import Project, SearchResponse, TeamMember, Version


def version_to_file_info(version: Version) -> FileInfo:
    hashes = {
        "sha1": version.files[0].hashes.sha1,
        "sha512": version.files[0].hashes.sha512,
    }
    return FileInfo(
        project_id=version.project_id,
        version_id=version.id,
        version_name=version.version_number,
        version_type=version.version_type.name,
        release_date=version.date_published,
        game_versions=version.game_versions,
        sha1=version.files[0].hashes.sha1,
        url=version.files[0].url,
        description=version.changelog or "",
        hashes=hashes
    )


class Modrinth(ConnectorInterface):
    API_BASE = "https://api.modrinth.com/v2"

    @property
    def HEADERS(self):
        """Get headers with configurable User-Agent."""
        return {
            "User-Agent": f"papermc-plugin-manager/{version('papermc_plugin_manager')}",
        }

    def get_download_link(self, file: FileInfo) -> str:
        return Version.get(file.version_id).files[0].url
        
    def get_file_info(self, id: str) -> FileInfo:
        return self._get_file_info_cached(id)
    
    def query(self, name: str, mc_version: str | None = None, limit: int = 5) -> list[SearchResult]:
        return self._query_cached(name, mc_version, limit)
    
    def get_project_info(self, id: str) -> ProjectInfo:
        return self._get_project_info_cached(id)

    @lru_cache(maxsize=128)
    def _get_project_info_cached(self, id: str, cb: Callable[[str], None] = default_feedback_cb) -> ProjectInfo:
        try:
            modrinth_project = Project.get(id)
        except HTTPError as e:
            raise PluginNotFoundException(f"Project with ID {id} not found on Modrinth.") from e
        
        cb(f"Fetching team members info for project {modrinth_project.title} ({id})...")
        members = TeamMember.list_for_project(id)
        owner = "Unknown"
        for member in members:
            if member.is_owner:
                owner = member.user.username
                break

        plugin_info = ProjectInfo(
            source="Modrinth",
            name=modrinth_project.title,
            project_id=modrinth_project.id,
            author=owner,
            description=modrinth_project.description,
            downloads=modrinth_project.downloads,
        )
        cb(f"Fetching versions info for project {modrinth_project.title} ({id})...")
        versions = Version.list_for_project(id, loaders=["paper"])
        if not versions:
            return plugin_info
        for version in versions:
            file_info = version_to_file_info(version)
            plugin_info.versions[file_info.version_id] = file_info
        return plugin_info
    
    @lru_cache(maxsize=128)
    def _query_cached(self, name: str, mc_version: Optional[str], limit: int) -> list[SearchResult]:
        facets = []
        facets.append(["categories:paper"])
        facets.append(["project_type:plugin"])
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        response = SearchResponse.search(name, limit=limit, facets=facets)
        results = []
        for hit in response.hits:
            result = SearchResult(hit.project_id, hit.title, hit.author, hit.downloads, hit.description)
            results.append(result)
        return results


    @lru_cache(maxsize=128)
    def _get_file_info_cached(self, id: str) -> FileInfo:
        try:
            version = Version.get(id)
            return version_to_file_info(version)
        except HTTPError as e:
            pass

        try:
            version = Version.get_by_hash(id)
            return version_to_file_info(version)
        except HTTPError as e:
            pass

        raise PluginNotFoundException(f"File with ID or hash {id} not found on Modrinth.")
