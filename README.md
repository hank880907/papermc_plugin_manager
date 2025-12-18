# PaperMC Plugin Manager (ppm)

A standalone CLI tool for inspecting and managing plugins on a PaperMC server using Modrinth metadata.
This project was written to solve the pain of manually tracking plugins on Linux servers accessed via SSH.
It is intended for server owners who want visibility and safe, controlled updates — not automatic plugin upgrades.

## Features

- **Installation Status**: See which plugins are installed at a glance
- **Search**: Search for plugins across Modrinth with fuzzy matching
- **Version Management**: Upgrade, downgrade, or switch between specific versions
- **Plugin Detection**: Automatically detects plugins

## Why This Exists

Many existing plugin managers suffer from one or more of the following problems:

- downloading the wrong plugin due to name collisions
- upgrading to a wrong version
- requiring accounts, Discord bots, or license servers
- running inside the Minecraft server itself

This project aims to avoid those pitfalls by being explicit, inspectable, and boring in the right ways.

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
ppm update # This will fetch plugin info from remote.
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
ppm install <plugin-name>

# Specific version
ppm install <plugin-name> --version <version>

# Latest snapshot/beta
ppm install <plugin-name> --snapshot
```
