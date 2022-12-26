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
