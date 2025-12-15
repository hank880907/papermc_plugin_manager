from ..connector_interface import ConnectorInterface, PluginInfo, PluginVersionInfo
import requests
import json
from typing import Dict


class Modrinth(ConnectorInterface):
    
    API_BASE = "https://api.modrinth.com/v2"
    HEADERS = {
        # Modrinth requires a uniquely identifying User-Agent (ideally with contact info)
        "User-Agent": "yourgithub/modrinth-plugin-downloader/0.1 (you@example.com)",
    }
    
    def parse_search_result(self, hit: dict) -> PluginInfo:
        id = hit["project_id"]
        name = hit["title"]
        author = hit["author"]
        description = hit.get("description", "No description provided.")
        downloads = hit["downloads"]
        supported_versions = hit["versions"]            
        plugin_info = PluginInfo(
            id=id,
            name=name,
            author=author,
            description=description,
            downloads=downloads,
            supported_versions=supported_versions,
        )
        return plugin_info
    
    def parse_project_info(self, project_data: dict, team_member:dict) -> PluginInfo:
        id = project_data["id"]
        name = project_data["title"]
        author = "Unknown"
        for member in team_member:
            if member['role'] == 'Owner':
                author = member['user']['username']
        description = project_data.get("description", "No description provided.")
        downloads = project_data["downloads"]
        supported_versions = project_data["game_versions"]
        plugin_info = PluginInfo(
            id=id,
            name=name,
            author=author,
            description=description,
            downloads=downloads,
            supported_versions=supported_versions,
        )
        return plugin_info
        
    
    def parse_plugin_version_info(self, version):
        return PluginVersionInfo(
            project_id=version["project_id"],
            version_id=version["id"],
            version_name=version["version_number"],
            version_type=version["version_type"],
            release_date=version["date_published"],
            mc_versions=version["game_versions"],
            hashes=version["files"][0]["hashes"],
            download_url=version["files"][0]["url"],
        )
    
    def download(self, id) -> None:
        self.download_primary_file(id)
    
    def query(self, name: str, byid: bool = False) -> dict:
        if byid:
            return {name: self.get_project_info(name)}
        else:
            return self.search_project_slug(name)
    
    def api_get(self, path: str, params: dict | None = None) -> dict | list:
        url = f"{self.API_BASE}{path}"
        r = requests.get(url, params=params, headers=self.HEADERS, timeout=30)

        # Basic handling for rate limiting
        if r.status_code == 429:
            reset = r.headers.get("X-Ratelimit-Reset", "?")
            raise RuntimeError(f"Rate limited by Modrinth API. Retry after ~{reset} seconds.")

        r.raise_for_status()
        return r.json()
    
    def get_project_info(self, project_id: str) -> PluginInfo:
        data = self.api_get(f"/project/{project_id}")
        if isinstance(data, dict):
            team_data = self.api_get(f"/project/{project_id}/members")
            if not isinstance(team_data, list):
                plugin_info = self.parse_project_info(data, team_data)
                self.populate_version_info(project_id, plugin_info)
                return plugin_info
        raise ValueError("Unexpected response format from Modrinth API")
    
    
    def populate_version_info(self, project_id: str, plugin_info: PluginInfo) -> None:
        params = {
            "loaders": json.dumps(["paper"])
        }
        versions_info = self.api_get(f"/project/{project_id}/version", params=params)
        plugin_info.latest_version = self.parse_plugin_version_info(versions_info[0])
        for version in versions_info:
            if version["version_type"] == "release":
                plugin_info.stable_version = self.parse_plugin_version_info(version)
                break
            
    def search_project_slug(self, query: str, limit: int = 5) -> dict:
        # Search endpoint: /v2/search :contentReference[oaicite:1]{index=1}
        facets = []
        # "categories" includes loaders in search, so "paper" is a common filter :contentReference[oaicite:2]{index=2}
        facets.append(["categories:paper"])
        facets.append(["project_type:plugin"])
        # facets.append(["server_side:required"])

        data = self.api_get(
            "/search",
            params={
                "query": query,
                "limit": limit,
                "index": "relevance",
                "facets": json.dumps(facets),
            },
        )

        if isinstance(data, dict):
            hits = data.get("hits", [])
            if not hits:
                raise ValueError(f"No results for query={query!r}")
            result: Dict[str, PluginInfo] = {}
            for hit in hits:
                id = hit["project_id"]
                versions_info = self.api_get(f"/project/{id}/version")
                result[id] = self.parse_search_result(hit)
                self.populate_version_info(id, result[id])
            return result
                
        raise ValueError("Unexpected response format from Modrinth API")
    
    
    def list_project_versions(self, project_slug: str):
        versions = self.api_get(f"/project/{project_slug}/version")
        return versions
    
    def download_primary_file(self, version_id):
        # Version includes files[].url + files[].primary :contentReference[oaicite:6]{index=6}
        version = self.api_get(f"/version/{version_id}")
        
        if isinstance(version, dict):
            files = version.get("files", [])
        else:
            raise ValueError("Unexpected response format from Modrinth API")
        
        if not files:
            raise ValueError("Version has no downloadable files.")
        
        for file in files:
            url = file.get("url")
            filename = f"plugins/{file.get("filename")}"
            with requests.get(url, stream=True, headers=self.HEADERS, timeout=60) as r:
                r.raise_for_status()
                with open(filename, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
            return filename
        
    def get_file_info(self, hash):
        data = self.api_get(f"/version_file/{hash}")
        print(data)
