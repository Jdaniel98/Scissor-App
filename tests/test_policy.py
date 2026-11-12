import pytest

from app.services.errors import InvalidDestination
from app.services.policy import check_destination


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com/a/b?c=d#e",
        "https://sub.example.co.uk:8443/path",
        "https://8.8.8.8/",
        "  https://example.com/trimmed  ",
    ],
)
def test_allowed(url):
    assert check_destination(url, own_hosts={"sciss.or"}) == url.strip()


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "mailto:someone@example.com",
        "data:text/html,hi",
        "http://0.0.0.0/",
        "http://100.64.0.1/",  # carrier-grade NAT
        "http://[fd00::1]/",
        "http://router.lan/",
        "http://box.home.arpa/",
        "http://db.internal/",
        "https://Sciss.OR/x",  # own host, any case
        "https://sciss.or./x",  # own host with trailing dot
        "https://example.com@evil.example/",
    ],
)
def test_refused(url):
    with pytest.raises(InvalidDestination):
        check_destination(url, own_hosts={"sciss.or"})
