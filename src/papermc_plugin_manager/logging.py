import logzero
from logzero import logger

def setup_logging(verbose: int = 0, log_file: str = None):
    """Setup logging configuration.

    Args:
        verbose: Enable debug logging
        log_file: Optional log file path
    """
    if verbose == 0:
        log_level = logzero.logging.WARNING
    elif verbose == 1:
        log_level = logzero.logging.INFO
    else:
        log_level = logzero.logging.DEBUG
    # Set log level
    logzero.loglevel(log_level)
    # Setup log file if specified
    if log_file:
        logzero.logfile(log_file)
    # Format: timestamp - level - message
    # log_format = "%(asctime)s - %(levelname)s - %(message)s"
    # logzero.formatter(logzero.logging.Formatter(log_format))
    logger.debug("Logging initialized")