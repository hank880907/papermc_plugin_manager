"""Custom exceptions for PaperMC Plugin Manager."""


class PPMException(Exception):
    """Base exception for all PPM errors."""

    pass


class PluginNotFoundException(PPMException):
    """Raised when a plugin cannot be found."""

    def __init__(self, plugin_name: str, message: str = None):
        self.plugin_name = plugin_name
        self.message = message or f"Plugin '{plugin_name}' not found"
        super().__init__(self.message)


class VersionNotFoundException(PPMException):
    """Raised when a specific version cannot be found."""

    def __init__(self, plugin_name: str, version: str, message: str = None):
        self.plugin_name = plugin_name
        self.version = version
        self.message = message or f"Version '{version}' not found for plugin '{plugin_name}'"
        super().__init__(self.message)


class DownloadFailedException(PPMException):
    """Raised when a download fails."""

    def __init__(self, url: str, reason: str = None):
        self.url = url
        self.reason = reason
        self.message = f"Download failed for {url}"
        if reason:
            self.message += f": {reason}"
        super().__init__(self.message)


class CacheException(PPMException):
    """Raised when cache operations fail."""

    def __init__(self, operation: str, reason: str = None):
        self.operation = operation
        self.reason = reason
        self.message = f"Cache operation '{operation}' failed"
        if reason:
            self.message += f": {reason}"
        super().__init__(self.message)


class InvalidVersionException(PPMException):
    """Raised when a version string is invalid."""

    def __init__(self, version: str, message: str = None):
        self.version = version
        self.message = message or f"Invalid version string: '{version}'"
        super().__init__(self.message)


class PluginAlreadyInstalledException(PPMException):
    """Raised when attempting to install an already installed plugin."""

    def __init__(self, plugin_name: str, version: str):
        self.plugin_name = plugin_name
        self.version = version
        self.message = f"Plugin '{plugin_name}' version '{version}' is already installed"
        super().__init__(self.message)


class ServerVersionException(PPMException):
    """Raised when server version cannot be determined."""

    def __init__(self, message: str = None):
        self.message = message or "Could not determine PaperMC server version"
        super().__init__(self.message)
