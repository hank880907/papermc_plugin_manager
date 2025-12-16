import hashlib
import json
import os
from pathlib import Path

import logzero
from logzero import logger

from .config import Config


def setup_logging(verbose: bool = False, log_file: str = None):
    """Setup logging configuration.

    Args:
        verbose: Enable debug logging
        log_file: Optional log file path
    """
    log_level = logzero.logging.DEBUG if verbose else logzero.logging.WARNING

    # Set log level
    logzero.loglevel(log_level)

    # Setup log file if specified
    if log_file:
        logzero.logfile(log_file)

    # Format: timestamp - level - message
    log_format = "%(asctime)s - %(levelname)s - %(message)s"
    logzero.formatter(logzero.logging.Formatter(log_format))

    logger.debug("Logging initialized")


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


def get_sha1(path: str | Path, chunk_size: int = None) -> str:
    """Compute the SHA1 hash of a file.

    Args:
        path: Path to the file
        chunk_size: Size of chunks to read (defaults to Config.DOWNLOAD_CHUNK_SIZE)

    Returns:
        str: SHA1 hash as a hexadecimal string
    """
    if chunk_size is None:
        chunk_size = Config.DOWNLOAD_CHUNK_SIZE

    h = hashlib.new("sha1")
    p = Path(path)

    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)

    return h.hexdigest()


def verify_file_hash(file_path: Path | str, expected_sha1: str) -> bool:
    """Verify that a file's SHA1 hash matches the expected value.

    Args:
        file_path: Path to the file to verify
        expected_sha1: Expected SHA1 hash

    Returns:
        bool: True if hash matches, False otherwise
    """
    actual_sha1 = get_sha1(file_path)
    is_valid = actual_sha1.lower() == expected_sha1.lower()

    if is_valid:
        logger.debug(f"File verification passed: {file_path}")
    else:
        logger.error(f"File verification failed for {file_path}")
        logger.error(f"Expected: {expected_sha1}, Got: {actual_sha1}")

    return is_valid
