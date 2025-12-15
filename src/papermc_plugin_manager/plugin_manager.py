from requests import HTTPError
from logzero import logger
import os
from typing import Tuple

from .connector_interface import ConnectorInterface, ProjectInfo, FileInfo


class PluginManager:


    def __init__(self, connector: ConnectorInterface, game_version: str):
        self.connector = connector
        self.game_version = game_version

        if os.path.exists("plugins") is False:
            os.makedirs("plugins")


    def fuzzy_find_project(self, name: str) -> Tuple[bool, ProjectInfo] | None:
        """
        Fuzzy find a project by its name or ID.
        returns a tuple (is_exact_match, ProjectInfo) if found, else None.
        
        :param self: Description
        :param name: Description
        :type name: str
        :return: Description
        :rtype: Tuple[bool, ProjectInfo] | None
        """

        try:
            result = self.connector.get_project_info(name)
            return True, result
        except HTTPError:
            pass

        logger.info(f"Plugin {name} not found by ID, searching by name...")
        results = self.connector.query(name, self.game_version)
        for project_id, project_info in results.items():
            return False, project_info
        
        logger.info(f"No results found for plugin {name}.")
        return None
    
    def install_plugin(self, plugin: FileInfo):
        self.connector.download(plugin, "plugins")
