import os
from pathlib import Path
import glob
from select import select
from typing import Dict, List, Tuple
from logzero import logger

from .database import SourceDatabase, InstallationTable
from .utils import compute_sha1
from .connector_interface import get_connector, list_connectors, ConnectorInterface, FileInfo, ProjectInfo
from .exceptions import PluginNotFoundException



class PluginManager:

    def __init__(self):
        self.db = SourceDatabase()
        self.plugin_dir = os.environ.get("PPM_PLUGIN_DIR", "plugins")
        self.connectors: Dict[str, ConnectorInterface] = {}
        for connector_name in list_connectors():
            self.connectors[connector_name] = get_connector(connector_name)

    def get_installed_plugins_filename(self) -> list[str]:
        """Get a list of installed plugin filenames."""
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist.")
            return []
        plugin_files = glob.glob(os.path.join(self.plugin_dir, "*.jar"))
        return plugin_files
    
    def update(self, default_source: str):
        # get the installed plugins and their hashes.
        plugins = self.get_installed_plugins_filename()
        plugin_hashes = []
        for plugin in plugins:
            sha1 = compute_sha1(plugin)
            filesize = Path(plugin).stat().st_size
            logger.debug(f"Plugin: {plugin}, SHA1: {sha1}")
            self.db.save_installation_info(plugin, sha1, filesize)
            plugin_hashes.append(sha1)
        # remove stale installations
        self.db.remove_stale_installations(plugin_hashes)
        # fetch installation info
        installations = self.db.get_all_installations()
        for installation in installations:
            project_info = self.db.get_project_by_file_sha1(installation.sha1)
            if project_info is not None:
                connector = self.connectors[project_info.source]
            else:
                connector = self.connectors[default_source]

            fileinfo = self.db.get_file_by_sha1(installation.sha1)
            if fileinfo is None:
                yield f"Fetching file info for {installation.filename} from {connector.__class__.__name__}"
                try:
                    fileinfo = connector.get_file_info(installation.sha1)
                except PluginNotFoundException as e:
                    logger.debug(f"Plugin with SHA1 {installation.sha1} not found on {connector.__class__.__name__}: {e}")
                    continue
            logger.info(f"Plugin: {installation.filename}, Version: {fileinfo.version_name}, Released: {fileinfo.release_date}")
            try:
                yield f"Fetching project info for {installation.filename} from {connector.__class__.__name__}"
                project_info = connector.get_project_info(fileinfo.project_id)
                self.db.save_project_info(project_info)
            except PluginNotFoundException as e:
                logger.warning(f"Plugin with SHA1 {installation.sha1} not found on {connector.__class__.__name__}: {e}")

    def get_installations(self) -> Tuple[List[ProjectInfo], List[InstallationTable]]:
        installations = self.db.get_all_installations()
        projects = []
        unrecognized = []
        for installation in installations:
            logger.debug(f"Installation: {installation.filename}, SHA1: {installation.sha1}")
            project = self.db.get_project_by_file_sha1(installation.sha1)
            if project is None:
                unrecognized.append(installation)
                continue
            project.current_version = self.db.get_file_by_sha1(installation.sha1)
            projects.append(project)
        return projects, unrecognized


def get_plugin_manager() -> PluginManager:
    """Get an instance of the PluginManager."""
    if not hasattr(get_plugin_manager, '_instance'):
        get_plugin_manager._instance = PluginManager()
    return get_plugin_manager._instance