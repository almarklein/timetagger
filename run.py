"""
Basic script to run timetagger.

You can use this to run timetagger locally. If you want to run it
online, you'd need to take care of authentication.
"""

import logging
from pkg_resources import resource_filename

import asgineer
from timetagger import config
from timetagger.server import (
    authenticate,
    AuthException,
    api_handler_triage,
    get_webtoken_unsafe,
    create_assets_from_dir,
    enable_service_worker,
)


logger = logging.getLogger("asgineer")

# Get sets of assets provided by TimeTagger
common_assets = create_assets_from_dir(resource_filename("timetagger.common", "."))
apponly_assets = create_assets_from_dir(resource_filename("timetagger.app", "."))
image_assets = create_assets_from_dir(resource_filename("timetagger.images", "."))
page_assets = create_assets_from_dir(resource_filename("timetagger.pages", "."))

# Combine into two groups. You could add/replace assets here.
app_assets = dict(**common_assets, **image_assets, **apponly_assets)
web_assets = dict(**common_assets, **image_assets, **page_assets)

# Enable the service worker so the app can be used offline and is installable
enable_service_worker(app_assets)

# Turn asset dicts into handlers. This feature of Asgineer provides
# lightning fast handlers that support compression and HTTP caching.
app_asset_handler = asgineer.utils.make_asset_handler(app_assets, max_age=0)
web_asset_handler = asgineer.utils.make_asset_handler(web_assets, max_age=0)


@asgineer.to_asgi
async def main_handler(request):
    """
    The main handler where we delegate to the API or asset handler.

    We serve at /timetagger for a few reasons, one being that the service
    worker won't interfere with other stuff you might serve on localhost.
    """

    if request.path == "/":
        return 307, {"Location": "/timetagger/"}, b""  # Redirect

    elif request.path.startswith("/timetagger/"):

        if request.path.startswith("/timetagger/api/v2/"):
            path = request.path[19:].strip("/")
            return await api_handler(request, path)
        elif request.path.startswith("/timetagger/app/"):
            path = request.path[16:].strip("/")
            return await app_asset_handler(request, path)
        else:
            path = request.path[12:].strip("/")
            return await web_asset_handler(request, path)

    else:
        return 404, {}, "only serving at /timetagger/"


async def api_handler(request, path):
    """The default API handler. Designed to be short, so that
    applications that implement alternative authentication and/or have
    more API endpoints can use this as a starting point.
    """

    # Some endpoints do not require authentication
    if not path and request.method == "GET":
        return 200, {}, "See https://timetagger.readthedocs.io"
    elif path.startswith("webtoken"):
        # The client-side that requests these is in pages/login.md
        if path == "webtoken_for_localhost":
            return await webtoken_for_localhost(request)
        elif path == "webtoken_for_credentials":
            return await webtoken_for_credentials(request)
        else:
            404, {}, "unknown auth path"

    # Authenticate and get user db
    try:
        auth_info, db = await authenticate(request)
    except AuthException as err:
        return 401, {}, f"unauthorized: {err}"

    # Handle endpoints that require authentication
    return await api_handler_triage(request, path, auth_info, db)


CREDENTIALS = [x.strip() for x in config.credentials.replace(";", ",").split(",")]


async def webtoken_for_credentials(request):
    """An authentication handler to exchange credentials for a webtoken.
    The credentials are set via the config and are intended to support
    at max a handful of users. For more sophisticated authentication
    roll your own `run.py` with your own authentication handler.
    See `get_webtoken_unsafe()` for details.
    """

    # Get credentials from request
    user = request.querydict["username"]
    pwhash = request.querydict["pwhash"]
    # Check
    key = user + ":" + pwhash
    if user and key in CREDENTIALS:
        token = await get_webtoken_unsafe(user)
        return 200, {}, dict(token=token)
    else:
        return 403, {}, "Invalid credentials"


async def webtoken_for_localhost(request):
    """An authentication handler that provides a webtoken when the
    hostname is localhost. See `get_webtoken_unsafe()` for details.
    """

    # Establish that we can trust the client
    if request.host not in ("localhost", "127.0.0.1"):
        return 403, {}, "forbidden: must be on localhost"

    # Return the webtoken for the default user
    token = await get_webtoken_unsafe("defaultuser")
    return 200, {}, dict(token=token)


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", config.bind, log_level="warning")
