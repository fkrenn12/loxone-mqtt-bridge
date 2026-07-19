import logging
import colorlog

handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(levelname)s - %(message)s",
    log_colors={
        "DEBUG": "cyan",  # DEBUG: Cyan
        "INFO": "green",  # INFO: Green
        "WARNING": "yellow",  # WARNING: yellow
        "ERROR": "red",  # ERROR: red
        "CRITICAL": "bold_red"  # CRITICAL: red/bold
    }
))

logger = colorlog.getLogger("colored_logger")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
