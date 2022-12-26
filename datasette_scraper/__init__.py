from datasette import hookimpl, Response
import html
from .config import get_database, ensure_schema

@hookimpl
def startup(datasette):
    async def inner():
        db = get_database(datasette)
        await ensure_schema(db)

    return inner

#async def scraper(request):
#    return Response.html(
#        "Hello"
#    )
#
#@hookimpl
#def register_routes():
#    return [(r"^/-/scraper$", scraper)]
