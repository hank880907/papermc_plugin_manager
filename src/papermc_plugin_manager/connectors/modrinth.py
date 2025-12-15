from ..connector_interface import ConnectorInterface, ProjectInfo, FileInfo

from .modrinth_models import Version, SearchResponse, Project, TeamMember

import requests
import json
from typing import Dict, Optional
from functools import lru_cache


def version_to_file_info(version: Version) -> FileInfo:
    return FileInfo(
        project_id=version.project_id,
        version_id=version.id,
        version_name=version.version_number,
        version_type=version.version_type.name,
        release_date=version.date_published,
        mc_versions=version.game_versions,
        hashes={"sha1": version.files[0].hashes.sha1, "sha512": version.files[0].hashes.sha512},
        url=version.files[0].url,
        description=version.changelog or "",
    )

class Modrinth(ConnectorInterface):
    
    API_BASE = "https://api.modrinth.com/v2"
    HEADERS = {
        # Modrinth requires a uniquely identifying User-Agent (ideally with contact info)
        "User-Agent": "hank880907/modrinth-plugin-downloader/0.1 (hank880907@gmail.com)",
    }

    def download(self, file: FileInfo, dest: str):
        """Download a file and yield progress information."""
        yield from Version.get(file.version_id).download_primary_file(dest)

    @lru_cache(maxsize=128)
    def query(self, name: str, mc_version: Optional[str] = None, limit: int = 5) -> Dict[str, ProjectInfo]:
        facets = []
        facets.append(["categories:paper"])
        facets.append(["project_type:plugin"])
        if mc_version:
            facets.append([f"versions:{mc_version}"])
        response = SearchResponse.search(name, limit=limit, facets=facets)
        results = {}
        for hit in response.hits:
            results[hit.project_id] = self.get_project_info(hit.project_id)
        return results

    @lru_cache(maxsize=128)
    def get_project_info(self, id: str) -> ProjectInfo:
        modrinth_project = Project.get(id)
        members = TeamMember.list_for_project(id)
        owner = "Unknown"
        for member in members:
            if member.is_owner:
                owner = member.user.username
                break
        
        plugin_info = ProjectInfo(
            name=modrinth_project.title,
            id=modrinth_project.id,
            author=owner,
            description=modrinth_project.description,
            downloads=modrinth_project.downloads,
        )
        versions = Version.list_for_project(id, loaders=["paper"])
        if not versions:
            return plugin_info
        plugin_info.latest = versions[0].id
        for version in versions:
            if version.version_type == "release":
                plugin_info.latest_release = version.id
                break
        for version in versions:
            file_info = version_to_file_info(version)
            plugin_info.versions[file_info.version_id] = file_info
        return plugin_info

    @lru_cache(maxsize=128)
    def get_file_info(self, id: str) -> FileInfo:
        """Get detailed information about a file by its ID."""
        try:
            version = Version.get(id)
            return version_to_file_info(version)
        except Exception as e:
            try:
                version = Version.get_by_hash(id)
                return version_to_file_info(version)
            except Exception as e2:
                raise RuntimeError(f"Failed to get file info for ID {id}: {e}")