# PaperMC Plugin Manager (ppm)

A modern, user-friendly command-line tool for managing PaperMC server plugins. Built with Python and featuring intelligent caching, automatic updates, and beautiful console output powered by Rich.

## Features

- 🔍 **Smart Search**: Search for plugins across Modrinth with fuzzy matching
- 📦 **Easy Installation**: Install plugins with a single command
- ⬆️ **Automatic Updates**: Upgrade all outdated plugins with one command
- ⬇️ **Version Management**: Upgrade, downgrade, or switch between specific versions
- 💾 **Intelligent Caching**: Fast operations with apt-like cache system
- 📊 **Beautiful UI**: Rich terminal interface with progress bars, tables, and panels
- 🔄 **Version Detection**: Automatically detects outdated plugins
- 📋 **Installation Status**: See which plugins are installed at a glance

## Installation

```bash
pip install papermc-plugin-manager
```

Or using uv:

```bash
uv pip install papermc-plugin-manager
```

## Configuration

PPM can be configured using environment variables:

- `PPM_CACHE_FILE` - Custom cache file location (default: `papermc_plugin_manager.yaml`)
- `PPM_PLUGINS_DIR` - Custom plugins directory (default: `./plugins`)
- `PPM_USER_AGENT` - Custom User-Agent for API requests
- `PPM_DEFAULT_PLATFORM` - Default plugin platform (default: `modrinth`)

**Example:**

```bash
export PPM_PLUGINS_DIR="/opt/papermc/plugins"
export PPM_CACHE_FILE="/var/cache/ppm.yaml"
ppm list
```

### Shell Completion (Optional)

Enable tab completion for plugin names and versions:

```bash
# For zsh
ppm --install-completion zsh

# For bash
ppm --install-completion bash

# For fish
ppm --install-completion fish
```

After installation, restart your terminal or source your shell configuration file.

**Autocomplete features:**

- Plugin names and IDs in `show`, `install`, and `rm` commands
- Version numbers in `--version` option for `show` and `install` commands
- All suggestions come from your local cache for instant results

**Examples:**

```bash
ppm install Via<TAB>              # Suggests: ViaVersion
ppm show CoreProtect --version 23<TAB>  # Suggests: 23.1, 23.0
ppm rm Luck<TAB>                  # Suggests: LuckPerms, Lu3KuzdV
```

## Usage

### Basic Commands

#### Search for Plugins

```bash
ppm search <plugin-name>
```

Example:

```bash
ppm search viaversion
```

#### Show Plugin Information

```bash
ppm show <plugin-name-or-id>
```

Examples:

```bash
ppm show viaversion
ppm show P1OZGk5p  # Using plugin ID
```

This command displays:

- Plugin metadata (author, downloads, latest versions)
- Installation status (installed version or not installed)
- Available versions
- Uses cache when available for faster response

#### List Installed Plugins

```bash
ppm list
```

Shows all installed plugins with:

- Project name
- Version information
- Release type (RELEASE, BETA, ALPHA)
- Release date
- Update status (Current or Outdated)

#### Update Plugin Cache

```bash
ppm update
```

Refreshes the cache with latest plugin information from Modrinth. Similar to `apt update`.

#### Install Plugins

```bash
# Install latest release version
ppm install <plugin-name>

# Install specific version
ppm install <plugin-name> --version <version>

# Install latest snapshot/beta
ppm install <plugin-name> --snapshot

# Skip confirmation prompts
ppm install <plugin-name> -y
```

Examples:

```bash
ppm install viaversion
ppm install viaversion --version 5.4.1
ppm install worldedit --snapshot -y
```

**Smart Installation Behavior:**

- If plugin is not installed: Installs the specified version
- If older version exists: Automatically upgrades to newer version
- If specific version requested: Replaces existing version (allows downgrades)
- If same version exists: Skips installation

#### Upgrade Plugins

```bash
ppm upgrade
```

Upgrades all outdated plugins to their latest versions. Respects release types:

- RELEASE plugins upgrade to latest RELEASE
- BETA plugins upgrade to latest BETA
- ALPHA plugins upgrade to latest ALPHA

Uses cached information (run `ppm update` first to check for updates).

### Advanced Usage

#### Server Information

```bash
ppm server-info
```

Displays current PaperMC server version and configuration.

#### Version-Specific Installation

```bash
# Downgrade to older version
ppm install viaversion --version 5.4.1 -y

# Upgrade to newer version
ppm install viaversion --version 5.6.0 -y
```

## Workflow (APT-like)

```bash
# 1. List installed plugins (fast, uses cache)
ppm list

# 2. Update cache with latest plugin information
ppm update

# 3. Check which plugins are outdated
ppm list

# 4. Upgrade all outdated plugins
ppm upgrade

# 5. Install new plugin
ppm install luckperms
```

## Cache System

The plugin manager uses an intelligent caching system stored in `papermc_plugin_manager.yaml`:

- **Plugin Cache**: Stores metadata for installed plugins (SHA1, version info, project details)
- **Project Cache**: Stores project information for faster lookups
- **SHA1 Validation**: Cache entries are validated using file hashes
- **Auto-Cleanup**: Removes stale cache entries for deleted plugins

### Cache Commands

```bash
# Use cache (default for list and upgrade)
ppm list

# Force refresh cache
ppm update

# Show command uses cache when available
ppm show viaversion
```

## Configuration

Set default platform (currently only Modrinth is supported):

```bash
export PPM_DEFAULT_PLATFORM=modrinth
```

## Requirements

- Python 3.10+
- PaperMC server (must be run from server directory)
- Internet connection for plugin downloads

## Dependencies

- `typer` - CLI framework
- `rich` - Beautiful terminal output
- `requests` - HTTP client
- `pyyaml` - YAML cache files

## Project Structure

```
papermc_plugin_manager/
├── src/
│   └── papermc_plugin_manager/
│       ├── __init__.py
│       ├── __main__.py          # CLI commands
│       ├── plugin_manager.py    # Core plugin management logic
│       ├── connector_interface.py # Plugin source abstraction
│       ├── console.py            # Rich UI components
│       ├── utils.py              # Utility functions
│       └── connectors/
│           ├── modrinth.py       # Modrinth API integration
│           └── modrinth_models.py
├── tests/
├── pyproject.toml
└── README.md
```

## Examples

### Complete Setup Workflow

```bash
# Navigate to your PaperMC server directory
cd /path/to/papermc/server

# Search for a plugin
ppm search essentials

# View plugin details
ppm show essentialsx

# Install plugin
ppm install essentialsx -y

# List all installed plugins
ppm list

# Update cache to check for updates
ppm update

# Upgrade all outdated plugins
ppm upgrade -y
```

### Managing Plugin Versions

```bash
# Install specific version
ppm install viaversion --version 5.4.1 -y

# Check installation
ppm list | grep ViaVersion

# Downgrade to older version
ppm install viaversion --version 5.3.0 -y

# Upgrade to latest
ppm install viaversion -y
```

## Features in Detail

### Outdated Detection

The plugin manager automatically detects outdated plugins by:

1. Comparing installed version with latest version of same type
2. Using semantic version comparison
3. Caching results for performance
4. Displaying status in the list command

### Progress Tracking

All downloads show:

- Real-time progress bar
- Download speed
- Estimated time remaining
- Total file size

### Smart Version Comparison

Handles various version formats:

- Semantic versions (1.2.3)
- Prefixed versions (v1.2.3)
- Build numbers (1.2.3+build.123)
- Snapshots (1.2.3-SNAPSHOT)

### Error Handling

- Validates PaperMC installation before operations
- Checks for network connectivity
- Handles corrupted cache gracefully
- Provides clear error messages

## Troubleshooting

### "Could not determine PaperMC version"

Make sure you're running the command from your PaperMC server directory where the `version_history.json` file exists.

### Cache Issues

Delete the cache file and update:

```bash
rm papermc_plugin_manager.yaml
ppm update
```

### Plugin Not Found

Try searching with different terms or use the exact plugin ID:

```bash
ppm search <term>
ppm show <plugin-id>
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your license here]

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI framework
- UI powered by [Rich](https://rich.readthedocs.io/)
- Plugin data from [Modrinth](https://modrinth.com/)

## Roadmap

- [ ] Support for additional plugin sources (Bukkit, Spigot, Hangar)
- [ ] Plugin dependency resolution
- [ ] Bulk operations (install multiple plugins)
- [ ] Plugin configuration management
- [ ] Backup and restore functionality
- [ ] Web interface
