"""
Basic script to run timetagger.

You can use this to run timetagger locally. If you want to run it
online, you'd need to take care of authentication.
"""

import logging
from pkg_resources import resource_filename

import asgineer
from timetagger.server import api_handler, create_assets_from_dir


logger = logging.getLogger("asgineer")


# Create dict with assets
assets = {}
assets.update(create_assets_from_dir(resource_filename("timetagger.client", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.static", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.images", ".")))

# Uncomment the line below to include the TimeTagger website
# assets.update(create_assets_from_dir(resource_filename("timetagger.website", "/")))

# Turn asset dict into a handler. This feature of Asgineer provides
# lightning fast handlers that support compression and HTTP caching.
asset_handler = asgineer.utils.make_asset_handler(assets, max_age=0)


@asgineer.to_asgi
async def main_handler(request):
    """The main handler where we delegate to the API handler or the
    asset handlers created above.
    """

    if request.path.startswith("/api/"):
        # Get apipath
        prefix = "/api/v1/"
        if not request.path.startswith(prefix):
            return 404, {}, "invalid API path"
        apipath = request.path[len(prefix) :].strip("/")
        # This is where you'd handle authentication ...
        user = "default"
        return await api_handler(request, apipath, user)
    else:
        status, headers, body = await asset_handler(request)
        headers["X-Frame-Options"] = "sameorigin"  # Prevent clickjacking
        return status, headers, body


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", "0.0.0.0:80", log_level="warning")
