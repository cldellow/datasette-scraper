# datasette-scraper

[![PyPI](https://img.shields.io/pypi/v/datasette-scraper.svg)](https://pypi.org/project/datasette-scraper/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-scraper?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-scraper/releases)
[![Tests](https://github.com/cldellow/datasette-scraper/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-scraper/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-scraper/blob/main/LICENSE)

Adds website scraping abilities to Datasette.

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-scraper

## Usage

Usage instructions go here.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-scraper
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
