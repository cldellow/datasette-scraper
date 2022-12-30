import pytest
from .utils import lazy_connection_factory
from .inserts import handle_insert

def test_lazy_connection_factory(tmp_path):
    db_name = tmp_path / "db.sqlite"
    factory = lazy_connection_factory('default', { 'default': db_name })

    conn = factory(None)
    conn2 = factory('default')

    assert conn == conn2
    with pytest.raises(Exception):
        factory('unknown')

def test_inserts(tmp_path):
    db_name = tmp_path / "db.sqlite"
    factory = lazy_connection_factory('default', { 'default': db_name })

    handle_insert(factory, { 'tab': [ { 'a!': 'A', 'b?': 2, 'c': 3 } ] })

    # It should have created the table, with appropriate nullability
    conn = factory(None)
    rows = conn.execute('SELECT a, b, c FROM tab').fetchall()
    assert rows == [('A', 2, 3)]

    handle_insert(factory, { 'tab': [ { 'a!': 'B', 'b?': None, 'c': 3 } ] })

    # ...but not a null c
    with pytest.raises(Exception):
        handle_insert(factory, { 'tab': [ { 'a!': 'B', 'b?': None, 'c': None } ] })

    # A row that already exists should be upserted
    handle_insert(factory, { 'tab': [ { 'a!': 'A', 'b?': 123, 'c': 234 } ] })

    rows = conn.execute("SELECT a, b, c FROM tab WHERE a = 'A'").fetchall()
    assert rows == [('A', 123, 234)]

    # missing columns should be added
    # in theory they can be flagged as NOT NULL, but only if the table is empty,
    # so in practice, they're going to have to be nullable.
    handle_insert(factory, { 'tab': [ { 'a!': 'C', 'b?': 123, 'c': 234, 'd?': 'd' } ] })

    rows = conn.execute("SELECT * FROM tab WHERE a = 'C'").fetchall()
    assert rows == [('C', 123, 234, 'd')]

    # can specify dbname
    handle_insert(factory, { 'default': { 'tab2': [{'a!': 'a'}] } })
    rows = conn.execute('SELECT * FROM tab2').fetchall()
    assert rows == [('a',)]

    # an upsert of all pkeys should work
    handle_insert(factory, { 'default': { 'tab2': [{'a!': 'a'}] } })
    rows = conn.execute('SELECT * FROM tab2').fetchall()
    assert rows == [('a',)]

    # reserved words are OK
    handle_insert(factory, { 'from': [ {'from!': 'a' } ] })
    handle_insert(factory, { 'from': [ {'from!': 'a', 'insert?': 'b' } ] })

    rows = conn.execute('SELECT * FROM "from"').fetchall()
    assert rows == [('a', 'b')]

