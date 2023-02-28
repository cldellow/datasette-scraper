from datasette.app import Datasette
import sqlite3
import pytest

import datasette_scraper.config


@pytest.mark.asyncio
async def test_plugin_is_installed(tmp_path):
    # Ensure we don't hit the cached values
    datasette_scraper.config._enabled_databases = None
    db_name = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_name)
    conn.close()
    datasette = Datasette(files=[db_name])
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-scraper" in installed_plugins

@pytest.mark.asyncio
async def test_plugin_tolerates_existing_tables(tmp_path):
    # Ensure we don't hit the cached values
    datasette_scraper.config._enabled_databases = None

    metadata = {
        'databases': {
            'db': {
                'plugins': {
                    'datasette-scraper': {
                    }
                }
            }
        }
    }

    db_name = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_name)
    with conn:
        conn.execute('CREATE TABLE x(x TEXT NOT NULL PRIMARY KEY)')
        conn.execute('CREATE UNIQUE INDEX y ON x(x)')
    conn.close()
    datasette = Datasette(
        files=[db_name],
        metadata=metadata
    )
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-scraper" in installed_plugins
