from setuptools import setup
import os

VERSION = "0.5"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="datasette-scraper",
    description="Adds website scraping abilities to Datasette.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Colin Dellow",
    url="https://github.com/cldellow/datasette-scraper",
    project_urls={
        "Issues": "https://github.com/cldellow/datasette-scraper/issues",
        "CI": "https://github.com/cldellow/datasette-scraper/actions",
        "Changelog": "https://github.com/cldellow/datasette-scraper/releases",
    },
    license="Apache License, Version 2.0",
    classifiers=[
        "Framework :: Datasette",
        "License :: OSI Approved :: Apache Software License"
    ],
    version=VERSION,
    packages=["datasette_scraper", "datasette_scraper.plugins"],
    entry_points={"datasette": ["scraper = datasette_scraper"]},
    install_requires=["datasette", "selectolax", "datasette-template-sql", "pluggy", "httpx", "zstandard", "more-itertools"],
    extras_require={"test": ["wheel", "pytest", "pytest-asyncio", "pytest-watch", "coverage"]},
    package_data={
        "datasette_scraper": ["static/*", "templates/*"]
    },
    python_requires=">=3.7",
)
