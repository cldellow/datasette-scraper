from datasette.app import Datasette
import sqlite3
import pytest


@pytest.mark.asyncio
async def test_plugin_is_installed(tmp_path):
    db_name = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_name)
    conn.close()
    datasette = Datasette(files=[db_name])
    response = await datasette.client.get("/-/plugins.json")
    assert response.status_code == 200
    installed_plugins = {p["name"] for p in response.json()}
    assert "datasette-scraper" in installed_plugins
