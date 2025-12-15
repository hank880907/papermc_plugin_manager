from importlib.metadata import files
import os
import json
from pathlib import Path
import hashlib

def get_papermc_version():
    version_history_path = "./version_history.json"
    if not os.path.exists(version_history_path):
        return None
    with open(version_history_path, "r") as f:
        version_history = json.load(f)
    if not version_history:
        return None
    return version_history["currentVersion"].split("-")[0]

def get_sha1(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute the hash of a file's raw byte content and return it as a hex string.
    algo: "sha1", "sha256", "sha512", ...
    """
    h = hashlib.new("sha1")
    p = Path(path)

    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)

    return h.hexdigest()