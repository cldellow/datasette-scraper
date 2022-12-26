from datasette import hookimpl, Response
import html
from .config import get_database, ensure_schema


@hookimpl
def startup(datasette):
    # We import plugins on startup to avoid a circular dependency issue...
    # this is maybe sketchy? OTOH, if we moved the impl of this hook to
    # a separate file, that would have solved it, too.
    from .plugin import pm
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
