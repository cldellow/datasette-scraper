from pluggy import HookimplMarker
from pluggy import HookspecMarker

hookspec = HookspecMarker("datasette_scraper")
hookimpl = HookimplMarker("datasette_scraper")

@hookspec
def get_seed_urls():
    """Get list of URLs to fetch."""
