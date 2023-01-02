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
def get_seed_urls(conn, config, job_id):
    """Get list of URLs to fetch."""

@hookspec(firstresult=True)
def before_fetch_url(conn, config, job_id, url, depth, request_headers):
    """Reject a URL, or modify its request headers."""

@hookspec(firstresult=True)
def fetch_cached_url(conn, config, job_id, url, depth, request_headers):
    """Fetch a previously cached URL."""

@hookspec()
def after_fetch_url(conn, config, job_id, url, request_headers, response, fresh, fetch_duration):
    """Process a fetched URL. Useful for caching or logging."""

@hookspec(firstresult=True)
def fetch_url(url, request_headers):
    """Fetch a URL live from an origin server."""

@hookspec()
def discover_urls(conn, config, job_id, url, response):
    """Discover new URLs to crawl."""

@hookspec()
def canonicalize_url(conn, config, job_id, from_url, to_url, to_url_depth):
    """Canonicalize a discovered URL, possibly rejecting it."""

@hookspec()
def extract_from_response(conn, config, job_id, url, response):
    """Extract some table rows from the response."""
