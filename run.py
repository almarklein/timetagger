"""
Basic script to run timetagger.

You can use this to run timetagger locally. If you want to run it
online, you'd need to take care of authentication.
"""

import logging
from pkg_resources import resource_filename

import asgineer
from timetagger.server import api_handler, create_assets_from_dir, enable_service_worker


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
        # Redirect
        return 307, {"Location": "/timetagger/"}, b""

    elif request.path.startswith("/timetagger/"):
        if request.path.startswith("/timetagger/api/"):
            # Get apipath
            prefix = "/timetagger/api/v1/"
            if not request.path.startswith(prefix):
                return 404, {}, "invalid API path"
            apipath = request.path[len(prefix) :].strip("/")
            # This is where you'd handle authentication ...
            user = "default"
            return await api_handler(request, apipath, user)
        elif request.path.startswith("/timetagger/app/"):
            path = request.path[16:]
            status, headers, body = await app_asset_handler(request, path)
            headers["X-Frame-Options"] = "sameorigin"  # Prevent clickjacking
            return status, headers, body
        else:
            path = request.path[12:]
            return await root_asset_handler(request, path)
    else:
        return 404, {}, "only serving at /timetagger/"


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
