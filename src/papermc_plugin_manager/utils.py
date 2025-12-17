import hashlib
import json
import os
from pathlib import Path
from logzero import logger

from .config import Config

def compute_md5(file_path):
    m = hashlib.md5()
    try:
        with open(file_path, 'rb') as f: # Open in binary mode 'rb'
            while chunk := f.read(8192): # Read in 8192 byte chunks
                m.update(chunk)
    except FileNotFoundError:
        return "File not found"
    return m.hexdigest()


def compute_sha1(path: str | Path, chunk_size: int = None) -> str:
    if chunk_size is None:
        chunk_size = Config.DOWNLOAD_CHUNK_SIZE
    h = hashlib.new("sha1")
    p = Path(path)
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def get_papermc_version():
    """Get the PaperMC version from version_history.json.

    Returns:
        str: The current PaperMC version, or None if not found.
    """
    version_history_path = Config.VERSION_HISTORY_FILE
    if not os.path.exists(version_history_path):
        return None
    try:
        with open(version_history_path) as f:
            version_history = json.load(f)
        if not version_history:
            return None
        return version_history["currentVersion"].split("-")[0]
    except (json.JSONDecodeError, KeyError):
        return None


def verify_file_hash(file_path: Path | str, expected_sha1: str) -> bool:
    """Verify that a file's SHA1 hash matches the expected value.

    Args:
        file_path: Path to the file to verify
        expected_sha1: Expected SHA1 hash

    Returns:
        bool: True if hash matches, False otherwise
    """
    actual_sha1 = compute_sha1(file_path)
    is_valid = actual_sha1.lower() == expected_sha1.lower()

    if is_valid:
        logger.debug(f"File verification passed: {file_path}")
    else:
        logger.error(f"File verification failed for {file_path}")
        logger.error(f"Expected: {expected_sha1}, Got: {actual_sha1}")

    return is_valid