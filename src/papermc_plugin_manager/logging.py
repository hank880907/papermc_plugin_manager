
import logzero
from logzero import logger


def setup_logging(verbose: int = 0, log_file: str | None = None):
    if verbose == 0:
        log_level = logzero.logging.WARNING
    elif verbose == 1:
        log_level = logzero.logging.INFO
    else:
        log_level = logzero.logging.DEBUG
    logzero.loglevel(log_level)
    if log_file:
        logzero.logfile(log_file)
    # Format: timestamp - level - message
    # log_format = "%(asctime)s - %(levelname)s - %(message)s"
    # logzero.formatter(logzero.logging.Formatter(log_format))
    logger.debug("Logging initialized")
