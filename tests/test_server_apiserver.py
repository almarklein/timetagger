import os
import json
import time
import asyncio

from asgineer.testutils import MockTestServer

from _common import run_tests
from timetagger.server._utils import decode_jwt_nocheck
from timetagger.server import _apiserver
from timetagger.server import (
    authenticate,
    AuthException,
    api_handler_triage,
    get_webtoken_unsafe,
    user2filename,
)

import itemdb


USER = "test"
HEADERS = {}


def get_webtoken_unsafe_sync(username, reset=False):
    co = get_webtoken_unsafe(username, reset)
    return asyncio.get_event_loop().run_until_complete(co)


def clear_test_db():
    filename = user2filename(USER)
    if os.path.isfile(filename):
        os.remove(filename)

    HEADERS["authtoken"] = get_webtoken_unsafe_sync(USER)


def get_from_db(what):
    filename = user2filename(USER)
    return itemdb.ItemDB(filename).select_all(what)


async def our_api_handler(request):
    """The API handler used during testing. It's similar to the default API handler."""
    prefix = "/api/v2/"
    path = request.path[len(prefix) :]
    if not request.path.startswith(prefix):
        return 404, {}, "Invalid API path"
    elif not path and request.method == "GET":
        return 200, {}, "API root"

    try:
        auth_info, db = await authenticate(request)
    except AuthException as err:
        return 401, {}, f"Auth failed: {err}"

    return await api_handler_triage(request, path, auth_info, db)


def dejsonize(r):
    return json.loads(r.body.decode())


def test_auth():
    clear_test_db()
    time.sleep(1.1)  # Expire is in integer seconds -> ensure exp is different

    headers = HEADERS.copy()

    # There is not auth - this is something to be implemented yourself
    with MockTestServer(our_api_handler) as p:
        # No auth needed for root
        r = p.get("/api/v2/")
        assert r.status == 200
        # No headers, no access
        r = p.get("/api/v2/updates?since=0")
        assert r.status == 401
        # Access with header
        r = p.get("/api/v2/updates?since=0", headers=headers)
        assert r.status == 200
        # No access if token is not produced by tt
        r = p.get("/api/v2/updates?since=0", headers={"authtoken": "foo"})
        assert r.status == 401

        # Get new auth token, old one should still work
        HEADERS["authtoken"] = get_webtoken_unsafe_sync(USER)
        assert HEADERS["authtoken"] != headers["authtoken"]
        r = p.get("/api/v2/updates?since=0", headers=headers)
        assert r.status == 200
        # Get new auth token, but reset seed, old one should fail
        # This confirms the revoking of tokens
        HEADERS["authtoken"] = get_webtoken_unsafe_sync(USER, reset=True)
        r = p.get("/api/v2/updates?since=0", headers=headers)
        assert r.status == 401
        # And the new token works
        r = p.get("/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200

        # Emulate token expiration
        ori_exp = _apiserver.WEBTOKEN_LIFETIME
        _apiserver.WEBTOKEN_LIFETIME = -10
        headers["authtoken"] = get_webtoken_unsafe_sync(USER)
        r = p.get("/api/v2/updates?since=0", headers=headers)
        assert r.status == 401
        assert "expired " in r.body.decode().lower()
        assert "revoked " not in r.body.decode().lower()
        _apiserver.WEBTOKEN_LIFETIME = ori_exp

        # Now revoke that expired token. Now it's marked as revoked,
        # because revoked is worse than expired, and clients can use that info.
        HEADERS["authtoken"] = get_webtoken_unsafe_sync(USER, True)
        r = p.get("/api/v2/updates?since=0", headers=headers)
        assert r.status == 401
        assert "expired " not in r.body.decode().lower()
        assert "revoked " in r.body.decode().lower()


def test_fails():
    with MockTestServer(our_api_handler) as p:
        # Invalid API version
        r = p.get("http://localhost/api/v99/", headers=HEADERS)
        assert r.status == 404
        r = p.get("http://localhost/api/v1/", headers=HEADERS)
        assert r.status == 404

        # The root should return *something*
        r = p.get("http://localhost/api/v2/", headers=HEADERS)
        assert r.status == 200

        # Invalid API path
        r = p.get("http://localhost/api/v2/records_xxx", headers=HEADERS)
        assert r.status == 404

        # Can only GET updates
        r = p.put("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 405
        r = p.post("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 405
        # Can only PUT  and GET records
        r = p.post("http://localhost/api/v2/records", headers=HEADERS)
        assert r.status == 405
        # Get only GET or PUT settings
        r = p.post("http://localhost/api/v2/settings", headers=HEADERS)
        assert r.status == 405
        # ...
        r = p.post("http://localhost/api/v2/forcereset", headers=HEADERS)
        assert r.status == 405
        # Can only GET token stuff
        r = p.put("http://localhost/api/v2/webtoken", headers=HEADERS)
        assert r.status == 405
        r = p.post("http://localhost/api/v2/apitoken", headers=HEADERS)
        assert r.status == 405


def test_settings():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Initially the settings list is empty
        r = p.get("http://localhost/api/v2/settings", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"settings"}
        x = d["settings"]
        assert isinstance(x, list) and len(x) == 0

        # Put some settings in
        settings = [
            dict(key="pref1", mt=110, value="xx"),
            dict(key="pref2", mt=110, value="xx"),
        ]
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"accepted", "failed", "errors"}

        # Now there are two
        r = p.get("http://localhost/api/v2/settings", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        settings = {x["key"]: x["value"] for x in d["settings"]}
        assert len(settings) == 2
        assert settings["pref1"] == "xx"
        assert settings["pref1"] == "xx"

        # Update and add
        settings = [
            dict(key="pref1", mt=100, value=42),
            dict(key="pref2", mt=120, value=42),
            dict(key="pref3", mt=120, value=42),
        ]
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert len(dejsonize(r)["accepted"]) == 3

        # Now there are three
        r = p.get("http://localhost/api/v2/settings", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        settings = {x["key"]: x["value"] for x in d["settings"]}
        assert len(settings) == 3
        assert settings["pref1"] == "xx"
        assert settings["pref2"] == 42
        assert settings["pref3"] == 42

        # -- fails

        # Try adding setting with missing fields
        settings = [dict(key="pref4", mt=100, value=42), dict(key="pref5", mt=100)]
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["pref4"]
        assert "missing" in dejsonize(r)["errors"][0]

        # Try adding setting with wrong field type
        settings = [dict(key="pref6", mt="xx", value=42)]
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []
        assert "invalid literal" in dejsonize(r)["errors"][0]

        # Try adding data over 10 MiB
        settings = [dict(key="pref8", mt=100, value=42)] * 600000
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 500
        assert "too large" in r.body.decode().lower()

        # Try adding settings with too long fields
        settings = [
            dict(key="p" * 256, mt=100, value=42),
            dict(key="pref10", mt=100, value="x" * 8192),
        ]
        r = p.put(
            "http://localhost/api/v2/settings",
            json.dumps(settings).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []
        assert "less than 256" in dejsonize(r)["errors"][0]
        assert "less than 256" in dejsonize(r)["errors"][1]

        # Check status. This checks that all the above requests
        # failed without adding settings in the same request
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["settings"]) == 4


def test_records():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Currently no records
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        records = dejsonize(r)["records"]
        assert records == []

        # Add records
        records = [
            dict(key="r11", mt=110, t1=100, t2=150, ds="#p1"),
            dict(key="r12", mt=110, t1=310, t2=350, ds="#p1"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"accepted", "failed", "errors"}
        assert dejsonize(r)["accepted"] == ["r11", "r12"]
        assert dejsonize(r)["errors"] == []

        # Check status
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 2

        # Now add more records
        records = [
            dict(key="r13", mt=120, t1=100, t2=150, ds="#p2"),
            dict(key="r14", mt=120, t1=310, t2=350, ds="#p2"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert "accepted" in r.body.decode().lower()

        # Check status
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 4

        # Try adding record with OK missing fields
        records = [dict(key="r22", mt=120, t1=100, t2=150)]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r22"]

        # -- fails

        # Try adding with a dict
        r = p.put(
            "http://localhost/api/v2/records", json.dumps({}).encode(), headers=HEADERS
        )
        assert r.status == 500
        assert "TypeError" in r.body.decode()

        # Actually, not really a fail, but you can send an empty list ...
        r = p.put(
            "http://localhost/api/v2/records", json.dumps([]).encode(), headers=HEADERS
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []

        # Try adding record with BAD missing fields
        records = [
            dict(key="r21", mt=120, t1=310, t2=350, ds="xx"),
            dict(key="r22", mt=120, t1=100, ds="xx"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r21"]
        assert dejsonize(r)["failed"] == ["r22"]
        assert "missing" in dejsonize(r)["errors"][0]

        # Try adding record with wrong field type
        records = [
            dict(key="r23", mt="xx", t1=310, t2=350, ds="xx"),
            dict(key="r24", mt=120, t1="xx", t2=150, ds="xx"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["failed"] == ["r23", "r24"]
        assert "invalid literal" in dejsonize(r)["errors"][0]
        assert "invalid literal" in dejsonize(r)["errors"][1]

        # Try adding records over 10 MiB
        records = [dict(key="r25", mt=120, t1=310, t2=350, ds="xx")] * 200000
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 500
        assert "too large" in r.body.decode().lower()

        # Try adding records with too long fields
        records = [
            dict(key="r26", mt=120, t1=310, t2=350, ds="x" * 1000),
            dict(key="r27", mt=120, t1=310, t2=350, ds="x" * 257),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["failed"] == ["r26", "r27"]
        assert "less than 256" in dejsonize(r)["errors"][0]
        assert "less than 256" in dejsonize(r)["errors"][1]

        # Try adding records that are not even dicts or missing a key
        records = [
            dict(key="r28", mt=120, t1="xx", t2=350, ds="x"),
            ["r17"],
            dict(mt=120, t1=310, t2=350, ds="x"),  # no key
            dict(key="r29", mt=120, t1="xx", t2=350, ds="x"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["failed"] == ["r28", "r29"]
        assert "invalid literal" in dejsonize(r)["errors"][0]
        assert "invalid literal" in dejsonize(r)["errors"][1]
        assert "not a dict with str" in dejsonize(r)["errors"][2]
        assert "not a dict with str" in dejsonize(r)["errors"][3]

        # Check status. This checks that all the above requets
        # failed without adding records in the same request
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 6


def test_records_get():
    # This endpoint was added later

    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Get current records
        r = p.get("http://localhost/api/v2/records?timerange=0-999", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"records"}
        assert d["records"] == []

        # Add records
        records = [
            dict(key="r11", mt=110, t1=100, t2=150, ds="#p1"),
            dict(key="r12", mt=110, t1=310, t2=350, ds="#p1"),
            dict(key="r13", mt=110, t1=700, t2=701, ds="#p1"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200

        # Get current records
        r = p.get("http://localhost/api/v2/records?timerange=0-999", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"records"}
        assert set(r["key"] for r in d["records"]) == {"r11", "r12", "r13"}

        # Get section containing only first
        for tr in ["0-200", "0-101", "99-101", "110-111", "149-151", "149-200"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange={tr}", headers=HEADERS
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(d.keys()) == {"records"}
            assert set(r["key"] for r in d["records"]) == {"r11"}

        # Get section containing only second
        for tr in ["300-500", "300-311", "309-311", "320-321", "349-351", "349-500"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange={tr}", headers=HEADERS
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(d.keys()) == {"records"}
            assert set(r["key"] for r in d["records"]) == {"r12"}

        # Get section containing only third (short record)
        for tr in ["600-800", "699-701"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange={tr}", headers=HEADERS
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(d.keys()) == {"records"}
            assert set(r["key"] for r in d["records"]) == {"r13"}

        # Using a zero range works if that timestamp is inside a record
        r = p.get(f"http://localhost/api/v2/records?timerange=120-120", headers=HEADERS)
        assert r.status == 200
        assert set(r["key"] for r in dejsonize(r)["records"]) == {"r11"}

        # Using a reversed range works if that range is fully inside a record
        r = p.get(f"http://localhost/api/v2/records?timerange=140-110", headers=HEADERS)
        assert r.status == 200
        assert set(r["key"] for r in dejsonize(r)["records"]) == {"r11"}
        # And only fully
        r = p.get(f"http://localhost/api/v2/records?timerange=151-110", headers=HEADERS)
        assert r.status == 200
        assert set(r["key"] for r in dejsonize(r)["records"]) == set()

        # Add some running records
        now = int(time.time())
        records = [
            dict(key="r21", mt=110, t1=now - 2000, t2=now - 2000, ds="#p1"),
            dict(key="r22", mt=110, t1=now - 3000, t2=now - 3000, ds="#p1"),
            dict(key="r23", mt=110, t1=now - 4000, t2=now - 4000, ds="#p1"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200

        # If we sample *somewhere* in a running records range, we'd get it
        for tr in [(-5000, 10), (-2500, 10), (-100, -90), (100, 110), (0, 0)]:
            trs = f"{now + tr[0]}-{now + tr[1]}"
            r = p.get(
                f"http://localhost/api/v2/records?timerange={trs}", headers=HEADERS
            )
            assert r.status == 200
            d = dejsonize(r)
            keys = [r["key"] for r in d["records"]]
            assert set(keys) == {"r21", "r22", "r23"}

        # Query before when the 2nd and 3d have started -> should only get 1st
        trs = f"{now - 3500}-{now - 3500}"
        r = p.get(f"http://localhost/api/v2/records?timerange={trs}", headers=HEADERS)
        d = dejsonize(r)
        keys = [r["key"] for r in d["records"]]
        assert set(keys) == {"r23"}

        # Query before when the 3d has started -> should only get 1st and 2nd
        trs = f"{now - 3500}-{now - 2999}"
        r = p.get(f"http://localhost/api/v2/records?timerange={trs}", headers=HEADERS)
        d = dejsonize(r)
        keys = [r["key"] for r in d["records"]]
        assert set(keys) == {"r22", "r23"}

        # Fails
        r = p.get(f"http://localhost/api/v2/records", headers=HEADERS)
        assert r.status == 400  # no timerange
        r = p.get(f"http://localhost/api/v2/records?timerange=foo-bar", headers=HEADERS)
        assert r.status == 400  # timerange not numeric
        r = p.get(f"http://localhost/api/v2/records?timerange=100", headers=HEADERS)
        assert r.status == 400  # timerange not two nums
        r = p.get(
            f"http://localhost/api/v2/records?timerange=100-200-300", headers=HEADERS
        )
        assert r.status == 400  # timerange not two nums


def test_updates():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Get updates
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"server_time", "reset", "records", "settings"}
        assert isinstance(d, dict)
        assert "server_time" in d
        assert "reset" in d
        assert d["records"] == []
        assert d["settings"] == []

        # Post a record
        records = [dict(key="r1", mt=110, t1=100, t2=110, ds="A record 1!")]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200

        # Post another record
        records = [dict(key="r2", mt=110, t1=200, t2=210, ds="A record 2!")]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200

        # Get updates again
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 2
        assert d["settings"] == []
        st1 = d["server_time"]

        # Post an update plus new records
        records = [
            dict(key="r1", mt=110, t1=100, t2=150, ds="A record 1!"),
            dict(key="r3", mt=110, t1=310, t2=350, ds="A record 3!"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200

        # If we query all updates, we get 3
        r = p.get("http://localhost/api/v2/updates?since=0", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 3
        assert set(x["key"] for x in d["records"]) == {"r1", "r2", "r3"}
        st2 = d["server_time"]

        # If we query updates since st1, we get 2
        r = p.get("http://localhost/api/v2/updates?since=" + str(st1), headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 2
        assert set(x["key"] for x in d["records"]) == {"r1", "r3"}

        # If we query updates since st2, we get 0
        r = p.get("http://localhost/api/v2/updates?since=" + str(st2), headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 0

        # Force reset
        r = p.put("http://localhost/api/v2/forcereset", headers=HEADERS)
        assert r.status == 200

        # If we query updates since st2 again, we NOW get 3
        r = p.get("http://localhost/api/v2/updates?since=" + str(st2), headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert d["reset"] is True
        assert len(d["records"]) == 3
        st3 = d["server_time"]

        # If we query updates since st3, its zero again
        r = p.get("http://localhost/api/v2/updates?since=" + str(st3), headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 0

        # If we query yet a bit later, we can be sure that the update was quick
        r = p.get(
            "http://localhost/api/v2/updates?since=" + str(st3 + 1), headers=HEADERS
        )
        assert r.status == 200
        d = dejsonize(r)
        assert d["reset"] == 0 and d["reset"] is not False  #

        # -- fails

        # Get updates wrong
        r = p.get("http://localhost/api/v2/updates", headers=HEADERS)
        assert r.status == 400
        assert "updates needs" in r.body.decode() and "since" in r.body.decode()
        #
        r = p.get("http://localhost/api/v2/updates?since=foo", headers=HEADERS)
        assert r.status == 400
        assert "since needs a number" in r.body.decode() and "since" in r.body.decode()


def test_webtoken():
    clear_test_db()
    time.sleep(1.1)

    headers = HEADERS.copy()

    with MockTestServer(our_api_handler) as p:
        # Get fresh webtoken
        r = p.get("http://localhost/api/v2/webtoken", headers=headers)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"token"}
        assert isinstance(d["token"], str) and d["token"].count(".") == 2
        assert decode_jwt_nocheck(d["token"])["username"] == USER
        assert decode_jwt_nocheck(d["token"])["expires"] < time.time() + 1209601

        # We can use it to get another
        assert d["token"] != headers["authtoken"]
        headers["authtoken"] = d["token"]

        # See ...
        r = p.get("http://localhost/api/v2/webtoken", headers=headers)
        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d["token"], str) and d["token"].count(".") == 2

        # Old tokens still work
        r = p.get("http://localhost/api/v2/webtoken", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d["token"], str) and d["token"].count(".") == 2

        # We can also reset the seed ...
        r = p.get("http://localhost/api/v2/webtoken?reset=1", headers=headers)
        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d["token"], str) and d["token"].count(".") == 2
        assert decode_jwt_nocheck(d["token"])["username"] == USER
        assert decode_jwt_nocheck(d["token"])["expires"] < time.time() + 1209601

        # Now the old token is invalid (i.e. revoked)
        r = p.get("http://localhost/api/v2/webtoken", headers=HEADERS)
        assert r.status == 401

        # Let's not break the other tests
        HEADERS["authtoken"] = headers["authtoken"]


def test_apitoken():
    clear_test_db()

    headers = HEADERS.copy()

    with MockTestServer(our_api_handler) as p:
        # Get fresh apitoken
        r = p.get("http://localhost/api/v2/apitoken", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"token"}
        assert isinstance(d["token"], str) and d["token"].count(".") == 2
        assert decode_jwt_nocheck(d["token"])["username"] == USER
        assert decode_jwt_nocheck(d["token"])["expires"] > 30000000000

        # We can use it to do stuff ...
        assert d["token"] != headers["authtoken"]
        headers["authtoken"] = d["token"]

        # See ...
        r = p.get("http://localhost/api/v2/updates?since=0", headers=headers)
        assert r.status == 200

        # ... but we cannot use it to get new tokens of any kind
        r = p.get("http://localhost/api/v2/webtoken", headers=headers)
        assert r.status == 403  # 403 is authorization, 401 is authentication
        r = p.get("http://localhost/api/v2/apitoken", headers=headers)
        assert r.status == 403

        # We can also reset the seed (using the webtoken, not apitoken)
        r = p.get("http://localhost/api/v2/apitoken?reset=1", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d["token"], str) and d["token"].count(".") == 2
        assert decode_jwt_nocheck(d["token"])["username"] == USER
        assert decode_jwt_nocheck(d["token"])["expires"] > 30000000000

        # It's different now
        assert d["token"] != headers["authtoken"]

        time.sleep(0.1)

        # Now the old token is invalid
        r = p.get("http://localhost/api/v2/updates?since=0", headers=headers)
        assert r.status == 401

        # And the new token works
        headers["authtoken"] = d["token"]
        r = p.get("http://localhost/api/v2/updates?since=0", headers=headers)
        assert r.status == 200


if __name__ == "__main__":
    run_tests(globals())
