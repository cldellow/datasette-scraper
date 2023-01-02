import pytest
from .utils import lazy_connection_factory, lazy_connection_factory_with_default
from .inserts import handle_insert

def test_lazy_connection_factory(tmp_path):
    db_name = tmp_path / "db.sqlite"
    raw_factory = lazy_connection_factory({ 'default': db_name })
    factory = lazy_connection_factory_with_default(raw_factory, 'default')

    conn = factory(None)
    conn2 = factory('default')

    assert conn == conn2
    with pytest.raises(Exception):
        factory('unknown')

def test_inserts(tmp_path):
    db_name = tmp_path / "db.sqlite"
    raw_factory = lazy_connection_factory({ 'default': db_name })
    factory = lazy_connection_factory_with_default(raw_factory, 'default')

    handle_insert(factory, { 'tab': [ { 'a!': 'A', 'b': 2} ] })

    # It should have created the table, with appropriate nullability
    conn = factory(None)
    rows = conn.execute('SELECT a, b FROM tab').fetchall()
    assert rows == [('A', 2)]

    handle_insert(factory, { 'tab': [ { 'a!': 'B', 'b': None } ] })

    # A row that already exists should be upserted
    handle_insert(factory, { 'tab': [ { 'a!': 'A', 'b': 123 } ] })

    rows = conn.execute("SELECT a, b FROM tab WHERE a = 'A'").fetchall()
    assert rows == [('A', 123)]

    # missing columns should be added
    handle_insert(factory, { 'tab': [ { 'a!': 'C', 'b': 123, 'c': 234 } ] })

    rows = conn.execute("SELECT * FROM tab WHERE a = 'C'").fetchall()
    assert rows == [('C', 123, 234)]

    # can specify dbname
    handle_insert(factory, { 'default': { 'tab2': [{'a!': 'a'}] } })
    rows = conn.execute('SELECT * FROM tab2').fetchall()
    assert rows == [('a',)]

    # an upsert of all pkeys should work
    handle_insert(factory, { 'default': { 'tab2': [{'a!': 'a'}] } })
    rows = conn.execute('SELECT * FROM tab2').fetchall()
    assert rows == [('a',)]

    # reserved words are OK, if perhaps a bit ill-advised
    handle_insert(factory, { 'from': [ {'from!': 'a' } ] })
    handle_insert(factory, { 'from': [ {'from!': 'a', 'insert': 'b' } ] })

    rows = conn.execute('SELECT * FROM "from"').fetchall()
    assert rows == [('a', 'b')]

def test_inserts_index(tmp_path):
    db_name = tmp_path / "db.sqlite"
    raw_factory = lazy_connection_factory({ 'default': db_name })
    factory = lazy_connection_factory_with_default(raw_factory, 'default')

    handle_insert(factory, { 'tab': [ {'a@': 'a', '__delete': True }, { 'a@': 'a', 'b': 1}, { 'a@': 'a', 'b': 2} ] })

    # It should have created the table, with appropriate nullability
    conn = factory(None)
    rows = conn.execute('SELECT a, b FROM tab').fetchall()
    assert rows == [('a', 1), ('a', 2)]

    handle_insert(factory, { 'tab': [ { 'a@': 'a', '__delete': True }, { 'a@': 'a', 'b': 3 } ] })
    rows = conn.execute('SELECT a, b FROM tab').fetchall()
    assert rows == [('a', 3)]

    # You can ask us to delete a row
    handle_insert(factory, { 'tab': [ { 'a@': 'a', '__delete': True} ] })

    rows = conn.execute("SELECT a, b FROM tab WHERE a = 'a'").fetchall()
    assert rows == []

    # reserved words are OK, if perhaps a bit ill-advised
    handle_insert(factory, { 'from': [ {'from@': 'a' } ] })
    handle_insert(factory, { 'from': [ {'from@': 'a', 'insert': 'b' }, { 'from@' : 'a', 'insert': 'b' } ] })

    rows = conn.execute('SELECT * FROM "from" ORDER BY 1,2').fetchall()
    assert rows == [('a', None), ('a', 'b'), ('a', 'b')]

