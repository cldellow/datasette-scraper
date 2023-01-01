import sqlite3

def remove_sigil(key):
    if key[-1] == '!':
        return key[:-1]

    return key

def quote(k):
    return '"{}"'.format(k)

def remove_sigils(keys):
    return [remove_sigil(key) for key in keys]

def handle(counts, factory, dbname, tablename, obj):
    inserted = 0
    updated = 0

    conn = factory(dbname)

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

    tpl = (dbname, tablename)

    if tpl in counts:
        counts[tpl] = (counts[tpl][0] + inserted, counts[tpl][1] + updated)
    else:
        counts[tpl] = (inserted, updated)


def handle_insert(factory, insert):
    counts = {}

    for k, v in insert.items():
        dbname = None

        if isinstance(v, dict):
            dbname = k
            for k, v in v.items():
                for obj in v:
                    handle(counts, factory, dbname, k, obj)
        else:
            for obj in v:
                handle(counts, factory, dbname, k, obj)

    return counts
