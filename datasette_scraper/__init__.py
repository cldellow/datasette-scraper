from datasette import hookimpl, Response
import html
import json
from .config import get_database, ensure_schema
from .plugin import pm
from collections import namedtuple

ConfigSchema = namedtuple('ConfigSchema', ['schema', 'uischema', 'key', 'group'], defaults=(None))

class JsonString:
    def __init__(self, obj):
        self.obj = obj

    def __html__(self):
        return json.dumps(self.obj)


@hookimpl
def startup(datasette):
    # We import plugins on startup to avoid a circular dependency issue...
    # this is maybe sketchy? OTOH, if we moved the impl of this hook to
    # a separate file, that would have solved it, too.
    async def inner():
        db = get_database(datasette)
        await ensure_schema(db)

    return inner

@hookimpl
def extra_template_vars(request):

    schema = {
        'type': 'object',
        'properties': {
        }
    };

    default_config = {}

    for plugin in pm.get_plugins():
        if not 'config_schema' in dir(plugin):
            continue

        rv = plugin.config_schema()

        schema['properties'][rv.key] = rv.schema

        if 'config_default_value' in dir(plugin):
            default_config[rv.key] = plugin.config_default_value()

    return {"dss_schema": JsonString(schema), "dss_default_config": JsonString(default_config)}

#async def scraper(request):
#    return Response.html(
#        "Hello"
#    )
#
#@hookimpl
#def register_routes():
#    return [(r"^/-/scraper$", scraper)]
