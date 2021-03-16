"""
Basic script to run timetagger.

You can use this to run timetagger locally. If you want to run it
online, you'd need to take care of authentication.
"""

import logging
from pkg_resources import resource_filename

import asgineer
from timetagger.server import (
    default_api_handler,
    create_assets_from_dir,
    enable_service_worker,
    get_webtoken_unsafe,
)


logger = logging.getLogger("asgineer")


# Create dict with assets. You could add/replace assets here.
common_assets = create_assets_from_dir(resource_filename("timetagger.common", "."))
apponly_assets = create_assets_from_dir(resource_filename("timetagger.app", "."))
image_assets = create_assets_from_dir(resource_filename("timetagger.images", "."))
page_assets = create_assets_from_dir(resource_filename("timetagger.pages", "."))

root_assets = {}
root_assets.update(common_assets)
root_assets.update(image_assets)
root_assets.update(page_assets)

app_assets = {}
app_assets.update(common_assets)
app_assets.update(image_assets)
app_assets.update(apponly_assets)

# Enable the service worker so the app can be used offline and is installable
enable_service_worker(app_assets)

# Turn asset dicts into a handlers. This feature of Asgineer provides
# lightning fast handlers that support compression and HTTP caching.
root_asset_handler = asgineer.utils.make_asset_handler(root_assets, max_age=0)
app_asset_handler = asgineer.utils.make_asset_handler(app_assets, max_age=0)


@asgineer.to_asgi
async def main_handler(request):
    """
    The main handler where we delegate to the API handler or the
    asset handlers created above.

    We serve at /timetagger for a few reasons, one being that the service
    worker won't interfere with other stuff you might server at localhost.
    """

    if request.path == "/":
        return 307, {"Location": "/timetagger/"}, b""  # Redirect

    elif request.path.startswith("/timetagger/"):
        if request.path.startswith("/timetagger/api/v2/"):
            path = request.path[19:].strip("/")
            if path == "webtoken_for_localhost":
                return await webtoken_for_localhost(request)
            else:
                return await default_api_handler(request, path)
        elif request.path.startswith("/timetagger/app/"):
            path = request.path[16:].strip("/")
            status, headers, body = await app_asset_handler(request, path)
            headers["X-Frame-Options"] = "sameorigin"  # Prevent clickjacking
            return status, headers, body
        else:
            path = request.path[12:].strip("/")
            return await root_asset_handler(request, path)
    else:
        return 404, {}, "only serving at /timetagger/"


async def webtoken_for_localhost(request):
    """An authentication handler that provides a webtoken when the hostname is
    localhost. If you run TimeTagger on the web, you must implement
    your own authentication workflow that ends with providing the client
    with a TimeTagger webtoken.

    Examples could be:
      * Implement username/password authentication.
      * Using an OAuth workflow via a trusted provider like Google or Github.
      * Using Auth0 to authenticate and exchanging its JWT with a webtoken.
      * Using Did to authenticate via email and exchanging its JWT for a webtoken.
    """

    # Establish that we can trust the client
    if request.host not in ("localhost", "127.0.0.1"):
        return 403, {}, "Not on localhost"

    # Define the username (i.e. email) and return the corersponding webtoken
    auth_info = dict(email="defaultuser")
    return get_webtoken_unsafe(auth_info)


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
