"""Unit tests for config module."""

import pytest
import os
from papermc_plugin_manager.config import Config


class TestConfig:
    """Test Config class."""
    
    def test_default_values(self):
        """Test default configuration values."""
        assert Config.CACHE_FILE == "papermc_plugin_manager.yaml"
        assert Config.PLUGINS_DIR == "./plugins"
        assert Config.VERSION_HISTORY_FILE == "./version_history.json"
        assert Config.DEFAULT_PLATFORM == "modrinth"
        assert Config.MODRINTH_API_BASE == "https://api.modrinth.com/v2"
    
    def test_cache_settings(self):
        """Test cache-related settings."""
        assert Config.CACHE_PROJECT_EXPIRY_HOURS == 24
        assert Config.CACHE_FILE_EXPIRY_DAYS == 7
        assert Config.CACHE_UNIDENTIFIED_EXPIRY_DAYS == 30
        assert Config.CACHE_MAX_SIZE_MB == 100
    
    def test_download_settings(self):
        """Test download-related settings."""
        assert Config.DOWNLOAD_CHUNK_SIZE == 1024 * 1024  # 1MB
        assert Config.MAX_RETRIES == 3
        assert Config.RETRY_DELAY_SECONDS == 2
    
    def test_display_settings(self):
        """Test display-related settings."""
        assert Config.DEFAULT_VERSION_LIMIT == 5
        assert Config.SEARCH_RESULT_LIMIT == 5
    
    def test_get_user_agent_default(self):
        """Test default user agent."""
        user_agent = Config.get_user_agent()
        assert "papermc-plugin-manager" in user_agent
        assert "0.1.0" in user_agent
    
    def test_get_user_agent_override(self, monkeypatch):
        """Test user agent override via environment variable."""
        custom_ua = "custom-user-agent/1.0"
        monkeypatch.setenv("PPM_USER_AGENT", custom_ua)
        assert Config.get_user_agent() == custom_ua
    
    def test_get_cache_file_default(self):
        """Test default cache file path."""
        assert Config.get_cache_file() == "papermc_plugin_manager.yaml"
    
    def test_get_cache_file_override(self, monkeypatch):
        """Test cache file path override via environment variable."""
        custom_cache = "/tmp/custom_cache.yaml"
        monkeypatch.setenv("PPM_CACHE_FILE", custom_cache)
        assert Config.get_cache_file() == custom_cache
    
    def test_get_plugins_dir_default(self):
        """Test default plugins directory."""
        assert Config.get_plugins_dir() == "./plugins"
    
    def test_get_plugins_dir_override(self, monkeypatch):
        """Test plugins directory override via environment variable."""
        custom_dir = "/custom/plugins"
        monkeypatch.setenv("PPM_PLUGINS_DIR", custom_dir)
        assert Config.get_plugins_dir() == custom_dir
