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
#   values in client/stores.py.

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
    You should catch this error and respond with 401 unauthorized.
    """

    def __init__(self, msg):
        super().__init__(msg)


# %% Main handler

# todo: rate limiting


async def api_handler_triage(request, path, auth_info, db):
    """The API handler that triages over the API options."""

    if path == "updates":
        if request.method == "GET":
            return await get_updates(request, auth_info, db)
        else:
            expl = "/updates can only be used with GET"
            return 405, {}, "method not allowed: " + expl

    elif path == "records":
        if request.method == "GET":
            return await get_records(request, auth_info, db)
        elif request.method == "PUT":
            return await put_records(request, auth_info, db)
        else:
            expl = "/records can only be used with GET and PUT"
            return 405, {}, "method not allowed: " + expl

    elif path == "settings":
        if request.method == "GET":
            return await get_settings(request, auth_info, db)
        elif request.method == "PUT":
            return await put_settings(request, auth_info, db)
        else:
            expl = "/settings can only be used with GET and PUT"
            return 405, {}, "method not allowed: " + expl

    elif path == "forcereset":
        if request.method == "PUT":
            return await put_forcereset(request, auth_info, db)
        else:
            expl = "/forcereset can only be used with PUT"
            return 405, {}, "method not allowed: " + expl

    elif path == "webtoken":
        if request.method in ("GET"):
            return await get_webtoken(request, auth_info, db)
        else:
            expl = "/webtoken can only be used with GET"
            return 405, {}, "method not allowed: " + expl

    elif path == "apitoken":
        if request.method in ("GET"):
            return await get_apitoken(request, auth_info, db)
        else:
            expl = "/apitoken can only be used with GET"
            return 405, {}, "method not allowed: " + expl

    else:
        expl = f"/{path} is not a valid API path"
        return 404, {}, "not found: " + expl


# %% Auth


WEBTOKEN_DAYS = 2 * 7
WEBTOKEN_LIFETIME = WEBTOKEN_DAYS * 24 * 60 * 60
API_TOKEN_EXP = 32503748400  # the year 3000


async def authenticate(request):
    """Authenticate the user, returning (auth_info, db) if all is well.
    Raises AuthException if an authtoken is missing, not issued by us,
    does not match the seed (i.e. has been revoked), or has expired.
    """

    # Notes:
    # * We raise an exception on auth fail, so that if the calling code
    #   would forget to handle the non-authenticated case, the request
    #   would still fail (albeit with a 500).
    # * The validation is done in order of importance. The seed is checked
    #   before the expiration. Clients can scan the 401 message for the word
    #   "revoked" and handle revokation different from expiration.

    st = time.time()

    # Get jwt from header. Validates that a token is provided.
    token = request.headers.get("authtoken", "")
    if not token:
        raise AuthException("Missing jwt 'authtoken' in header.")

    # Decode the jwt to get auth_info. Validates that we created it.
    try:
        auth_info = decode_jwt(token)
    except Exception as err:
        raise AuthException(str(err))

    # Open the database, this creates it if it does not yet exist
    dbname = user2filename(auth_info["username"])
    db = await itemdb.AsyncItemDB(dbname)
    await db.ensure_table("userinfo", *INDICES["userinfo"])
    await db.ensure_table("records", *INDICES["records"])
    await db.ensure_table("settings", *INDICES["settings"])

    # Get reference seed from db
    expires = auth_info["expires"]
    tokenkind = "apitoken" if expires > st + WEBTOKEN_LIFETIME else "webtoken"
    ref_seed = await _get_token_seed_from_db(db, tokenkind, False)

    # Compare seeds. Validates that the token is not revoked.
    if not ref_seed or ref_seed != auth_info["seed"]:
        raise AuthException(f"The {tokenkind} is revoked (seed does not match)")

    # Check expiration last. Validates that the token is not too old.
    # If a token is both revoked and expired, we want to emit the revoked-message.
    if auth_info["expires"] < st:
        raise AuthException(f"The {tokenkind} has expired (after {WEBTOKEN_DAYS} days)")

    # All is well!
    return auth_info, db


async def get_webtoken(request, auth_info, db):
    # Get reset option
    reset = request.querydict.get("reset", "")
    reset = reset.lower() not in ("", "false", "no", "0")
    # Auth
    if auth_info["expires"] > time.time() + WEBTOKEN_LIFETIME:
        return 403, {}, "forbidden: /webtoken needs auth with a web-token"

    return await _get_any_token(auth_info, db, "webtoken", reset)


async def get_apitoken(request, auth_info, db):
    # Get reset option
    reset = request.querydict.get("reset", "")
    reset = reset.lower() not in ("", "false", "no", "0")
    # Auth
    if auth_info["expires"] > time.time() + WEBTOKEN_LIFETIME:
        return 403, {}, "forbidden: /apitoken needs auth with a web-token"

    return await _get_any_token(auth_info, db, "apitoken", reset)


async def _get_any_token(auth_info, db, tokenkind, reset):
    assert tokenkind in ("webtoken", "apitoken")
    # Get expiration time
    if tokenkind == "apitoken":
        expires = API_TOKEN_EXP
    else:
        expires = int(time.time()) + WEBTOKEN_LIFETIME
    # Create token
    seed = await _get_token_seed_from_db(db, tokenkind, reset)
    payload = dict(
        username=auth_info["username"],
        expires=expires,
        seed=seed,
    )
    token = create_jwt(payload)

    result = dict(token=token)
    return 200, {}, result


async def _get_token_seed_from_db(db, tokenkind, reset):
    # Get seed
    query = f"key = '{tokenkind}_seed'"
    ob = await db.select_one("userinfo", query) or {}
    seed = ob.get("value", "")
    # Create new seed if needed
    if reset or not seed:
        seed = secrets.token_urlsafe(8)  # new random seed
        st = time.time()
        async with db:
            await db.put_one(
                "userinfo", key=f"{tokenkind}_seed", st=st, mt=st, value=seed
            )
    return seed


async def get_webtoken_unsafe(username, reset=False):
    """This function provides a webtoken that can be used to
    authenticate future requests. It is intended to bootstrap the
    authentication; the caller of this function is responsible for the
    request being authenticated in another way, for example:

    * Checking that the request is from localhost (for local use only).
    * Obtaining and validating a JWT from a trusted auth provider (e.g. Auth0).
    * Going through an OAuth workflow with a trusted provider (e.g Google or Github).
    * Implement an authenticate-via-email workflow.
    * Implement username/password authentication.

    The provided webtoken expires in two weeks. It is recommended to
    use GET /api/v2/webtoken to get a fresh token once a day.
    """
    # Open db
    dbname = user2filename(username)
    db = await itemdb.AsyncItemDB(dbname)
    await db.ensure_table("userinfo", *INDICES["userinfo"])
    # Produce payload
    seed = await _get_token_seed_from_db(db, "webtoken", reset)
    payload = dict(
        username=username,
        expires=int(time.time()) + WEBTOKEN_LIFETIME,
        seed=seed,
    )
    # Return token
    token = create_jwt(payload)
    return token


# %% The implementation


async def get_updates(request, auth_info, db):

    # Parse since
    since_str = request.querydict.get("since", "").strip()
    if not since_str:
        return 400, {}, "bad request: /updates needs since"
    try:
        since = float(since_str)
    except ValueError:
        return 400, {}, "bad request: /updates since needs a number (timestamp)"

    # # Parse pollmethod option
    # pollmethod = request.querydict.get("pollmethod", "").strip() or "short"
    # if pollmethod not in ("short", "long"):
    #     return 400, {}, "/records pollmethod must be 'short' or 'long'"

    server_time = time.time()

    # Early exit - this is what will happen most of the time. Use a margin to
    # account for limited resolution of getmtime.
    if db.mtime + 0.2 < since:
        return dict(
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
        return 400, {}, "bad request: /records needs timerange (2 timestamps)"
    timerange = timerange_str.split("-")
    try:
        timerange = [float(x) for x in timerange]
        if len(timerange) != 2:
            raise ValueError()
    except ValueError:
        return 400, {}, "bad request: /records timerange needs 2 numbers (timestamps)"

    # Collect records
    tr1, tr2 = int(timerange[0]), int(timerange[1])
    query = f"(t2 >= {tr1} AND t1 <= {tr2}) OR (t1 == t2 AND t1 <= {tr2})"
    records = await db.select("records", query)

    # Return result
    result = dict(records=records)
    return 200, {}, result


async def put_records(request, auth_info, db):
    return await _push_items(request, auth_info, db, "records")


async def get_settings(request, auth_info, db):

    # Collect settings
    settings = await db.select_all("settings")

    # Return result
    result = dict(settings=settings)
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
    failed = []  # keys of corrupt items
    errors = []  # error messages, matching up with failed
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
                failed.append(item["key"])
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
        accepted=accepted,
        failed=failed,
        errors=errors + errors2,
    )
    return 200, {}, result


async def put_forcereset(request, auth_info, db):
    st = time.time()

    async with db:
        await db.put_one("userinfo", key="reset_time", st=st, mt=st, value=st)

    result = dict(status="ok")
    return 200, {}, result
