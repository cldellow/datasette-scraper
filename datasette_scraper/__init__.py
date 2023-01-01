import datasette
import html
from jinja2 import FunctionLoader
import re
import os
import json
from .config import get_database, ensure_schema
from .plugin import pm
from .routes import routes
from .workers import start_workers
from collections import namedtuple

ConfigSchema = namedtuple('ConfigSchema', ['schema', 'uischema', 'key', 'group', 'sort'], defaults=(None, 1000))

class JsonString:
    def __init__(self, obj):
        self.obj = obj

    def __html__(self):
        return json.dumps(self.obj)


@datasette.hookimpl
def startup(datasette):
    async def inner():
        db = get_database(datasette)
        await ensure_schema(db)

        start_workers(datasette)

    return inner

class MyFunctionLoader(FunctionLoader):
    def list_templates(self):
        return []

@datasette.hookimpl
def prepare_jinja2_environment(env, datasette):
    def load_func(path):
        try:
            if path.startswith('table-') and path.endswith('-dss_crawl.html'):
                path = 'table-dss_crawl.html'
            elif path.startswith('table-') and path.endswith('-dss_job.html'):
                path = 'table-dss_job.html'
            elif path.startswith('table-') and path.endswith('-dss_host_rate_limit.html'):
                path = 'table-dss_host_rate_limit.html'
            elif path.startswith('table-') and path.endswith('-dss_job_stats.html'):
                path = 'table-dss_job_stats.html'
            elif path.startswith('table-') and path.endswith('-dss_extract_stats.html'):
                path = 'table-dss_extract_stats.html'
            elif path.startswith('table-') and path.endswith('-dss_zstd_dict.html'):
                path = 'table-dss_zstd_dict.html'
            elif path.startswith('row-') and path.endswith('-dss_crawl.html'):
                path = 'row-dss_crawl.html'
            elif path.startswith('row-') and path.endswith('-dss_host_rate_limit.html'):
                path = 'row-dss_host_rate_limit.html'

            template_path = os.path.abspath(os.path.join(__file__, '..', 'templates', path))

            f = open(template_path, 'r')
            contents = f.read()
            f.close()

            # TODO: this should return True in prod, I think? Although maybe
            #       just a performance improvement, so it's fine.
            return contents, path, lambda: False
        except FileNotFoundError:
            return None

    env.loader.loaders.insert(0, MyFunctionLoader(load_func))

@datasette.hookimpl
def get_metadata(datasette, key, database, table):
    rv = {
        'databases': {}
    }

    db_name = get_database(datasette).name

    rv['databases'][db_name] = {
        'tables': {
            'dss_crawl_queue': {
                'sort_desc': 'id'
            },
            'dss_crawl_queue_history': {
                'sort_desc': 'processed_at'
            },
            'dss_fetch_cache': {
                'sort_desc': 'fetched_at'
            },
            'dss_job': {
                'sort_desc': 'id'
            },
            'dss_job_stats': {
                'sort_desc': 'job_id'
            },

        }
    }

    return rv

@datasette.hookimpl
def extra_template_vars(datasette, request):
    """Add dss_schema, dss_default_config, dss_id variables."""

    known_groups = {
        'Seeds': 1,
        'Links': 2,
        'Caching': 5,
        'Extracting': 6,
        'Other': 7,
    }

    groups = {}

    async def extra_vars():
        schema = {
            'type': 'object',
            'properties': {
            }
        };

        schema['properties']['name'] = {
            'type': 'string',
            'minLength': 1
        }

        default_config = {'name': ''}

        for plugin in pm.get_plugins():
            if not 'config_schema' in dir(plugin):
                continue

            rv = plugin.config_schema()

            schema['properties'][rv.key] = rv.schema

            group = rv.group
            if not group in known_groups:
                group = 'Other'

            groups[group] = groups.get(group, [])
            groups[group].append((rv.uischema, rv.sort))

            if 'config_default_value' in dir(plugin):
                default_config[rv.key] = plugin.config_default_value()

        id = 0

        category_schemas = []
        for key in sorted(groups.keys(), key=lambda x: known_groups[x]):
            elements = sorted(groups[key], key=lambda x: x[1])
            elements = [x[0] for x in elements]
            category_schemas.append({
                'type': 'Category',
                'label': key,
                'elements': elements
            })

        uischema = {
            "type": "VerticalLayout",
            "elements": [
                {
                    "type": "Control",
                    "scope": "#/properties/name",
                },
                {
                    "type": "Categorization",
                    "elements": category_schemas,
                }
            ]
        }


        m = re.search('/dss_crawl/([0-9]+)$', request.path)
        if m:
            id = int(m.group(1))
            db = get_database(datasette)
            rv = await db.execute('SELECT name, config FROM dss_crawl WHERE id = ?', [id])
            for row in rv:
                config = json.loads(row['config'])
                config['name'] = row['name']
                default_config = config

        return {
            "dss_schema": JsonString(schema),
            "dss_uischema": JsonString(uischema),
            "dss_default_config": JsonString(default_config),
            "dss_id": id
        }

    return extra_vars

@datasette.hookimpl
def register_routes():
    return routes
