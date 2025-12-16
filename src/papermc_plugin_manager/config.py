"""Configuration constants for PaperMC Plugin Manager."""

import os


class Config:
    """Central configuration for the PaperMC Plugin Manager."""

    # File paths
    CACHE_FILE: str = "papermc_plugin_manager.yaml"
    PLUGINS_DIR: str = "./plugins"
    VERSION_HISTORY_FILE: str = "./version_history.json"

    # Default settings
    DEFAULT_PLATFORM: str = os.getenv("PPM_DEFAULT_PLATFORM", "modrinth")

    # Cache settings
    CACHE_PROJECT_EXPIRY_HOURS: int = 24
    CACHE_FILE_EXPIRY_DAYS: int = 7
    CACHE_UNIDENTIFIED_EXPIRY_DAYS: int = 30
    CACHE_MAX_SIZE_MB: int = 100

    # API settings
    DEFAULT_USER_AGENT: str = "papermc-plugin-manager/0.1.0 (github.com/hankwu/papermc-plugin-manager)"
    MODRINTH_API_BASE: str = "https://api.modrinth.com/v2"

    # Download settings
    DOWNLOAD_CHUNK_SIZE: int = 1024 * 1024  # 1MB
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 2

    # Display settings
    DEFAULT_VERSION_LIMIT: int = 5
    SEARCH_RESULT_LIMIT: int = 5

    @classmethod
    def get_user_agent(cls) -> str:
        """Get the user agent string, allowing override via environment variable."""
        return os.getenv("PPM_USER_AGENT", cls.DEFAULT_USER_AGENT)

    @classmethod
    def get_cache_file(cls) -> str:
        """Get cache file path, allowing override via environment variable."""
        return os.getenv("PPM_CACHE_FILE", cls.CACHE_FILE)

    @classmethod
    def get_plugins_dir(cls) -> str:
        """Get plugins directory path, allowing override via environment variable."""
        return os.getenv("PPM_PLUGINS_DIR", cls.PLUGINS_DIR)
