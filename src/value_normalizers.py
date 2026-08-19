from logger import logger
from constants import *
from utils import *
from pydantic.color import COLORS_BY_NAME

SERVICES = ["color", "brightness", "color_temp", "turn_on", "turn_off", "state"]


def limit_to_percent(value):
    return min(max(value, 0), 100)


def validate_and_normalize(domain: str, service: str, value: str, is_matter: bool) -> tuple:
    """
    Validates the service and normalizes the value based on the service type.

    :param domain: The device domain (e.g., "zigbee" or "matter").
    :param service: The requested service (e.g., "brightness", "color").
    :param value: The input value.
    :param is_matter: Boolean indicating if the device is Matter.
    :return: A tuple (service, normalized_value) or (None, None) if validation fails.
    """
    if service not in SERVICES:
        logger.warning(f"Unknown service: {service}")
        return None, None

    # Attempt to parse the value
    parsed_value = _parse_value(value)
    if parsed_value is None:
        return service, None

    # Normalize the value based on the service type
    service, value = _normalize_value(service, parsed_value)
    return service, value


def _parse_value(value: str) -> any:
    """Attempts to parse the value and cast it to numeric if applicable."""
    if value is None:
        return None

    # Try to parse the value as JSON
    try:
        parsed_value = json.loads(value)
    except Exception:
        parsed_value = value  # Use the original value if it is not valid JSON

    # Try to cast the parsed value to numeric
    try:
        return cast_to_numeric(parsed_value)
    except Exception as e:
        logger.error(f"Failed to cast value to numeric: {parsed_value}. Error: {e}")
        return None


def _parse_value_old(value: str) -> any:
    """Attempts to parse the value and cast to numeric if applicable."""
    if value is None:
        return None

    try:
        value = json.loads(value)
    except Exception:
        pass  # Ignore if value is not JSON

    try:
        return cast_to_numeric(value)  # Attempt to cast to numeric
    except Exception as e:
        logger.error(f"Failed parsing value: {value}. Error: {e}")
        return None


def _normalize_value(service: str, value: any) -> any:
    """Normalizes the value based on the specified service."""

    def normalize_brightness(val):
        return min(max(value, 0), 100) if isinstance(val, int) else 0

    def normalize_state(val):
        return int(bool(val))

    def normalize_color_temp(val):
        return val if isinstance(val, int) else 0

    def normalize_color(val):
        return _normalize_color(val)

    service_normalizers = {
        "brightness": normalize_brightness,
        "state": normalize_state,
        "color_temp": normalize_color_temp,
        "color": normalize_color,
    }

    handler = service_normalizers.get(service)

    if not handler:
        logger.warning(f"Unsupported service: {service}")
        return None, None

    # Normalize the value using the handler
    normalized_value = handler(value)

    # Custom checks for "color" and "color_temp"
    if service == "color" and normalized_value == [0, 0, 0]:
        return None, None
    if service == "color_temp" and normalized_value == 0:
        return None, None

    return service, normalized_value


def _normalize_value_old(service: str, value: any) -> any:
    """Normalizes the value based on the specified service."""
    handler = {
        "brightness": lambda val: limit_to_percent(val) if isinstance(val, int) else 0,
        "state": lambda val: int(bool(val)),
        "color_temp": lambda val: val if isinstance(val, int) else 0,
        "color": lambda val: _normalize_color(val),
    }.get(service)

    if not handler:
        logger.warning(f"Unsupported service: {service}")
        return None, None
    value = handler(value)

    # we do not handle black rgb value, because in this case color_temp  will define the light
    if service == "color" and value == [0, 0, 0]:
        return None, None

    # we do not handle color_temp=0, color_temp starts with 1
    if service == "color_temp" and value == 0:
        return None, None

    return service, value


def _normalize_color(value: any) -> list | None:
    """Normalizes color information (HEX, RGB, or color names)."""
    try:
        if isinstance(value, int):
            # Convert Loxone color code to RGB
            return list(extract_rgb_components(value))

        if isinstance(value, str):
            # Check for color names in known dictionaries
            rgb = COLORS_BY_NAME.get(value) or COLORS_BY_NAME_DE.get(value)
            if rgb:
                return normalize_to_list(rgb)

        # Assume the value is a list or tuple and normalize
        return normalize_to_list(value)

    except Exception as e:
        logger.error(f"Failed to normalize color value '{value}': {e}")
        return None


def _normalize_color_old(value: any) -> list | None:
    """Normalizes color information (HEX, RGB, or color names)."""
    if isinstance(value, int):
        # Convert Loxone color code to RGB
        try:
            return list(extract_rgb_components(value))
        except Exception as e:
            logger.error(f"Failed to extract RGB from color code '{value}': {e}")
            return None

    if isinstance(value, str):
        # Check for color names in known dictionaries
        try:
            # Retrieve color from known dictionaries or normalize as a list
            rgb = COLORS_BY_NAME.get(value) or COLORS_BY_NAME_DE.get(value)
            if rgb:
                return normalize_to_list(rgb)
        except Exception as e:
            logger.error(f"Error processing string color '{value}': {e}")
            return None

    # If the input is a list or tuple
    try:
        return normalize_to_list(value)
    except Exception as e:
        logger.error(f"Error normalizing color value: {value}. Error: {e}")
        return None