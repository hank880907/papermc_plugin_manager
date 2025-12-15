from ..connector_interface import ConnectorInterface, ProjectInfo, FileInfo

from .modrinth_models import Version, SearchResponse, Project, TeamMember

import requests
import json
from typing import Dict, Optional


def version_to_file_info(version: Version) -> FileInfo:
    return FileInfo(
        project_id=version.project_id,
        version_id=version.id,
        version_name=version.version_number,
        version_type=version.version_type,
        release_date=version.date_published,
        mc_versions=version.game_versions,
        hashes=version.files[0].hashes,
        url=version.files[0].url,
    )

class Modrinth(ConnectorInterface):
    
    API_BASE = "https://api.modrinth.com/v2"
    HEADERS = {
        # Modrinth requires a uniquely identifying User-Agent (ideally with contact info)
        "User-Agent": "hank880907/modrinth-plugin-downloader/0.1 (you@example.com)",
    }

    def download(self, id: str, dest: str) -> None:
        Version.get(id).download_primary_file(dest)
    
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
        plugin_info.latest = version_to_file_info(versions[0])
        for version in versions:
            if version.version_type == "release":
                plugin_info.latest_release = version_to_file_info(version)
                break
        return plugin_info

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