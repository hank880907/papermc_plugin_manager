# PaperMC Plugin Manager (ppm)

A modern, user-friendly command-line tool for managing PaperMC server plugins. Built with Python and featuring intelligent caching, automatic updates, and beautiful console output powered by Rich.

## Features

- **Search**: Search for plugins across Modrinth with fuzzy matching
- **Easy Installation**: Install plugins with a single command
- **Version Management**: Upgrade, downgrade, or switch between specific versions
- **Version Detection**: Automatically detects outdated plugins
- **Installation Status**: See which plugins are installed at a glance

## Screenshots

**List installed plugins** - View all installed plugins with version information and update status:
![ppm list](media/ppm_list.png)

**Search for plugins** - Find plugins across Modrinth with fuzzy matching:
![ppm search](media/ppm_search.png)

**Show plugin details** - Display comprehensive plugin information including metadata and available versions:
![ppm show](media/ppm_show.png)

## Installation

```bash
pip install papermc-plugin-manager
```

Or using uv:

```bash
uv tool install papermc-plugin-manager
```

## Usage

- List installed plugins:

```bash
ppm update
ppm list
```

- Search for plugins:

```bash
ppm search <plugin-name>
```

- Show plugin details:

```bash
ppm show <plugin-name-or-id> [--version <version>]
```

- Install plugins:

```bash
# Latest release
ppm install <plugin-name> [-y]

# Specific version
ppm install <plugin-name> --version <version> [-y]

# Latest snapshot/beta
ppm install <plugin-name> --snapshot [-y]
```