import importlib
import pluggy
import sys
from . import hookspecs

DEFAULT_PLUGINS = (
    "datasette_scraper.plugins.fetch_url",
    "datasette_scraper.plugins.fetch_cache",
    "datasette_scraper.plugins.discover_allow",
    "datasette_scraper.plugins.discover_deny",
    "datasette_scraper.plugins.discover_html_links",
    "datasette_scraper.plugins.discover_only_same_origin",
    "datasette_scraper.plugins.discover_maintain_ssl",
    "datasette_scraper.plugins.canonicalize_shopify_products",
    "datasette_scraper.plugins.follow_redirects",
    "datasette_scraper.plugins.seed_urls",
    "datasette_scraper.plugins.seed_sitemaps",
    "datasette_scraper.plugins.max_depth",
    "datasette_scraper.plugins.max_pages",
    "datasette_scraper.plugins.max_pages_per_domain",
    "datasette_scraper.plugins.extract_links",
    "datasette_scraper.plugins.extract_json_ld",
    "datasette_scraper.plugins.extract_json_ld_product",
)

pm = pluggy.PluginManager("datasette_scraper")
pm.add_hookspecs(hookspecs)

if not hasattr(sys, "_called_from_test"):
    # Only load plugins if not running tests
    pm.load_setuptools_entrypoints("datasette_scraper")

# Load default plugins
for plugin in DEFAULT_PLUGINS:
    mod = importlib.import_module(plugin)
    pm.register(mod, plugin)
