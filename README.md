# datasette-scraper

[![PyPI](https://img.shields.io/pypi/v/datasette-scraper.svg)](https://pypi.org/project/datasette-scraper/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-scraper?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-scraper/releases)
[![Tests](https://github.com/cldellow/datasette-scraper/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-scraper/blob/main/LICENSE)

`datasette-scraper` is a Datasette plugin to manage small-ish crawl and extract jobs.
~100K pages per crawl is the sweet spot.

- Opinionated yet extensible
  - Many useful things are possible out-of-the-box, or write your own pluggy hooks to go further
- Leans heavily into SQLite
  - Introspect your crawls via ops tables exposed in Datasette
- Uses lightweight, fast libraries
  - [Datasette](https://datasette.io/) as a host
  - [selectolax](https://github.com/rushter/selectolax) for HTML parsing
  - [httpx](https://www.python-httpx.org/) for HTTP requests
  - [pluggy](https://pluggy.readthedocs.io/en/stable/) for extensibility
  - [sqlite-zstd](https://github.com/phiresky/sqlite-zstd) for efficiently storing compressed page responses
- **Not for adversarial crawling**
  - Want to crawl a site that blocks bots? You're on your own

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-scraper

## Usage

Configure `datasette-scraper` via `metadata.json`:

```
{
  "plugins": {
    "datasette-scraper": {
      // CONFIG GOES HERE
    }
  }
}
```

`datasette-scraper` uses plugins, which can be configured in this block.

A sample config that shows the use of all the plugins that ship with `datasette-scraper`
looks like:

```jsonc
{
  // Where should datasette-scraper store its operational data,
  // page crawls, etc?
  //
  // If omitted, defaults to the first database in the instance.
  "ops-database": "db-name",

  // The set of crawls to perform.
  // This may eventually move to a table in SQLite.
  "crawls": {
    // A crawl whose name is "hn-top-5"
    "hn-top-5": {
      // The starting set of URLs to crawl (optional)
      "seed-urls": ["https://news.ycombinator.com"],

      // A set of domains whose sitemaps will be discovered via
      // robots.txt, and used to discover URLs (optional)
      "seed-sitemaps": ["news.ycombinator.com"],

      // Extract candidate next links from a webpage via CSS selectors
      "discover-html-urls": {
        // When an HTML page is fetched, where should we find candidate
        // URLs to enqueue for crawling?

        // If absent (ie not []), the default is shown below
        "selectors": [
          {
            // Only look for links on pages whose URL matches this regex
            "url-regex": ".+",
            "selector": "a",
            // By default uses DOM inner text; you can specify an attribute to use
            // instead
            "attribute": "href"
          }
        ],
      },

      // Whether to discover URLs from the Location header of 3xx redirects
      "discover-redirect-urls": true,

      // When true, only follows links to pages on the same domain
      // as the source page
      "discover-only-same-origin": true,

      // If any of these regexes match, the page will not be queued for crawling.
      // If absent or empty, no limit
      // NB: seed URLs will always be crawled
      "discover-deny": [],

      // If this is present and non-empty, only URLs that match will be enqueued
      // for crawling.
      // NB: seed URLs will always be crawled
      "discover-allow": [
        {
          "from": ".+",
          "to": ".+"
        }
      ],

      // When discovering URLs, should we rewrite URLs from
      // https://example.com/collections/foo/products/bar -> https://example.com/products/bar
      "canonicalize-shopify-urls": true,

      // The maximum distance from a seed that a page can be, and still be crawled.
      // If absent, no limit
      "max-depth": 0,

      // The maximum number of pages to be crawled from this crawl
      // If absent, no limit
      // NB: seed URLs will always be crawled
      "max-pages": 5,

      // The maximum number of pages to be crawled per any single domain
      // If absent, no limit
      // NB: seed URLs will always be crawled
      "max-pages-per-domain": 5,

      // Should we cache responses? If yes, when should we re-fetch?
      // If multiple rules match, the lowest value wins.
      // no value -> never re-fetch
      // 0        -> always refetch
      // x > 0    -> refetch if older than X seconds
      "fetch-cache": {
        "staleness": [
          {
            // URLs will be tested with 2 values:
            // their URL, eg https://example.com/
            // their depth, eg depth:0 for a seed, depth:1 for a page discovered directly from a seed
            "url-regex": "/news?p=[0-9]+",
            "max-age": 10,
          },
        ]
      },

      // Extract information like title, metadesc, author, publish date,
      // preview image.
      "extract-seo": {
        // optional; absent implies .*
        "url-regex": ".*",

        // optional
        "database": "dbname",

        // optional; defaults to dss_seo
        "table": "dss_seo",

        // optional; if present, will try to extract body of article
        "extract-article": true
      },

      // Extract link graph
      "extract-links": {
        // optional; absent implies .*
        "url-regex": ".*",

        // optional
        "database": "dbname",

        // optional; defaults to dss_links
        "table": "dss_links",
      },

      // Extract JSON LD e-commerce listings
      "extract-ecommerce-jsonld": {
        // optional; absent implies .*
        "url-regex": ".*",

        // optional
        "database": "dbname",

        // optional; defaults to dss_ecommerce
        "table": "dss_ecommerce",
      },

      // Extract Shopify e-commerce listings
      "extract-ecommerce-shopify": {
        // optional; absent implies .*
        "url-regex": ".*",

        // optional
        "database": "dbname",

        // optional; defaults to dss_ecommerce
        "table": "dss_ecommerce",
      },

      // TODO: determine schema for this
      "extract-selectors": {
        // TODO: flag to indicate whether we should mark up the source to
        //       make it more amenable for CSS extraction

        // TODO: how to do invariant things, eg if we wanted to build
        //       out a join table of categories, we'd extract the category
        //       from the same root HTML element... how to infer that?

        // TODO: how to do many-to-many, if such a thing exists? maybe it's
        //       an advanced case and can be ignored.
        "url-regex": "/garments/",

        // optional
        "database": "dbname",
        "extractors": {
          "patterns": {
            "selector": ".w-full.container",
            "attributes": {
              "url!": [
                "h3 a",
                { "attribute": "href" }
              ],
              "name": [
                "h3 a",
                { "text": true }
              ],
              "designer_name": [
                "h3 + p a",
                { "text": true }
              ]
            }
          },
          "pattern_categories": {
            "selector": ".w-full.container",
            "attributes": {
              "url!": [
                "h3 a",
                { "attribute": "href" }
              ],
              "category!": [
                "html h1",
                { "text": true }
              ]
            }
          }
        ]
      }
    }
  }
}
```

## Usage notes

`datasette-scraper` requires a database in which to track its operational data,
and a database in which to store scraped data. They can be the same database.

Both databases will be put into WAL mode.

The ops database's `user_version` pragma will be used to track schema versions.

## Architecture

`datasette-scraper` handles the core bookkeeping for scraping--keeping track of
which URLs have been scraped, rate-limiting, making the actual request. It relies
on plugins to do almost all the interesting work. For example, following redirects,
navigating sitemaps, extracting data.

### Overview

```mermaid
flowchart LR
direction TB

subgraph init
  A(user starts crawl) --> B[get_seed_urls]
end

subgraph crawl [for each URL to crawl]
  before_fetch_url --> fetch_cached_url -> fetch_url
end

subgraph discover [for each URL crawled]
  discover_urls --> canonicalize_url --> canonicalize_url
  canonicalize_url --> x[queue URL to crawl]
  extract_from_response
end

init --> crawl --> discover
```

### Plugin hooks

Most plugins will only implement a few of these hooks.

`scraper` is an object that gives access to the `datasette` object,
and to some helper functions to access datas about the current crawl.

#### `get_seed_urls(config)`

Returns a list of strings representing seed URLs to be fetched.

They will be considered to have depth of 0, i.e. seeds.

#### `before_fetch_url(conn, config, url, depth, request_headers)`

`request_headers` is a dict, you can modify it to control what gets sent in the request.

Returns:
  - truthy to indicate this URL should not be crawled (for example, crawl max page limit)
  - falsy to express no opinion

> **Note** `before_fetch_url` vs `canonicalize_url`
>
> You can also use the `canonicalize_url` hook to reject URLs prior to them entering
> the crawl queue.
>
> A URL rejected by `canonicalize_url` will not result in an entry in the
> `dss_crawl_queue` and `dss_crawl_queue_history` tables.
>
> Which one you use is a matter of taste, in general, if you _never_ want the URL,
> reject it at canonicalization time.

#### `fetch_cached_url(conn, config, url, request_headers)`

Fetch a previously-cached HTTP response. The system will not have checked that
there was rate limit available before calling this.

Returns:
  - `None`, to indicate not handled
  - a response object, which is a dict with:
    - `fetched_at` - an ISO 8601 time like `2022-12-26 01:23:45.00`
    - `headers` - the response headers, eg `[['content-type', 'text/html']]`
    - `status_code` - the respones code, eg `200`
    - `text` - the response body

Once any plugin has returned a truthy value, no other plugin's `fetch_url`
hook will be invoked.


#### `fetch_url(conn, config, url, request_headers)`

Fetch an HTTP response from the live server. The system will have checked that there
was rate limit available before calling this.

Same return type and behaviour as `fetch_cached_url`.

#### `discover_urls(config, url, response)`

- TODO: probably this wants access to a (lazily) parsed form of the response ?

Returns a list of URLs to crawl.

The URLs can be either strings, in which case they'll get enqueued as depth + 1, or tuple of URL and depth. This can be useful for paginated index pages, where you'd like to crawl to a max depth of, say, 2, but treat all the index pages as being at depth 1.

> **Note**
>
> Sneaky plugins can abuse this hook to stash the response somewhere so
> that future runs can avoid hitting the origin server. If link discovery
> and extraction ever become a multiprocess thing, we'll add an explicit
> `after_fetch_url` hook.

#### `canonicalize_url(config, from_url, to_url, to_url_depth)`

Returns:
  - `False` to filter URL
  - an URL to be crawled instead
  - `None` or `True` to no-op

The URL to be crawled can be a string, or a tuple of string and depth.

This hook is useful for:
  - blocking URLs that we never want
  - canonicalizing URLs, for example, by omitting query parameters
  - restricting crawls to same origin
  - resetting depth for pagination

#### `extract_from_response(scraper, config, url, response)`

- TODO: probably this wants access to a (lazily) parsed form of the response ?

- TODO: do we care about trying to model relationships? Maybe we just rely
        on convention, and you have to manually extract all the tuples yourself.

Returns an object of rows-to-be-inserted-or-upserted:

```jsonc
{
  "dbname": {  // can be omitted, in which case, first DB will be used
    "tablename": [
      {
        "id!": "cldellow@gmail.com",  // ! indicates pkey, compound OK
        "name": "Colin",
        "age": 37
      }
    ]
  }
}
```

#### Metadata hooks

These hooks don't affect operation of the scrapes. They provide metadata to
help validate a user's configuration and show UI to configure a crawl.

##### config_schema()

Returns a [JSON schema](https://json-schema.org/understanding-json-schema/) describing the configuration this plugin accepts.

The schema is optional; if omitted, users will have to hand-edit their configurations
versus using interactive UI tools.

##### config_default_value()

Returns `None` to indicate that new crawls should not use this plugin by default.

Otherwise, returns a reasonable default value that conforms to the schema in `config_schema()`

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-scraper
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest

## Questions

### How can we provide a lazily parsed form of the response?

In many cases, code will be operating on the same DOM tree. We should provide a way
to access that where we lazily parse it at most once.

### Can `extract-selectors` be made user friendly?

e.g. you pick one of the URLs that you crawl. You click a link to post its content to
a website. The content gets scrubbed a bit first -- `script`, `style` and `svg` tags
are emptied (but left in place, so the DOM is unchanged).

Then you provide an expected output like:

```
{
  "patterns": [
    {
      "url!": "https://vikisews.com/vykrojki/shirts-t-shirts-blouses/kaia-blouse/",
      "name": "Kaia Blouse",
      "designer": "Viki Sews"
    }
  ],
  "pattern_categories": [
    {
      "url!": "https://vikisews.com/vykrojki/shirts-t-shirts-blouses/kaia-blouse/",
      "category!": "Button-Ups"
    }
  ]
}
```

Then we try to find a set of transforms that satisfies this, and show you the
sample output.

At any point, you have a base64-encoded representation of the input that you can
stash somewhere.

Eventually we could make the UI more user friendly, too.

This could run entirely in an AWS lambda.
