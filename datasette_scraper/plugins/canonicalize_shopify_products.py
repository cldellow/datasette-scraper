from ..hookspecs import hookimpl
from urllib.parse import urlparse
import re

CANONICALIZE_SHOPIFY_PRODUCTS = 'canonicalize-shopify-products'

shopify_product_re = re.compile('^https://([^/]+)/collections/[^/]+/products/([^?#]+)(.*)$')

@hookimpl
def canonicalize_url(config, from_url, to_url, to_url_depth):
    if not CANONICALIZE_SHOPIFY_PRODUCTS in config or not config[CANONICALIZE_SHOPIFY_PRODUCTS]:
        return

    m = shopify_product_re.search(to_url)

    if m:
        return 'https://{}/products/{}{}'.format(m.group(1), m.group(2), m.group(3))

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'boolean',
          'title': 'Canonicalize Shopify product URLs',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(CANONICALIZE_SHOPIFY_PRODUCTS)
        },
        key = CANONICALIZE_SHOPIFY_PRODUCTS,
        group = 'Links',
        sort = 10
    )

@hookimpl
def config_default_value():
    return True
