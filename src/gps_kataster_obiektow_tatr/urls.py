"""Syntactic checks for absolute source URLs; no network access or rewriting."""

from urllib.parse import urlsplit

from rfc3986_validator import validate_rfc3986


def valid_absolute_url(value: str) -> bool:
    if not value or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    if not validate_rfc3986(value, rule="URI"):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.netloc:
            # Accessors also reject malformed IPv6 and nonnumeric/out-of-range ports.
            return bool(parsed.hostname) and (parsed.port is None or parsed.port >= 0)
        return parsed.scheme not in {"http", "https", "ftp"} and bool(parsed.path)
    except ValueError:
        return False
