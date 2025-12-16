# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-16

### Added

- Configuration constants module (`config.py`) for centralized settings management
- Custom exception classes for better error handling:
  - `PluginNotFoundException`
  - `VersionNotFoundException`
  - `DownloadFailedException`
  - `CacheException`
  - `InvalidVersionException`
  - `PluginAlreadyInstalledException`
  - `ServerVersionException`
- Environment variable support for configuration overrides:
  - `PPM_CACHE_FILE` - Override cache file location
  - `PPM_PLUGINS_DIR` - Override plugins directory
  - `PPM_USER_AGENT` - Override API user agent
  - `PPM_DEFAULT_PLATFORM` - Override default platform
- Improved error messages with specific exception types
- Better documentation in docstrings

### Changed

- Refactored all hard-coded paths and configuration values to use `Config` class
- Improved error handling throughout the codebase
- Updated User-Agent to include project repository URL
- Bumped version from 0.0.1 to 0.1.0
- Enhanced `get_papermc_version()` with better error handling

### Fixed

- Consistent error handling across all CLI commands
- More informative error messages for common failure cases

## [0.0.1] - 2025-12-15

### Added

- Initial release with core functionality
- Search for plugins on Modrinth
- Install, upgrade, and remove plugins
- List installed plugins with compatibility indicators
- Cache system for performance
- Shell completion support (zsh, bash, fish)
- Autocomplete for plugin names and versions
- Support for unidentified (non-Modrinth) plugins
- Rich terminal UI with tables and progress bars
- apt-like workflow (update/upgrade commands)
- Version compatibility checking
