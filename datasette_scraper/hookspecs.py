from pluggy import HookimplMarker
from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette_scraper")
hookimpl = HookimplMarker("datasette_scraper")

@hookspec
def config_schema():
    """Returns a JSON-schema of what a valid value looks like."""

@hookspec
def config_default_value():
    """Returns a reasonable default value that conforms to config_schema."""

@hookspec
def get_seed_urls(config):
    """Get list of URLs to fetch."""

@hookspec(firstresult=True)
def before_fetch_url(conn, config, url, depth, request_headers):
    """Reject a URL, or modify its request headers."""

@hookspec(firstresult=True)
def fetch_url(conn, config, url, request_headers):
    """Fetch a URL."""

@hookspec()
def discover_urls(config, url, response):
    """Discover new URLs to crawl."""
