import importlib
import pluggy
import sys
from . import hookspecs

DEFAULT_PLUGINS = (
    "datasette_scraper.plugins.seed_urls",
    "datasette_scraper.plugins.max_depth",
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
