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

    schema['properties']['name'] = {
        'type': 'string',
        'minLength': 1
    }

    default_config = {'name': 'xx'}

    for plugin in pm.get_plugins():
        if not 'config_schema' in dir(plugin):
            continue

        rv = plugin.config_schema()

        schema['properties'][rv.key] = rv.schema

        if 'config_default_value' in dir(plugin):
            default_config[rv.key] = plugin.config_default_value()

    return {"dss_schema": JsonString(schema), "dss_default_config": JsonString(default_config)}

async def scraper_upsert(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    form = await request.post_vars()

    id = int(form['id'])
    config = json.loads(form['config'])

    name = config['name']
    config.pop('name')

    db = get_database(datasette)

    if not id:
        rv = await db.execute_write('INSERT INTO _dss_crawl(name, config) VALUES (?, ?)', [name, json.dumps(config)], block=True)
        id = rv.lastrowid
    else:
        await db.execute_write('UPDATE _dss_crawl SET name = ?, config = ? WHERE id = ?', [name, json.dumps(config), id], block=True)

    return Response.redirect('/-/scraper/crawl/{}'.format(id))

@hookimpl
def register_routes():
    return [(r"^/-/scraper/upsert$", scraper_upsert)]
