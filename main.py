from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

import requests

API_BASE = "https://api.modrinth.com/v2"
HEADERS = {
    # Modrinth requires a uniquely identifying User-Agent (ideally with contact info)
    "User-Agent": "yourgithub/modrinth-plugin-downloader/0.1 (you@example.com)",
}

def api_get(path: str, params: dict | None = None) -> dict | list:
    url = f"{API_BASE}{path}"
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)

    # Basic handling for rate limiting
    if r.status_code == 429:
        reset = r.headers.get("X-Ratelimit-Reset", "?")
        raise RuntimeError(f"Rate limited by Modrinth API. Retry after ~{reset} seconds.")

    r.raise_for_status()
    return r.json()

def search_project_slug(query: str, require_server_side: bool = True) -> str:
    # Search endpoint: /v2/search :contentReference[oaicite:1]{index=1}
    facets = []
    # "categories" includes loaders in search, so "paper" is a common filter :contentReference[oaicite:2]{index=2}
    facets.append(["categories:paper"])
    if require_server_side:
        facets.append(["server_side:required"])

    data = api_get(
        "/search",
        params={
            "query": query,
            "limit": 5,
            "index": "relevance",
            "facets": json.dumps(facets),
        },
    )

    hits = data.get("hits", [])
    if not hits:
        raise ValueError(f"No results for query={query!r}")

    return hits[0]["slug"]  # search results include "slug" :contentReference[oaicite:3]{index=3}

def pick_latest_release_version(project_slug: str, mc_version: str, loader: str) -> dict:
    # List project's versions: GET /project/{id|slug}/version :contentReference[oaicite:4]{index=4}
    versions = api_get(
        f"/project/{project_slug}/version",
        params={
            # These query params are JSON strings like ["paper"] :contentReference[oaicite:5]{index=5}
            "loaders": json.dumps([loader]),
            "game_versions": json.dumps([mc_version]),
        },
    )

    # Prefer newest "release"
    releases = [v for v in versions if v.get("version_type") == "release"]
    if not releases:
        raise ValueError(f"No release versions found for {project_slug} on {loader} {mc_version}")

    # date_published is ISO-8601; string sort works for ISO timestamps
    releases.sort(key=lambda v: v.get("date_published", ""), reverse=True)
    return releases[0]

def download_primary_file(version: dict, dest_dir: Path) -> Path:
    # Version includes files[].url + files[].primary :contentReference[oaicite:6]{index=6}
    files = version.get("files", [])
    if not files:
        raise ValueError("Version has no downloadable files.")

    primary = next((f for f in files if f.get("primary") is True), files[0])
    url = primary["url"]
    filename = primary["filename"]

    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / filename

    with requests.get(url, stream=True, headers=HEADERS, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

    return out_path

if __name__ == "__main__":
    # Option A: if you already know the Modrinth slug (from https://modrinth.com/plugin/<slug>)
    project_slug = "luckperms"  # <-- replace

    # Option B: search by name instead
    # project_slug = search_project_slug("LuckPerms")

    mc_version = "1.21.1"  # <-- replace
    loader = "paper"       # common for Paper/Purpur plugin builds

    plugins_dir = Path("./plugins")

    version = pick_latest_release_version(project_slug, mc_version, loader)
    jar_path = download_primary_file(version, plugins_dir)

    print(f"Downloaded: {jar_path}")

# from papermc_plugin_manager.connectors.modrinth import Modrinth


# connector = Modrinth()

# data = connector.list_project_versions("P1OZGk5p")
# for d in data:
#     print(f"{d['name']} - {d['version_number']} {d['version_type']} {d['date_published']}")