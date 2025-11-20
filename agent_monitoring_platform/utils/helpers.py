import uuid
from datetime import timedelta


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID"""
    id_str = str(uuid.uuid4()).replace("-", "")[:12]
    return f"{prefix}_{id_str}" if prefix else id_str


def format_duration(milliseconds: float) -> str:
    """Format milliseconds to human-readable duration"""

    if milliseconds < 1000:
        return f"{milliseconds:.2f}ms"
    elif milliseconds < 60000:
        return f"{milliseconds / 1000:.2f}s"
    else:
        return f"{milliseconds / 60000:.2f}m"


def parse_duration(duration_str: str) -> float:
    """Parse human-readable duration to milliseconds"""

    duration_str = duration_str.strip().lower()

    if duration_str.endswith("ms"):
        return float(duration_str[:-2])
    elif duration_str.endswith("s"):
        return float(duration_str[:-1]) * 1000
    elif duration_str.endswith("m"):
        return float(duration_str[:-1]) * 60000
    elif duration_str.endswith("h"):
        return float(duration_str[:-1]) * 3600000
    else:
        return float(duration_str)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values"""

    if old_value == 0:
        return 0 if new_value == 0 else 100

    return ((new_value - old_value) / abs(old_value)) * 100


def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncate string to max length"""

    if len(s) <= max_length:
        return s
    return s[: max_length - 3] + "..."


def mask_sensitive_data(data: str) -> str:
    """Mask sensitive information in data"""

    import re

    patterns = [
        (r"api[_-]?key[:\s]*['\"]?([a-zA-Z0-9_\-]+)['\"]?", "api_key: ***"),
        (r"password[:\s]*['\"]?([^\s'\"]+)['\"]?", "password: ***"),
        (r"token[:\s]*['\"]?([a-zA-Z0-9_\-]+)['\"]?", "token: ***"),
        (r"\b[0-9]{16}\b", "****-****-****-****"),
    ]

    for pattern, replacement in patterns:
        data = re.sub(pattern, replacement, data, flags=re.IGNORECASE)

    return data
