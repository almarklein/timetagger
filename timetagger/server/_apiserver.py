"""
This implements the API side of the server.
"""

import os
import json
import time
import logging

from itemdb import ItemDB

from ._utils import asyncthis, user2filename


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


async def api_handler(request, apipath, user):
    """The main API request handler."""

    # Take care that our PUT (and DELETE) are idempotent (multiple
    # identical requests should have the same effect as a single request)
    #
    # Upon an error, we just respond with an appropriate status code, and a
    # message in text/plain; we don't try to wrap the error in a dict.

    if not apipath:
        # Respond with "index" if this is the API root
        baseurl = f"{request.scheme}://{request.host}:{request.port}/api/v1/"
        return {
            "version": 1,
            "GET updates since the given time": baseurl + "updates?since=xx",
            # "GET records.": baseurl + "records",
            "GET settings": baseurl + "settings",
            "PUT (add/update) records": baseurl + "records",
            "PUT (push/update) user settings": baseurl + "settings",
        }

    elif apipath == "updates":
        if request.method == "GET":
            return await get_updates_handler(request, user)
        else:
            return 405, {}, "/api/v1/updates can only be used with GET"

    elif apipath == "records":
        if request.method == "PUT":
            return await put_items_handler(request, user, "records")
        else:
            return 405, {}, "/api/v1/records can only be used with PUT"

    elif apipath == "settings":
        if request.method == "PUT":
            return await put_items_handler(request, user, "settings")
        elif request.method == "GET":
            return await get_items_handler(request, user, "settings")
        else:
            return 405, {}, "/api/v1/settings can only be used with PUT or GET"

    elif apipath == "forcereset":
        if request.method == "PUT":
            return await force_reset_handler(request, user)
        else:
            return 405, {}, "/api/v1/forcereset can only be used with PUT"

    else:
        return 404, {}, "invalid API call"


def get_user_db(user):
    """Open the user db and return the db and its mtime (which is -1 if the db did not yet exist)."""
    # Get database name and its mtime
    dbname = user2filename(user)
    if os.path.isfile(dbname):
        mtime = os.path.getmtime(dbname)
    else:
        mtime = -1
    # Open the database, this creates it if it does not yet exist
    db = ItemDB(dbname)
    return db, mtime


async def force_reset_handler(request, user):
    """Set the reset_time to force a reset for each first next update."""
    return await asyncthis(_force_reset, user)


def _force_reset(user):

    db, mtime = get_user_db(user)
    st = time.time()
    db.ensure_table("userinfo", *INDICES["userinfo"])

    with db:
        db.put_one("userinfo", key="reset_time", st=st, mt=st, value=st)

    return 200, {}, {"status": "ok"}


async def get_updates_handler(request, user):
    """Coroutine to handle a GET updates request."""
    # todo: it may be possible to keep track of db access in-process
    # so that we can make this handler very fast when nothing has changed, but
    # this fails (or becomes complex) when multiple processes are involved
    # (e.g. live vs staging).
    try:
        since = float(request.querydict.get("since", ""))
    except ValueError:
        return 400, {}, "/api/v1/updates needs float ?since argument"

    return await asyncthis(_get_updates, user, since)


def _get_updates(user, since):

    db, mtime = get_user_db(user)
    server_time = time.time()
    for what in ("records", "settings", "userinfo"):
        db.ensure_table(what, *INDICES[what])

    # Early exit - this is what will happen most of the time. Use a margin to
    # account for limited resolution of getmtime.
    if mtime + 0.2 < since:
        return dict(
            server_time=server_time,
            reset=0,  # Not False; is used in the tests to know that we exited early
            records=[],
            settings=[],
        )

    # Get reset time from userinfo. We set userinfo.reset_time when the
    # database is reset (or when we want to force a refresh). We make
    # the client reset if since < reset_time.
    ob = db.select_one("userinfo", "key == 'reset_time'")
    reset_time = float((ob or {}).get("value", -1))
    reset = since <= reset_time

    if reset:
        records = db.select_all("records")
        settings = db.select_all("settings")
    else:
        query = f"st >= {float(since)}"
        records = db.select("records", query)
        settings = db.select("settings", query)

    return dict(
        status="ok",
        server_time=server_time,
        reset=reset,
        records=records,
        settings=settings,
    )


async def get_items_handler(request, user, what):
    """Coroutine to handle a GET settings request."""
    return await asyncthis(_get_items, user, what)


def _get_items(user, what):

    db, mtime = get_user_db(user)
    server_time = time.time()

    if mtime <= 0:
        return 200, {}, {"server_time": server_time, what: []}

    db.ensure_table(what, *INDICES[what])
    items = db.select_all(what)
    return 200, {}, {"status": "ok", "server_time": server_time, what: items}


async def put_items_handler(request, user, what):
    """Coroutine to handle a PUT records/settings request."""
    # Download items
    items = await request.get_json(10 * 2 ** 20)  # 10 MiB limit
    if not isinstance(items, list):
        raise TypeError(f"List of {what}'s' must be a list")

    # Apply
    return await asyncthis(_push_items, user, what, items)


def _push_items(user, what, items):

    db, mtime = get_user_db(user)
    server_time = time.time()
    db.ensure_table(what, *INDICES[what])
    db.ensure_table("userinfo", *INDICES["userinfo"])

    req = REQS[what]
    spec = SPECS[what]

    accepted = []  # keys of accepted items (but might have mt < current)
    fail = []  # keys of corrupt items
    errors = []  # error messages, matching up with fail
    errors2 = []  # error messages for items that did not even have a key

    with db:
        ob = db.select_one("userinfo", "key == 'reset_time'")
        reset_time = float((ob or {}).get("value", -1))

        for item in items:

            # First check minimal requirement.
            if not (isinstance(item, dict) and isinstance(item.get("key", None), str)):
                errors2.append("Got item that is not a dict with str 'key' field.")
                continue

            # Get current item (or None). We will ALWAYS update the item's st
            # (except when cur_item is None and incoming is corrupt).
            # This helps guarantee consistency between server and client.
            cur_item = db.select_one(what, "key == ?", item["key"])

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
            db.put(what, item)

    # Done
    body = {
        "status": ("fail" if fail else "ok"),
        "accepted": accepted,
        "fail": fail,
        "errors": errors + errors2,
    }
    return 200, {}, body
