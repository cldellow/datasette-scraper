import sqlite3
import itertools

def remove_sigil(key):
    if key[-1] == '!' or key[-1] == '@':
        return key[:-1]

    return key

def quote(k):
    return '"{}"'.format(k)

def remove_sigils(keys):
    return [remove_sigil(key) for key in keys]

def handle(counts, conn, dbname, tablename, obj):
    tpl = (dbname, tablename)

    inserted = 0
    updated = 0
    deleted = 0

    if '__delete' in obj:
        clause = {}
        for k, v in obj.items():
            if k == '__delete':
                continue

            clause[k] = v

        try:
            with conn:
                rv = conn.execute(
                    'DELETE FROM {} WHERE {}'.format(
                        quote(tablename),
                        ', '.join([quote(remove_sigil(k)) + ' = ?' for k in clause.keys()])
                    ),
                    list(clause.values())
                )
                deleted += rv.rowcount

            if tpl in counts:
                counts[tpl] = (counts[tpl][0] + inserted, counts[tpl][1] + updated, counts[tpl][2] + deleted)
            else:
                counts[tpl] = (inserted, updated, deleted)

            return
        except:
            # The delete might fail because the table hasn't been created yet; ignore it
            return


    args = [
        quote(tablename),
        ', '.join([quote(k) for k in remove_sigils(obj.keys())]),
        ', '.join(['?'] * len(obj.keys()))
    ]

    bindings = list(obj.values())
    stmt = 'INSERT INTO {} ({}) VALUES ({})'.format(*args)

    # If they've specified a pkey, do an UPSERT
    keys = obj.keys()
    pkeys = remove_sigils([pk for pk in keys if pk[-1] == '!'])

    if pkeys and len(pkeys) != len(keys):
        stmt += ' ON CONFLICT({}) DO UPDATE SET {}'.format(
            ', '.join([quote(k) for k in pkeys]),
            ', '.join(['{} = ?'.format(quote(remove_sigil(k))) for k in keys if k[-1] != '!'])
        )

        for k in keys:
            if k[-1] != '!':
                bindings.append(obj[k])
    elif pkeys:
        stmt += ' ON CONFLICT({}) DO NOTHING'.format(
            ', '.join([quote(k) for k in pkeys])
        )
    retry = True

    while retry:
        retry = False
        try:
            #print('stmt={}, values={}'.format(stmt, bindings))

            cur = conn.cursor()
            # This SELECT 1 is a little hacky - we need to force the cursor to show
            # us the lastrowid inserted on this connection.
            cur.execute('SELECT 1')
            lastrowid = cur.lastrowid
            cur.execute(stmt, bindings)
            if cur.lastrowid and cur.lastrowid != lastrowid:
                inserted += 1
            else:
                updated += 1
        except sqlite3.OperationalError as e:
            if e.args[0] == 'no such table: {}'.format(tablename):
                colspec = ',\n'.join(['  {} ANY {}'.format(quote(remove_sigil(k)), 'NOT NULL' if k[-1] == '!' else '')  for k in keys])

                pkeyspec = ''
                if pkeys:
                    pkeyspec = ', PRIMARY KEY({})'.format(', '.join([quote(k) for k in pkeys]))

                create_stmt = 'CREATE TABLE {} (\n{}{})'.format(quote(tablename), colspec, pkeyspec)
                #print(create_stmt)
                conn.execute(create_stmt)

                indexed_columns = [remove_sigil(k) for k in keys if k.endswith('@')]

                if indexed_columns:
                    create_index_stmt = 'CREATE INDEX {} ON {}({})'.format(quote("idx_" + tablename + "_multiple"), quote(tablename), ', '.join([quote(col) for col in indexed_columns]))
                    conn.execute(create_index_stmt)
                retry = True
            elif e.args[0].startswith('table {} has no column named '.format(tablename)):
                needs_column = e.args[0].split(' ')[-1]
                for k in keys:
                    if remove_sigil(k) == needs_column:
                        alter_stmt = 'ALTER TABLE {} ADD COLUMN {} ANY'.format(quote(tablename), quote(needs_column))
                        #print(alter_stmt)
                        conn.execute(alter_stmt)
                        retry = True
                        break

                if not retry:
                    raise e
            else:
                raise

    if tpl in counts:
        counts[tpl] = (counts[tpl][0] + inserted, counts[tpl][1] + updated, counts[tpl][2] + deleted)
    else:
        counts[tpl] = (inserted, updated, deleted)

def get_existing_rows(conn, table, obj, all_columns):
    clause = {}
    for k, v in obj.items():
        if k == '__delete':
            continue

        clause[k] = v
    stmt = 'SELECT {} FROM {} WHERE {}'.format(
        ', '.join([quote(remove_sigil(k)) + " AS " + quote(k) for k in all_columns.keys()]),
        quote(table),
        ' AND '.join(['{} = ?'.format(quote(remove_sigil(k))) for k in clause.keys()])
    )
    #print(stmt)
    all_hits = conn.execute(stmt, list(clause.values())).fetchall()
    rv = []
    for hit in all_hits:
        obj = {}
        for i, k in enumerate(all_columns.keys()):
            obj[k] = hit[i]
        rv.append(obj)
    return rv

def rows_match(python_rows, sqlite_rows):
    # There are some challenges here that mean a naive check for membership with `in`
    # will sometimes return a false negative. We will do the correct thing, but
    # fail to optimize.
    #
    # 1) We type our columns as ANY, so SQLite defaults to the NUMERIC affinity
    #    if the input can be coerced to a number. Thus we get 123, which won't
    #    match a Python string of '123' or '123.0'
    #
    # 2) Dicts that are passed to us can have fewer keys than columns returned,
    #    but as long as all the keys that are present are in the row from the
    #    db, that's fine.
    if len(python_rows) != len(sqlite_rows):
        return False

    banned = {}
    for python_row in python_rows:
        ok = False
        for i in range(len(sqlite_rows)):
            if i in banned:
                continue

            sqlite_row = sqlite_rows[i]

            if python_row == sqlite_row:
                banned[i] = True
                ok = True
                # delete the row to try to be a bit faster
                break

        if ok:
            continue

        # Look again, and be more forgiving about types and missing fields.
        for i in range(len(sqlite_rows)):
            if i in banned:
                continue

            sqlite_row = sqlite_rows[i]

            all_ok = True
            for k, python_value in python_row.items():
                sqlite_value = sqlite_row[k]

                if sqlite_value == python_value:
                    continue

                if isinstance(sqlite_value, int) or isinstance(sqlite_value, float):
                    if str(sqlite_value) == python_value:
                        continue

                    try:
                        if sqlite_value == float(python_value):
                            continue
                    except ValueError:
                        pass


                all_ok = False
                break

            if all_ok:
                banned[i] = True
                ok = True
                break

        if not ok:
            #print('failed to find python row {} in sqlite_rows={}'.format(python_row, sqlite_rows))
            return False

    return len(banned) == len(sqlite_rows)

def prune_raw(conn, dbname, table, rows):
    """Try to elide operations that would not actually change the DB."""

    # Ensure deletes always happen first; mutate the input so the slow path
    # has same behaviour as the fast path
    rows.sort(key=lambda x: not '__delete' in x)

    # NB: This doesn't try to be a general purpose solution!
    # It optimizes for a very narrow use case: when all of the rows being
    # touched have the same sigiled columns.

    # Case 1: pkey upserts - they all have the name! sigil
    # { 'name!': 'Colin', 'gender': 'm' }
    # { 'name!': 'Jenn', 'gender': 'f' }
    #
    # This represents a bunch of pkey upserts. A given row can be elided if
    # there is an existing row that has that subset of columns.

    # Case 2: indexed column or pkey deletes - they all have the url@ sigil
    # { 'url@': 'example.org', '__delete': True }
    #
    # This can be elided if no rows exist with the given url.

    # Case 3: indexed column upserts - they all have the url@ sigil
    # { 'url@': 'example.org', '__delete': True }
    # { 'url@': 'example.org', 'to': 'google.com' }
    # { 'url@': 'example.org', 'to': 'bing.com' }
    #
    # We only handle the happiest path here - if all rows are present in the db,
    # omit this sequence of instructions.

    # Any other case is ignored and falls through to the slow path.

    sigil_columns = None
    all_columns = {}
    for row in rows:
        x = {}
        for k in row.keys():
            if k[-1] == '!' or k[-1] == '@':
                x[k] = True
                all_columns[k] = k
            elif k != '__delete':
                all_columns[k] = k

        if sigil_columns == None:
            sigil_columns = x
        elif sigil_columns != x:
            print('! sigil mismatch: {} and  {}'.format(sigil_columns, x))
            return rows

    if not sigil_columns:
        print('! no sigils')
        return rows

    # They're all the same, fast path is permitted.
    #
    # Group the rows by the values of their sigils.
    key_columns = list(sigil_columns.keys())
    grouped_rows = itertools.groupby(rows, key=lambda row: tuple([row[k] for k in key_columns]))

    all_sigils_are_pkey = True
    all_sigils_are_index = True
    for sigil_column in sigil_columns:
        if sigil_column[-1] != '!':
            all_sigils_are_pkey = False
        if sigil_column[-1] != '@':
            all_sigils_are_index = False

    new_rows = []
    for (key, grouper) in grouped_rows:
        key_rows = list(grouper)

        if len(key_rows) == 1 and '__delete' in key_rows[0]:
            #print('optimizable delete: key={} rows={}'.format(key, key_rows[0]))
            #TODO: optimization: this could just be a SELECT EXISTS(...)
            existing_rows = get_existing_rows(conn, table, key_rows[0], all_columns)
            if existing_rows:
                new_rows.extend(key_rows)
        elif len(key_rows) > 1 and '__delete' in key_rows[0] and not '__delete' in key_rows[1]:
            #print('optimizable delete/insert: key={} rows={}'.format(key, key_rows))
            existing_rows = get_existing_rows(conn, table, key_rows[0], all_columns)
            #print(existing_rows)

            if not rows_match(key_rows[1:], existing_rows):
                #print('failed to optimize delete/insert')
                #print('optimizable delete/insert: key={} rows={}'.format(key, key_rows))
                new_rows.extend(key_rows)
        elif not '__delete' in key_rows[0] and all_sigils_are_pkey:
            #print('optimizable pkey: key={} rows={}'.format(key, key_rows))

            for row in key_rows:
                existing_rows = get_existing_rows(conn, table, row, all_columns)

                if len(existing_rows) != 1:
                    new_rows.append(row)
                elif existing_rows[0] != row:
                    new_rows.append(row)
        else:
            #print('not optimizable: key={} rows={}'.format(key, key_rows))
            new_rows.extend(key_rows)


    return new_rows

def prune(conn, dbname, table, rows):
    try:
        return prune_raw(conn, dbname, table, rows)
    except sqlite3.OperationalError as e:
        # Probably this table has not been created yet, or the user is adding
        # a column. Fall through to slow path.
        #print(e)
        return rows

def handle_insert(factory, insert):
    # This function does a _lot_. It can:
    # - create tables
    # - create indexes
    # - add columns to existing tables
    # - delete rows that match a predicate
    # - insert rows
    #
    # Additionally, it tries to avoid doing write transactions needlessly. Given a set of input,
    # it will try to determine if the database would actually be changed. It does this interrogation
    # using only read transactions. If the database would not be changed, no write lock is required.
    #
    # If the database _would_ be changed, it tries to issue the smallest set of changes, so that
    # other writers are blocked for the smallest time and we don't bloat the wal journal.
    counts = {}

    for k, v in insert.items():
        dbname = None

        if isinstance(v, dict):
            dbname = k
            conn = factory(dbname)

            for table, objs in v.items():
                objs = prune(conn, dbname, table, objs)
                counts[(dbname, table)] = (0, 0, 0)
                for obj in objs:
                    handle(counts, conn, dbname, table, obj)
        else:
            conn = factory(dbname)
            table = k
            objs = v
            counts[(dbname, table)] = (0, 0, 0)
            objs = prune(conn, dbname, table, objs)
            for obj in objs:
                handle(counts, conn, dbname, table, obj)

    return counts
