# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.3] - 2025-12-16

### Added

- Game version compatibility information displayed in `show` command's plugin info panel
- Compatibility icons (✓/⚠/✗) shown in Available Versions table in `show` command
- Automatic cache refresh after plugin installation for immediate availability

### Changed

- Version number now automatically fetched from `pyproject.toml` instead of hardcoded

## [0.0.2] - 2025-12-16

### Added

- Comprehensive docstrings for all CLI commands
- Better help messages explaining command behavior and options

### Fixed

- Suppressed log output during shell autocomplete to prevent terminal pollution
- Default log level changed to WARNING for cleaner output (use --verbose for DEBUG)
- Fixed `ppm` with no arguments to show help and exit with code 2 instead of silently succeeding

### Changed

- Cache manager refactored to use dataclass serialization with `asdict()` and automatic field detection
- Improved cache deserialization to handle extra fields gracefully

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
