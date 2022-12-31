import json
from datasette import Response
from datasette.utils import tilde_encode
from .config import get_database
from .workers import seed_crawl

async def crawl_exists(datasette, crawl_id):
    db = get_database(datasette)
    rv = await db.execute('SELECT id FROM dss_crawl WHERE id = ?', [crawl_id])
    for row in rv:
        return True

    return False

def redirect_to_crawl(datasette, id):
    db_name = get_database(datasette).name
    return Response.redirect('/{}/dss_crawl/{}'.format(db_name, id))

async def scraper_upsert(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    form = await request.post_vars()

    id = int(form['id'])
    config = json.loads(form['config'])

    name = config['name']
    config.pop('name')

    db = get_database(datasette)

    if not id:
        rv = await db.execute_write('INSERT INTO dss_crawl(name, config) VALUES (?, ?)', [name, json.dumps(config)], block=True)
        id = rv.lastrowid
    else:
        await db.execute_write('UPDATE dss_crawl SET name = ?, config = ? WHERE id = ?', [name, json.dumps(config), id], block=True)

    return redirect_to_crawl(datasette, id)

async def scraper_host_rate_limit(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    form = await request.post_vars()

    host = form['host']
    delay_seconds = float(form['delay_seconds'])

    db = get_database(datasette)

    await db.execute_write('UPDATE dss_host_rate_limit SET delay_seconds = ? WHERE host = ?', [delay_seconds, host], block=True)

    return Response.redirect('/{}/dss_host_rate_limit/{}'.format(db.name, tilde_encode(host)))


async def scraper_crawl_id(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    id = int(request.url_vars["id"])

    if not await crawl_exists(datasette, id):
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

    if not await crawl_exists(datasette, id):
        return Response('not found', status=404)

    db = get_database(datasette)

    rv = await db.execute_write("INSERT INTO dss_job(crawl_id) VALUES (?)", [id], block=True);
    job_id = rv.lastrowid

    # TODO: handle UNIQUE constraint failed: dss_job.crawl_id

    seed_crawl(job_id)

    return redirect_to_crawl(datasette, id)

async def scraper_crawl_id_cancel(datasette, request):
    if request.method != 'POST':
        return Response('Unexpected method', status=405)

    crawl_id = int(request.url_vars["id"])

    if not await crawl_exists(datasette, crawl_id):
        return Response('not found', status=404)

    def cancel(conn):
        with conn:
            rv = conn.execute('SELECT id FROM dss_job WHERE crawl_id = ? AND finished_at IS NULL', [crawl_id])
            job_id, = rv.fetchone()

            if job_id:
                conn.execute("UPDATE dss_job SET finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [job_id])
                conn.execute("DELETE FROM dss_crawl_queue WHERE job_id = ?", [job_id])

    db = get_database(datasette)

    await db.execute_write_fn(cancel)

    return redirect_to_crawl(datasette, crawl_id)


async def scraper_crawl_id_edit(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    id = int(request.url_vars["id"])

    if not await crawl_exists(datasette, id):
        return Response('not found', status=404)

    db = get_database(datasette)

    return Response.html(
        await datasette.render_template('/pages/-/scraper/new.html', request=request)
    )


routes = [
    (r"^/-/scraper/upsert$", scraper_upsert),
    (r"^/-/scraper/host-rate-limit$", scraper_host_rate_limit),
    # CONSIDER: Should we hijack the usual Datasette table / row routes?
    # (r"^/test/dss_crawl/(?P<id>1)$", scraper_crawl_id),
    (r"^/-/scraper/crawl/(?P<id>[0-9]+)/start$", scraper_crawl_id_start),
    (r"^/-/scraper/crawl/(?P<id>[0-9]+)/cancel$", scraper_crawl_id_cancel),
]
