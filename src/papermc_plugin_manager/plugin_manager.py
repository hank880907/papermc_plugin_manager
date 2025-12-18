import glob
import os
from collections.abc import Callable
from pathlib import Path

from logzero import logger

from .connector_interface import ConnectorInterface, ProjectInfo, SearchResult, get_connector, list_connectors
from .database import InstallationTable, SourceDatabase
from .exceptions import PluginNotFoundException
from .utils import compute_sha1, default_feedback_cb


class PluginManager:

    def __init__(self, default_source: str):
        self.db = SourceDatabase()
        self.plugin_dir = "plugins"
        self.connectors: dict[str, ConnectorInterface] = {}
        for connector_name in list_connectors():
            self.connectors[connector_name] = get_connector(connector_name)
        self.default_source = default_source
        # if self.default_source not in self.connectors:
        #     raise ValueError(f"Default source '{self.default_source}' is not a valid connector.")

    def get_installed_plugins_filename(self) -> list[str]:
        """Get a list of installed plugin filenames."""
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Plugin directory {self.plugin_dir} does not exist.")
            return []
        return glob.glob(os.path.join(self.plugin_dir, "*.jar"))

    def needs_update(self) -> bool:
        """check if plugin manager needs to update installed plugins."""
        installed_plugins = self.get_installed_plugins_filename()
        for plugin in installed_plugins:
            sha1 = compute_sha1(plugin)
            if not self.db.is_sha1_known(sha1):
                return True
        return False

    def update(self, feedback_cb: Callable[[str], None] = default_feedback_cb):
        # get the installed plugins and their hashes.
        plugins = self.get_installed_plugins_filename()
        plugin_hashes = []
        for plugin in plugins:
            sha1 = compute_sha1(plugin)
            filesize = Path(plugin).stat().st_size
            logger.debug(f"Plugin: {plugin}, SHA1: {sha1}")
            self.db.save_installation_info(os.path.basename(plugin), sha1, filesize)
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
                connector = self.connectors[self.default_source]

            fileinfo = self.db.get_file_by_sha1(installation.sha1)
            if fileinfo is None:
                feedback_cb(f"Fetching file info for {installation.filename} from {connector.__class__.__name__}")
                try:
                    fileinfo = connector.get_file_info(installation.sha1)
                except PluginNotFoundException as e:
                    logger.debug(f"Plugin with SHA1 {installation.sha1} not found on {connector.__class__.__name__}: {e}")
                    continue
            logger.info(f"Plugin: {installation.filename}, Version: {fileinfo.version_name}, Released: {fileinfo.release_date}")
            try:
                feedback_cb(f"Fetching project info for {installation.filename} from {connector.__class__.__name__}")
                project_info = connector.get_project_info(fileinfo.project_id)
                self.db.save_project_info(project_info)
            except PluginNotFoundException as e:
                logger.warning(f"Plugin with SHA1 {installation.sha1} not found on {connector.__class__.__name__}: {e}")

    def get_installations(self) -> tuple[list[ProjectInfo], list[InstallationTable]]:
        installations = self.db.get_all_installations()
        projects = []
        unrecognized = []
        for installation in installations:
            logger.debug(f"Installation: {installation.filename}, SHA1: {installation.sha1}")
            project = self.db.get_project_by_file_sha1(installation.sha1)
            if project is None:
                unrecognized.append(installation)
                continue
            projects.append(project)
        return projects, unrecognized

    def get_installation_names(self) -> list[str]:
        """Get a list of installed plugin names for autocompletion."""
        installations, _ = self.get_installations()
        return [plugin.name for plugin in installations] + [plugin.project_id for plugin in installations]

    def get_project_info(self, name):
        project_info = self.db.get_project_info(name)
        if project_info:
            logger.debug(f"Found local project info for '{name}': '{project_info.name}'")
            return project_info

        logger.debug(f"Project '{name}' not found in local database. Querying default source '{self.default_source}'")

        try:
            logger.debug(f"Fetching project info for '{name}' from default source '{self.default_source}'")
            project_info = self.connectors[self.default_source].get_project_info(name)
            local_project = self.db.get_project_info(project_info.project_id)
            if local_project:
                logger.debug(f"Found local project match for '{name}': '{local_project.name}'")
                return local_project
            return project_info
        except PluginNotFoundException:
            pass

        return None

    def fuzzy_find_project(self, name: str) -> tuple[bool, ProjectInfo | None]:
        """Fuzzy find projects by name across all connectors."""
        project = self.get_project_info(name)
        if project:
            return True, project
        try:
            logger.debug(f"Fuzzy searching for project '{name}' in default source '{self.default_source}'")
            query = self.connectors[self.default_source].query(name, limit=1)
            if query:
                for result in query:
                    local_project = self.db.get_project_info(result.project_id)
                    if local_project:
                        logger.debug(f"Found local project match for '{name}': '{local_project.name}'")
                        return False, local_project
                    project_info = self.connectors[self.default_source].get_project_info(result.project_id)
                    return False, project_info
        except PluginNotFoundException:
            pass

        return False, None

    def search_projects(self, query: str, mc_version: str | None = None, limit: int = 10) -> list[SearchResult]:
        """Search for projects across all connectors."""
        connector = self.connectors[self.default_source]
        try:
            return connector.query(query, mc_version, limit)
        except Exception as e:
            logger.error(f"Error searching for projects: {e}")
            return []

def get_plugin_manager() -> PluginManager:
    """Get an instance of the PluginManager."""
    from .config import Config
    if not hasattr(get_plugin_manager, '_instance'):
        get_plugin_manager._instance = PluginManager(Config.DEFAULT_SOURCE)  # type: ignore
    return get_plugin_manager._instance # type: ignore
