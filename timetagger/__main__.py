"""
Default script to run timetagger.

The timetagger library behaves like a framework; it provides the
building blocks to setup a timetracking app. This script puts things
together in the "default way". You can also create your own script to
customize/extend timetagger or embed in it a larger application.

A major hurdle in deploying an app like this is user authentication.
Timetagger implements its own token-based authentication, but it needs
to be "bootstrapped": the server needs to provide the first webtoken
when it has established trust in some way.

This script implements two methods to do this:
* A single-user login when client and server are on the same machine (localhost).
* Authentication with credentials specified as config params.

If you want another form of login, you will need to implement that yourself,
using a modified version of this script.
"""

import sys
import json
import logging
from base64 import b64decode
from pkg_resources import resource_filename

import bcrypt
import asgineer
import itemdb
import pscript
import iptools
import timetagger
from timetagger import config
from timetagger.server import (
    authenticate,
    AuthException,
    api_handler_triage,
    get_webtoken_unsafe,
    create_assets_from_dir,
    enable_service_worker,
)


# Special hooks exit early
if __name__ == "__main__" and len(sys.argv) >= 2:
    if sys.argv[1] in ("--version", "version"):
        print("timetagger", timetagger.__version__)
        print("asgineer", asgineer.__version__)
        print("itemdb", itemdb.__version__)
        print("pscript", pscript.__version__)
        sys.exit(0)


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
        if request.path == "/timetagger/status":
            return 200, {}, "ok"
        elif request.path.startswith("/timetagger/api/v2/"):
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
    elif path == "bootstrap_authentication":
        # The client-side that requests these is in pages/login.md
        return await get_webtoken(request)

    # Authenticate and get user db
    try:
        auth_info, db = await authenticate(request)
        # Only validate if proxy auth is enabled
        if config.proxy_auth_enabled:
            await validate_auth(request, auth_info)
    except AuthException as err:
        return 401, {}, f"unauthorized: {err}"

    # Handle endpoints that require authentication
    return await api_handler_triage(request, path, auth_info, db)


async def get_webtoken(request):
    """Exhange some form of trust for a webtoken."""

    auth_info = json.loads(b64decode(await request.get_body()))
    method = auth_info.get("method", "unspecified")

    if method == "localhost":
        return await get_webtoken_localhost(request, auth_info)
    elif method == "usernamepassword":
        return await get_webtoken_usernamepassword(request, auth_info)
    elif method == "proxy":
        return await get_webtoken_proxy(request, auth_info)
    else:
        return 401, {}, f"Invalid authentication method: {method}"


async def get_webtoken_proxy(request, auth_info):
    """An authentication handler that provides a webtoken when
    the user is autheticated through a trusted reverse proxy
    by a given header. See `get_webtoken_unsafe()` for details.
    """

    # Check if proxy auth is enabled
    if not config.proxy_auth_enabled:
        return 403, {}, "forbidden: proxy auth is not enabled"

    # Check if the request comes from a trusted proxy
    client = request.scope["client"][0]
    if client not in TRUSTED_PROXIES:
        return 403, {}, "forbidden: the proxy is not trusted"

    # Get username from request header
    user = await get_username_from_proxy(request)
    if not user:
        return 403, {}, "forbidden: no proxy user provided"

    # Return the webtoken for proxy user
    token = await get_webtoken_unsafe(user)
    return 200, {}, dict(token=token)


async def get_username_from_proxy(request):
    """Returns the username that is provided by the reverse proxy
    through the request headers.
    """

    return request.headers.get(config.proxy_auth_header.lower(), "").strip()


async def get_webtoken_usernamepassword(request, auth_info):
    """An authentication handler to exchange credentials for a webtoken.
    The credentials are set via the config and are intended to support
    a handful of users. See `get_webtoken_unsafe()` for details.
    """
    # This approach uses bcrypt to hash the passwords with a salt,
    # and is therefore much safer than e.g. BasicAuth.

    # Get credentials from request
    user = auth_info.get("username", "").strip()
    pw = auth_info.get("password", "").strip()
    # Get hash for this user
    hash = CREDENTIALS.get(user, "")
    # Check
    if user and hash and bcrypt.checkpw(pw.encode(), hash.encode()):
        token = await get_webtoken_unsafe(user)
        return 200, {}, dict(token=token)
    else:
        return 403, {}, "Invalid credentials"


async def get_webtoken_localhost(request, auth_info):
    """An authentication handler that provides a webtoken when the
    hostname is localhost. See `get_webtoken_unsafe()` for details.
    """

    # Don't allow localhost validation when proxy auth is enabled
    if config.proxy_auth_enabled:
        return 403, {}, "forbidden: disabled when proxy auth is available"
    # Establish that we can trust the client
    if request.host not in ("localhost", "127.0.0.1"):
        return 403, {}, "forbidden: must be on localhost"
    # Return the webtoken for the default user
    token = await get_webtoken_unsafe("defaultuser")
    return 200, {}, dict(token=token)


async def validate_auth(request, auth_info):
    """Validates that the autheticated user is still the same that
    is provided by the reverse proxy.
    """

    # Check that the proxy user is the same
    proxy_user = await get_username_from_proxy(request)
    if proxy_user and proxy_user != auth_info["username"]:
        raise AuthException("Autheticated user does not match proxy user")


def load_credentials():
    d = {}
    for s in config.credentials.replace(";", ",").split(","):
        name, _, hash = s.partition(":")
        d[name] = hash
    return d


def load_trusted_proxies():
    ips = [s.strip() for s in config.proxy_auth_trusted.replace(";", ",").split(",")]
    return iptools.IpRangeList(*ips)


CREDENTIALS = load_credentials()
TRUSTED_PROXIES = load_trusted_proxies()


if __name__ == "__main__":
    asgineer.run(main_handler, "uvicorn", config.bind, log_level="warning")
