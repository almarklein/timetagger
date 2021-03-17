"""
This implements the API side of the server.
"""

import json
import time
import logging
import secrets

import itemdb

from ._utils import user2filename, create_jwt, decode_jwt


logger = logging.getLogger("asgineer")


# At the server:
#
# * We specify the fields that an item has (that the server accepts).
# * We specify a subset of those that are required. This allows more flexibility
#   in clients, and helps when we add fields at the server, but have old clients.
# * We specify how the incoming values are converted/checked.
# * Other incoming fields are simply ignored.
# * There is a special field st (server time) that the server adds to each item.
# * We have tests to ensure that the lines below line up with the same
#   values client/stores.py.

to_int = int
to_float = float


def to_str(s):
    s = str(s)
    if len(s) >= STR_MAX:
        raise ValueError("String values must be less than 256 chars.")
    return s


def to_jsonable(x):
    s = json.dumps(x)
    if len(s) >= STR_MAX:
        raise ValueError("Values must be less than 256 chars when jsonized.")
    return x


# ----- COMMON PART (don't change this comment)

RECORD_SPEC = dict(key=to_str, mt=to_int, t1=to_int, t2=to_int, ds=to_str)
RECORD_REQ = ["key", "mt", "t1", "t2"]

SETTING_SPEC = dict(key=to_str, mt=to_int, value=to_jsonable)
SETTING_REQ = ["key", "mt", "value"]

STR_MAX = 256

# ----- END COMMON PART (don't change this comment)

SPECS = {"records": RECORD_SPEC, "settings": SETTING_SPEC}
REQS = {
    "records": frozenset(RECORD_REQ),
    "settings": frozenset(SETTING_REQ),
}

# Database indices
INDICES = {
    "records": ("!key", "st", "t1", "t2"),
    "settings": ("!key", "st"),
    "userinfo": ("!key", "st"),
}


class AuthException(Exception):
    """Exception raised when authentication fails.
    You should catch this error and respond with 403.
    """

    pass


# %% Main handler

# todo: rate limiting


async def api_handler_triage(request, path, auth_info, db):
    """The API handler that triages over the API options.

    On authenication: the 3d argument is the JWT payload obtained with
    `authenticate()` (auth step 1). The current function will check the
    seed of the payload against the seed in the user db (auth step 2).
    An AuthException is raised if this check fails.
    """

    if path == "updates":
        if request.method == "GET":
            return await get_updates(request, auth_info, db)
        else:
            return 405, {}, "api/v2/updates can only be used with GET and PUT"

    elif path == "records":
        if request.method == "GET":
            return await get_records(request, auth_info, db)
        elif request.method == "PUT":
            return await put_records(request, auth_info, db)
        else:
            return 405, {}, "api/v2/records can only be used with GET and PUT"

    elif path == "settings":
        if request.method == "GET":
            return await get_settings(request, auth_info, db)
        elif request.method == "PUT":
            return await put_settings(request, auth_info, db)
        else:
            return 405, {}, "api/v2/records can only be used with GET and PUT"

    elif path == "forcereset":
        if request.method == "PUT":
            return await put_forcereset(request, auth_info, db)
        else:
            return 405, {}, "/api/v2/forcereset can only be used with PUT"

    elif path == "webtoken":
        if request.method in ("GET"):
            return await get_webtoken(request, auth_info, db)
        else:
            return 405, {}, "/api/v2/webtoken can only be used with GET"

    elif path == "apitoken":
        if request.method in ("GET"):
            return await get_apitoken(request, auth_info, db)
        else:
            return 405, {}, "/api/v2/apitoken can only be used with GET"

    else:
        return 404, {}, f"/api/v2/{path} is not a valid API path"


async def authenticate(request):
    """Open the user db and return the auth_info and database.
    This will also validate the token seed, and raise AuthException when
    it does not match.
    """

    # First path of auth
    auth_info = await _validate_token_and_get_info(request)

    # Open the database, this creates it if it does not yet exist
    dbname = user2filename(auth_info["email"])
    db = await itemdb.AsyncItemDB(dbname)

    # Ensure tables
    await db.ensure_table("userinfo", *INDICES["userinfo"])
    await db.ensure_table("records", *INDICES["records"])
    await db.ensure_table("settings", *INDICES["settings"])

    # Second part of auth
    await _validate_token_seed(db, auth_info)

    return auth_info, db


# %% Auth


WEBTOKEN_DAYS = 2 * 7
WEBTOKEN_LIFETIME = WEBTOKEN_DAYS * 24 * 60 * 60
API_TOKEN_EXP = 32503748400  # the year 3000


async def _validate_token_and_get_info(request):
    """Authenticate the request by validating the token in the HTTP header.
    Raises an AuthException if the authentication fails.

    Returns the JWT payload. This validate the expiration and that this is
    a token that we issues. It does not verify the token seed yet, this
    must happen when the database is opened.
    """
    token = request.headers.get("authtoken", "")
    if not token:
        raise AuthException("Missing jwt 'authtoken' in header.")
    try:
        return decode_jwt(token)
    except Exception as err:
        text = str(err)
        if "expired" in text:
            text = f"The token has expired (after {WEBTOKEN_DAYS} days)"
        raise AuthException(text)


async def _validate_token_seed(db, auth_info):
    """Raises an AuthException if the seed in the auth_info does not match with
    the seed in the db.
    """
    # Get tokenkind
    if auth_info["exp"] > time.time() + WEBTOKEN_LIFETIME:
        tokenkind = "apitoken"
    else:
        tokenkind = "webtoken"

    # Get seed value from db
    query = f"key = '{tokenkind}_seed'"
    ob = await db.select_one("userinfo", query) or {}
    seed = ob.get("value", "")

    # Compare
    if not seed:
        raise AuthException(f"No {tokenkind} seed in db")
    if seed != auth_info["seed"]:
        raise AuthException(f"The {tokenkind} seed does not match")


async def get_webtoken(request, auth_info, db):

    # Get reset option
    reset = request.querydict.get("reset", "")
    reset = reset.lower() not in ("", "false", "no", "0")

    # Auth
    if auth_info["exp"] > time.time() + WEBTOKEN_LIFETIME:
        return 403, {}, "Not allowed with a non-expiring token"

    return await _get_any_token(auth_info, db, "webtoken", reset)


async def get_apitoken(request, auth_info, db):

    # Get reset option
    reset = request.querydict.get("reset", "")
    reset = reset.lower() not in ("", "false", "no", "0")

    # Auth
    if auth_info["exp"] > time.time() + WEBTOKEN_LIFETIME:
        return 403, {}, "Not allowed with a non-expiring token"

    return await _get_any_token(auth_info, db, "apitoken", reset)


async def _get_any_token(auth_info, db, tokenkind, reset):

    assert tokenkind in ("webtoken", "apitoken")

    # Get expiration time
    exp = int(time.time()) + WEBTOKEN_LIFETIME
    if tokenkind == "apitoken":
        exp = API_TOKEN_EXP

    # Create token
    payload = dict(
        email=auth_info["email"],
        exp=exp,
        seed=await _get_token_seed_from_db(db, tokenkind, reset),
    )
    token = create_jwt(payload)

    result = dict(status="ok", token=token)
    return 200, {}, result


async def _get_token_seed_from_db(db, tokenkind, reset):
    st = time.time()
    query = f"key = '{tokenkind}_seed'"
    ob = await db.select_one("userinfo", query) or {}
    seed = ob.get("value", "")
    if reset or not seed:
        seed = secrets.token_urlsafe(8)
        async with db:
            await db.put_one(
                "userinfo", key=f"{tokenkind}_seed", st=st, mt=st, value=seed
            )
    return seed


async def get_webtoken_unsafe(auth_info, reset=False):
    """This function provides a webtoken that can be used to
    authenticate future requests.

    The caller of this function is responsible for the request being secure, e.g. by:
    * Checking that we're serving on localhost.
    * Validating a JWT from another trusted source.
    * Going through an OAuth workflow with a trusted auth provider.

    The provided webtoken expires in two weeks. It is recommended to
    use GET /api/v2/webtoken to get a fresh token once a day.
    """
    # Open db
    dbname = user2filename(auth_info["email"])
    db = await itemdb.AsyncItemDB(dbname)
    await db.ensure_table("userinfo", *INDICES["userinfo"])
    # Produce payload
    payload = dict(
        email=auth_info["email"],
        exp=int(time.time()) + WEBTOKEN_LIFETIME,
        seed=await _get_token_seed_from_db(db, "webtoken", reset),
    )
    # Return token
    token = create_jwt(payload)
    return token


# %% The implementation


async def get_updates(request, auth_info, db):

    # Parse since
    since_str = request.querydict.get("since", "").strip()
    if not since_str:
        return 400, {}, "/api/v2/updates needs since"
    try:
        since = float(since_str)
    except ValueError:
        return 400, {}, "/api/v2/updates since needs a number (timestamp)"

    # # Parse pollmethod option
    # pollmethod = request.querydict.get("pollmethod", "").strip() or "short"
    # if pollmethod not in ("short", "long"):
    #     return 400, {}, "/api/v2/records pollmethod must be 'short' or 'long'"

    server_time = time.time()

    # Early exit - this is what will happen most of the time. Use a margin to
    # account for limited resolution of getmtime.
    if db.mtime + 0.2 < since:
        return dict(
            status="ok",
            server_time=server_time,
            reset=0,  # Not False; is used in the tests to know that we exited early
            records=[],
            settings=[],
        )

    # Get reset time from userinfo. We set userinfo.reset_time when the
    # database is reset (or when we want to force a refresh). We make
    # the client reset if since < reset_time.
    ob = await db.select_one("userinfo", "key == 'reset_time'")
    reset_time = float((ob or {}).get("value", -1))
    reset = since <= reset_time

    # Get data
    if reset:
        records = await db.select_all("records")
        settings = await db.select_all("settings")
    else:
        query = f"st >= {float(since)}"
        records = await db.select("records", query)
        settings = await db.select("settings", query)

    # Return result
    result = dict(
        status="ok",
        server_time=server_time,
        reset=reset,
        records=records,
        settings=settings,
    )
    return 200, {}, result


async def get_records(request, auth_info, db):

    # Parse timerange option
    timerange_str = request.querydict.get("timerange", "").strip()
    if not timerange_str:
        return 400, {}, "/api/v2/records needs timerange (2 timestamps)"
    timerange = timerange_str.split("-")
    try:
        timerange = [float(x) for x in timerange]
        if len(timerange) != 2:
            raise ValueError()
    except ValueError:
        return 400, {}, "/api/v2/records timerange needs 2 numbers (timestamps)"

    # Collect records
    query = f"t2 >= {timerange[0]} AND t1 <= {timerange[1]}"
    records = await db.select("records", query)

    # Return result
    result = dict(
        status="ok",
        records=records,
    )
    return 200, {}, result


async def put_records(request, auth_info, db):
    return await _push_items(request, auth_info, db, "records")


async def get_settings(request, auth_info, db):

    # Collect settings
    settings = await db.select_all("settings")

    # Return result
    result = dict(
        status="ok",
        settings=settings,
    )
    return 200, {}, result


async def put_settings(request, auth_info, db):
    return await _push_items(request, auth_info, db, "settings")


async def _push_items(request, auth_info, db, what):

    # Download items
    items = await request.get_json(10 * 2 ** 20)  # 10 MiB limit
    if not isinstance(items, list):
        raise TypeError(f"List of {what} must be a list")

    server_time = time.time()

    req = REQS[what]
    spec = SPECS[what]

    accepted = []  # keys of accepted items (but might have mt < current)
    fail = []  # keys of corrupt items
    errors = []  # error messages, matching up with fail
    errors2 = []  # error messages for items that did not even have a key

    async with db:
        ob = await db.select_one("userinfo", "key == 'reset_time'")
        reset_time = float((ob or {}).get("value", -1))

        for item in items:
            # First check minimal requirement.
            if not (isinstance(item, dict) and isinstance(item.get("key", None), str)):
                errors2.append("Got item that is not a dict with str 'key' field.")
                continue

            # Get current item (or None). We will ALWAYS update the item's st
            # (except when cur_item is None and incoming is corrupt).
            # This helps guarantee consistency between server and client.
            cur_item = await db.select_one(what, "key == ?", item["key"])

            # Validate and copy the item (only copy fields that we know)
            try:
                item = {
                    key: func(item[key]) for key, func in spec.items() if key in item
                }
                if req.difference(item.keys()):
                    raise ValueError(
                        f"A {what} is missing required fields: {req.difference(item.keys())}"
                    )
                if item["mt"] < reset_time:
                    raise ValueError("Item was modified after a reset")
            except Exception as err:
                # Item is corrupt - mark it as failed
                fail.append(item["key"])
                errors.append(str(err))
                # Re-put the current item if there was one, otherwise ignore
                if cur_item is not None:
                    item = cur_item
                else:
                    continue
            else:
                accepted.append(item["key"])

            # Reput the current item if its mt is larger than the incoming item.
            if cur_item is not None and cur_item["mt"] > item["mt"]:
                item = cur_item

            # Ensure that st is never equal, so that we can guarantee
            # eventual consistency. It also means that the exact value
            # of mt is less important and we can allow it to be int.
            if cur_item is not None:
                item["st"] = max(server_time, cur_item["st"] + 0.0001)
            else:
                item["st"] = server_time

            # Store it!
            await db.put(what, item)

    # Return result
    result = dict(
        status=("fail" if fail else "ok"),
        accepted=accepted,
        fail=fail,
        errors=errors + errors2,
    )
    return 200, {}, result


async def put_forcereset(request, auth_info, db):
    st = time.time()

    async with db:
        await db.put_one("userinfo", key="reset_time", st=st, mt=st, value=st)

    result = dict(status="ok")
    return 200, {}, result
