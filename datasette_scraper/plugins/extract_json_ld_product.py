import re
import json
from ..hookspecs import hookimpl
from ..utils import get_html_parser
from urllib.parse import urljoin

EXTRACT_JSON_LD_PRODUCT = 'extract-json-ld-product'

_re = {}

@hookimpl
def extract_from_response(config, url, response):
    if not EXTRACT_JSON_LD_PRODUCT in config:
        return {}

    rv = {}

    for options in config[EXTRACT_JSON_LD_PRODUCT]:
        if 'url-regex' in options:
            regex = options['url-regex']
            if regex in _re:
                compiled = _re[regex]
            else:
                compiled = re.compile(regex)
                _re[regex] = compiled

            if not compiled.search(url):
                continue

        dbname = options['database']
        tablename = options['table']

        if dbname in rv:
            database = rv[dbname]
        else:
            database = rv[dbname] = {}

        if tablename in database:
            table = database[tablename]
        else:
            table = database[tablename] = []

        parsed = get_html_parser(response)
        table.append({'source_url@': url, '__delete': True})
        for script in parsed.css('script[type="application/ld+json"]'):
            parsed = None
            try:
                parsed = json.loads(script.text())
            except:
                continue

            if not isinstance(parsed, dict):
                continue

            if not '@type' in parsed or parsed['@type'] != 'Product' or not '@context' in parsed or parsed['@context'] != 'http://schema.org/':
                continue

            products = extract_products(parsed)

            for product in products:
                product['source_url@'] = url

            table.extend(products)

    return rv

def extract_products(parsed):
    rv = []
    base = {}

    if 'name' in parsed:
        base['name'] = parsed['name']

    if 'sku' in parsed and parsed['sku'] and isinstance(parsed['sku'], str):
        base['sku'] = parsed['sku']

    if 'mpn' in parsed and parsed['mpn'] and isinstance(parsed['mpn'], str):
        base['mpn'] = parsed['mpn']

    if 'image' in parsed:
        if isinstance(parsed['image'], str):
            base['image'] = parsed['image']

        if isinstance(parsed['image'], list) and parsed['image']:
            base['image'] = parsed['image'][0]

    if 'id' in parsed:
        base['id'] = parsed['id']

    if 'url' in parsed:
        base['url'] = parsed['url']

    if 'brand' in parsed:
        if isinstance(parsed['brand'], dict) and 'name' in parsed['brand']:
            base['brand'] = parsed['brand']['name']

    if 'seller' in parsed:
        if isinstance(parsed['seller'], dict) and 'name' in parsed['seller']:
            base['seller'] = parsed['seller']['name']

    # This is a lot of boilerplate for not much use - maybe we make it configurable
    # to extract or not?
    #if 'description' in parsed:
    #    base['description'] = parsed['description']

    offers = []
    raw_offers = []
    if 'offers' in parsed and isinstance(parsed['offers'], dict):
        raw_offers = [parsed['offers']]
    elif 'offers' in parsed and isinstance(parsed['offers'], list):
        raw_offers = parsed['offers']

    valid_base = 'name' in parsed

    if not valid_base:
        return []

    for raw in raw_offers:
        new_dict = {}
        for k, v in base.items():
            new_dict[k] = v

        # https://schema.org/ItemAvailability
        if 'availability' in raw and raw['availability'].startswith('https://schema.org/'):
            new_dict['availability'] = raw['availability'][19:]

        # https://schema.org/ItemCondition
        if 'itemCondition' in raw and raw['itemCondition'].startswith('https://schema.org/'):
            new_dict['condition'] = raw['itemCondition'][19:]

        if 'sku' in raw:
            new_dict['sku'] = raw['sku']

        if 'url' in raw:
            new_dict['url'] = raw['url']

        if 'id' in raw:
            new_dict['id'] = raw['id']

        if 'priceSpecification' in raw:
            spec = raw['priceSpecification']

            if 'price' in spec:
                new_dict['price'] = spec['price']

            if 'priceCurrency' in spec:
                new_dict['currency'] = spec['priceCurrency']


        if 'price' in raw:
            new_dict['price'] = raw['price']

        if 'priceCurrency' in raw:
            new_dict['currency'] = raw['priceCurrency']

        rv.append(new_dict)

    if rv:
        return rv

    return [base]




@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'url-regex': {
                        'type': 'string',
                    },
                    'database': {
                        'type': 'string',
                    },
                    'table': {
                        'type': 'string',
                    },
                },
                'required': ['database', 'table']
            }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(EXTRACT_JSON_LD_PRODUCT),
            'label': 'Extract JSON+LD product details'
        },
        key = EXTRACT_JSON_LD_PRODUCT,
        sort = 3000,
        group = 'Extracting',
    )

@hookimpl
def config_default_value():
    return []
