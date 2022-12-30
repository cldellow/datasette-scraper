from ..hookspecs import hookimpl
from .seed_urls import SEED_URLS
from ..utils import get_html_parser
from urllib.parse import urlparse

SEED_SITEMAPS = 'seed-sitemaps'

@hookimpl
def get_seed_urls(config):
    if not SEED_SITEMAPS in config or not config[SEED_SITEMAPS]:
        return []

    rv = []
    seen_hosts = {}
    # We cheat, and peek into the config for seed-urls to find domains whose
    # robots.txt we'll sniff for a sitemap.
    seed_urls = []
    if SEED_URLS in config:
        seed_urls = config[SEED_URLS]

    for url in seed_urls:
        parsed = urlparse(url)
        host = parsed.hostname

        if host in seen_hosts:
            continue

        seen_hosts[host] = True

        candidates = [
            '{}://{}/robots.txt'.format(parsed.scheme, host),
            '{}://{}/sitemap.xml'.format(parsed.scheme, host)
        ]

        for candidate in candidates:
            if not candidate in seed_urls:
                rv.append(candidate)

    return rv

@hookimpl
def discover_urls(config, url, response):
    if not SEED_SITEMAPS in config or not config[SEED_SITEMAPS]:
        return []

    parsed = urlparse(url)

    if parsed.path == '/robots.txt':
        sitemaps = list(set([x.split(' ')[1] for x in response['text'].split('\n') if x.startswith('Sitemap: ')]))
        return sitemaps

    rv = []
    if parsed.path.endswith('.xml'):
        parsed = get_html_parser(response)

        for node in parsed.css('sitemapindex sitemap loc'):
            url = node.text()
            if url:
                rv.append((url, 0))

        for node in parsed.css('urlset url loc'):
            url = node.text()
            if url:
                rv.append((url, 1))

    return rv


@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'boolean',
            'title': 'Follow XML sitemaps',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(SEED_SITEMAPS),
        },
        key = SEED_SITEMAPS,
        group = 'Seeds',
        sort = 100,
    )

@hookimpl
def config_default_value():
    return True