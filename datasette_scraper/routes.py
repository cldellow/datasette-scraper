import json
from datasette import Response
from datasette.utils import tilde_encode
from .config import enabled_databases
from .workers import seed_crawl, discover_missing_dictionaries
from .zstd import train_zstd_dict

async def crawl_exists(datasette, db, crawl_id):
    db = datasette.databases[db]
    rv = await db.execute('SELECT id FROM dss_crawl WHERE id = ?', [crawl_id])
    for row in rv:
        return True

    return False

def redirect_to_crawl(db_name, id):
    return Response.redirect('/{}/dss_crawl/{}'.format(db_name, id))

async def scraper_upsert(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    form = await request.post_vars()

    id = int(form['id'])
    config = json.loads(form['config'])
    db_name = request.url_vars['db']

    name = config['name']
    config.pop('name')

    db = datasette.databases[db_name]

    if not id:
        rv = await db.execute_write('INSERT INTO dss_crawl(name, config) VALUES (?, ?)', [name, json.dumps(config)], block=True)
        id = rv.lastrowid
    else:
        await db.execute_write('UPDATE dss_crawl SET name = ?, config = ? WHERE id = ?', [name, json.dumps(config), id], block=True)

    return redirect_to_crawl(db_name, id)

async def scraper_discover_missing_dictionaries(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    db_name = request.url_vars['db']
    db = datasette.databases[db_name]
    await discover_missing_dictionaries(db)

    return Response.redirect('/{}/dss_zstd_dict'.format(db.name))

async def scraper_host_rate_limit(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    form = await request.post_vars()

    host = form['host']
    delay_seconds = float(form['delay_seconds'])

    db_name = request.url_vars['db']
    db = datasette.databases[db_name]

    await db.execute_write('UPDATE dss_host_rate_limit SET delay_seconds = ? WHERE host = ?', [delay_seconds, host], block=True)

    return Response.redirect('/{}/dss_host_rate_limit/{}'.format(db.name, tilde_encode(host)))


async def scraper_crawl_id(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    id = int(request.url_vars["id"])
    db_name = request.url_vars['db']

    if not await crawl_exists(datasette, db_name, id):
        return Response('not found', status=404)

    context = {
        'dss_id': id
    }

    return Response.html(
        await datasette.render_template('/pages/-/scraper/crawl.html', context=context, request=request)
    )

async def scraper_crawl_id_start(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    id = int(request.url_vars["id"])
    db_name = request.url_vars['db']

    if not await crawl_exists(datasette, db_name, id):
        return Response('not found', status=404)

    db = datasette.databases[db_name]

    rv = await db.execute_write("INSERT INTO dss_job(crawl_id) VALUES (?)", [id], block=True);
    job_id = rv.lastrowid

    await seed_crawl(db, job_id)

    return redirect_to_crawl(db_name, id)

async def scraper_crawl_id_cancel(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    crawl_id = int(request.url_vars["id"])
    db_name = request.url_vars['db']

    if not await crawl_exists(datasette, db_name, crawl_id):
        return Response('not found', status=404)

    def cancel(conn):
        with conn:
            rv = conn.execute('SELECT id FROM dss_job WHERE crawl_id = ? AND finished_at IS NULL', [crawl_id])
            job_id, = rv.fetchone()

            if job_id:
                conn.execute("UPDATE dss_job SET status = 'cancelled', finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [job_id])
                conn.execute("DELETE FROM dss_crawl_queue WHERE job_id = ?", [job_id])

    db = datasette.databases[db_name]

    await db.execute_write_fn(cancel)

    return redirect_to_crawl(db_name, crawl_id)


async def scraper_crawl_id_edit(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    db_name = request.url_vars['db']
    id = int(request.url_vars["id"])

    if not await crawl_exists(datasette, db_name, id):
        return Response('not found', status=404)

    return Response.html(
        await datasette.render_template('new-crawl.html', request=request)
    )

async def scraper_new(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    return Response.html(
        await datasette.render_template('new-crawl.html', request=request)
    )


def get_routes(datasette):
    routes = []

    for db in enabled_databases(datasette):
        routes.append((r"^/(?P<db>{})/-/scraper/new$".format(db), scraper_new))
        routes.append((r"^/(?P<db>{})/-/scraper/upsert$".format(db), scraper_upsert))
        routes.append((r"^/(?P<db>{})/-/scraper/host-rate-limit$".format(db), scraper_host_rate_limit))
        routes.append((r"^/(?P<db>{})/-/scraper/crawl/(?P<id>[0-9]+)/start$".format(db), scraper_crawl_id_start))
        routes.append((r"^/(?P<db>{})/-/scraper/crawl/(?P<id>[0-9]+)/cancel$".format(db), scraper_crawl_id_cancel))
        routes.append((r"^/(?P<db>{})/-/scraper/discover-missing-dictionaries$".format(db), scraper_discover_missing_dictionaries))

    return routes
