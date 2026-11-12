"""Which destinations a short link may point at."""

import ipaddress
from urllib.parse import urlsplit

from validators import url as is_valid_url

from .errors import InvalidDestination

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = {"http", "https"}
# Names that only mean something on a private network or the machine itself.
PRIVATE_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home.arpa")


def check_destination(url: str, own_hosts: set[str]) -> str:
    """Return the URL, stripped, if a short link may point at it; raise otherwise.

    Refused: anything that isn't http(s), URLs with a username or password in them (a
    phishing trick: https://bank.com@evil.example), private, loopback and other non-public
    addresses, local-only hostnames, and this app's own hosts (a link to itself would loop).
    """
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise InvalidDestination(f"URL is longer than {MAX_URL_LENGTH} characters")

    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise InvalidDestination("Only http and https links can be shortened")
    if parts.username is not None or parts.password is not None:
        raise InvalidDestination("Links can't contain a username or password")

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        raise InvalidDestination("URL has no host")

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None

    if address is not None:
        if not address.is_global:
            raise InvalidDestination("Links to private or local addresses aren't allowed")
    elif host == "localhost" or host.endswith(PRIVATE_SUFFIXES) or "." not in host:
        raise InvalidDestination("Links to local or internal hosts aren't allowed")

    if host in own_hosts:
        raise InvalidDestination("Links to this shortener itself aren't allowed")

    if not is_valid_url(url):
        raise InvalidDestination("URL is not valid")
    return url
