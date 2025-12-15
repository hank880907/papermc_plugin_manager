import typer
import os
from typing import Optional
from papermc_plugin_manager.connector_interface import get_connector, CliContext
from .utils import get_papermc_version
import hashlib
from pathlib import Path

app = typer.Typer()

DEFAULT_PLATFORM = os.getenv("PPM_DEFAULT_PLATFORM", "modrinth")

@app.command()
def query(
    name: str = typer.Argument(..., help="Name of the plugin to query"),
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
    byid: bool = typer.Option(False, help="Query by plugin ID instead of name"),
    ):
    
    connector = get_connector(platform)
    typer.echo("Using connector: " + connector.__class__.__name__)
    result = connector.query(name, byid)
    if not result:
        typer.echo("No results found.")
    else:
        if byid:
            typer.echo(f"{result[name].complete_description()}")
        else:
            typer.echo(f"found {len(result)} results.")
            for i, plugin_id in enumerate(result, start=1):
                typer.echo(f"\n{i}: {plugin_id}")
                typer.echo(f"{result[plugin_id].complete_description()}")
    
# @app.command()
# def init(force: bool = typer.Option(False, "-f", "--force", help="Force re-initialization even if already initialized")):
#     """Initialize the plugin manager (e.g., create config files)."""
    
#     config_path = "./ppm_config.yaml"
#     if os.path.exists(config_path) and not force:
#         typer.echo("Configuration already exists. Use --force to re-initialize.")
#         return
#     # Create a default configuration file
#     version_history_path = "./version_history.json"
#     if not os.path.exists(version_history_path):
#         typer.echo("Cannot determine paperMC version. Please run this command in a PaperMC server directory.")
#         return
    
#     typer.echo("Initialization complete.")
    
@app.command()
def info(ctx: typer.Context):
    """Display information about the current CLI context."""
    cli_ctx: CliContext = ctx.obj
    for key, value in cli_ctx.__dict__.items():
        typer.echo(f"{key}: {value}")
        
@app.command()
def install(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Name or ID of the plugin to install"),
    plugin_version: Optional[str] = typer.Option(None, help="Specific plugin version to install"),
    snapshot: bool = typer.Option(False, help="Install the latest snapshot version"),
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),
    ):
    
    """Install a plugin for the current PaperMC version."""
    cli_ctx: CliContext = ctx.obj
    connector = get_connector(platform)
    typer.echo("Using connector: " + connector.__class__.__name__)
    results = connector.query(name, byid=False)
    for id, project in results.items():
        if project.name == name:
            typer.echo(f"Installing plugin: {project.name} (ID: {project.id})")
            if project.stable_version is None:
                typer.echo("No stable version available for installation.")
                return
            connector.download(project.stable_version.version_id)
            typer.echo("Installation complete.")
            return
        
    typer.echo(f"Plugin {name} not found, or cannot be uniquely identified.")
    

def file_sha_hex(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
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

@app.command()
def status(
    ctx: typer.Context,
    platform: str = typer.Option(DEFAULT_PLATFORM, help="Plugin platform to query"),):
    connector = get_connector(platform)
    files = os.listdir("./plugins")
    for file in files:
        path = Path("./plugins") / file
        if path.is_file():
            sha1 = file_sha_hex(path)
            connector.get_file_info(sha1)
            typer.echo(f"{file}: {sha1}")
            
    
    
    
    
    


@app.callback()
def initialize_cli(ctx: typer.Context):
    """
    Manage users in the awesome CLI app.
    """
    game_version = get_papermc_version()
    if not game_version:
        typer.echo("Could not determine PaperMC version. Please run this command in a PaperMC server directory.")
        raise typer.Exit()
    
    ctx.obj = CliContext(
        game_version=game_version
    )
    
    


def main():
    app()