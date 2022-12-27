import json
from datasette import Response
from .config import get_database

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
        rv = await db.execute_write('INSERT INTO _dss_crawl(name, config) VALUES (?, ?)', [name, json.dumps(config)], block=True)
        id = rv.lastrowid
    else:
        await db.execute_write('UPDATE _dss_crawl SET name = ?, config = ? WHERE id = ?', [name, json.dumps(config), id], block=True)

    return Response.redirect('/-/scraper/crawl/{}'.format(id))

async def scraper_crawl_id(datasette, request):
    if request.method != 'GET':
        return Response('Unexpected method', status=405)

    id = request.url_vars["id"]

    print(id)

    db = get_database(datasette)

    return Response.html(
        await datasette.render_template('/pages/-/scraper/new.html', request=request)
    )
    #return await datasette.render_template('index.html', context=None, request=request)
    #return Response.html('hi {}'.format(id))


routes = [
    (r"^/-/scraper/upsert$", scraper_upsert),
    (r"^/-/scraper/crawl/(?P<id>[0-9]+)$", scraper_crawl_id),
]
