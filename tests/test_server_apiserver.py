import os
import json
import time
import asyncio

from asgineer.testutils import MockTestServer

from _common import run_tests
from timetagger import __version__ as timetagger_version
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
        r = p.get("http://localhost/api/v2/records?timerange=120-120", headers=HEADERS)
        assert r.status == 200
        assert set(r["key"] for r in dejsonize(r)["records"]) == {"r11"}

        # Using a reversed range works if that range is fully inside a record
        r = p.get("http://localhost/api/v2/records?timerange=140-110", headers=HEADERS)
        assert r.status == 200
        assert set(r["key"] for r in dejsonize(r)["records"]) == {"r11"}
        # And only fully
        r = p.get("http://localhost/api/v2/records?timerange=151-110", headers=HEADERS)
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
        r = p.get("http://localhost/api/v2/records", headers=HEADERS)
        assert r.status == 400  # no timerange
        r = p.get("http://localhost/api/v2/records?timerange=foo-bar", headers=HEADERS)
        assert r.status == 400  # timerange not numeric
        r = p.get("http://localhost/api/v2/records?timerange=100", headers=HEADERS)
        assert r.status == 400  # timerange not two nums
        r = p.get(
            "http://localhost/api/v2/records?timerange=100-200-300", headers=HEADERS
        )
        assert r.status == 400  # timerange not two nums


def test_records_get_running_filter():
    """Test the `running` query parameter for filtering records by running state"""

    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        now = int(time.time())

        # Add a mix of running and stopped records
        records = [
            dict(key="r1", mt=110, t1=100, t2=150, ds="#stopped1"),
            dict(key="r2", mt=110, t1=200, t2=250, ds="#stopped2"),
            dict(key="r3", mt=110, t1=300, t2=350, ds="#stopped3"),
            dict(key="r4", mt=110, t1=now - 1000, t2=now - 1000, ds="#running1"),
            dict(key="r5", mt=110, t1=now - 2000, t2=now - 2000, ds="#running2"),
            dict(key="r6", mt=110, t1=now - 3000, t2=now - 3000, ds="#running3"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r1", "r2", "r3", "r4", "r5", "r6"]

        # Test without running parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999", headers=HEADERS
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
        }

        # Test with running=true - should return only running records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test with running=false - should return only stopped records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test alternative truthy values
        for truthy_value in ["yes", "on", "1", "y"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&running={truthy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test alternative falsy values
        for falsy_value in ["no", "off", "0", "n"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&running={falsy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test case insensitivity on truthy values
        for truthy_value in ["TRUE", "True", "YES", "Yes", "ON", "On"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&running={truthy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test case insensitivity on falsy values
        for falsy_value in ["FALSE", "False", "NO", "No", "OFF", "Off"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&running={falsy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test empty running parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
        }

        # Test unknown/invalid value - should interpret as truthy
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=maybe",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test running filter combined with specific timerange
        # Timerange that includes only r1 and r4
        timerange_start = 50
        timerange_end = max(200, now - 950)

        # Without filter - should get records overlapping this range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # r1 (100-150) should be included
        assert "r1" in keys
        # Running records should be included if they started before timerange_end
        assert "r4" in keys or "r5" in keys or "r6" in keys

        # With running=true - should only get running records in range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&running=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should not include stopped record r1
        assert "r1" not in keys
        # Should only include running records
        for key in keys:
            assert key in {"r4", "r5", "r6"}

        # With running=false - should only get stopped records in range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&running=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should not include running records
        for key in keys:
            assert key not in {"r4", "r5", "r6"}
        # r1 should be included if in range
        if "r1" in keys:
            assert keys <= {"r1", "r2", "r3"}


def test_records_get_hidden_filter():
    """Test the `hidden` query parameter for filtering records by hidden state"""

    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Add a mix of hidden and non-hidden records
        records = [
            dict(key="r1", mt=110, t1=100, t2=150, ds="#visible1"),
            dict(key="r2", mt=110, t1=200, t2=250, ds="#visible2"),
            dict(key="r3", mt=110, t1=300, t2=350, ds="#visible3"),
            dict(key="r4", mt=110, t1=400, t2=450, ds="HIDDEN #deleted1"),
            dict(key="r5", mt=110, t1=500, t2=550, ds="HIDDEN #deleted2"),
            dict(key="r6", mt=110, t1=600, t2=650, ds="HIDDEN #deleted3"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r1", "r2", "r3", "r4", "r5", "r6"]

        # Test without hidden parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999", headers=HEADERS
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
        }

        # Test with hidden=true - should return only hidden records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test with hidden=false - should return only non-hidden records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test alternative truthy values
        for truthy_value in ["yes", "on", "1", "y"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&hidden={truthy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test alternative falsy values
        for falsy_value in ["no", "off", "0", "n"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&hidden={falsy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test case insensitivity on truthy values
        for truthy_value in ["TRUE", "True", "YES", "Yes", "ON", "On"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&hidden={truthy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test case insensitivity on falsy values
        for falsy_value in ["FALSE", "False", "NO", "No", "OFF", "Off"]:
            r = p.get(
                f"http://localhost/api/v2/records?timerange=0-99999999999&hidden={falsy_value}",
                headers=HEADERS,
            )
            assert r.status == 200
            d = dejsonize(r)
            assert set(r["key"] for r in d["records"]) == {"r1", "r2", "r3"}

        # Test empty hidden parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&hidden=",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
        }

        # Test unknown/invalid value - should interpret as truthy
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&hidden=maybe",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r5", "r6"}

        # Test hidden filter combined with specific timerange
        # Timerange that includes r1, r2, r3, r4
        timerange_start = 50
        timerange_end = 499

        # Without filter - should get records overlapping this range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # r1, r2, r3, r4 should be included
        assert keys == {"r1", "r2", "r3", "r4"}

        # With hidden=true - should only get hidden records in range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should not include visible records
        assert "r1" not in keys
        assert "r2" not in keys
        assert "r3" not in keys
        # Should only include hidden records
        for key in keys:
            assert key in {"r4", "r5", "r6"}

        # With hidden=false - should only get visible records in range
        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should not include hidden records
        for key in keys:
            assert key not in {"r4", "r5", "r6"}
        # Should only include visible records
        assert keys <= {"r1", "r2", "r3"}


def test_records_get_tag_filter():
    """Test the `tag` query parameter for filtering records by single and multiple tags"""

    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Add records with various tag combinations
        records = [
            dict(key="r1", mt=110, t1=100, t2=150, ds="#work"),
            dict(key="r2", mt=110, t1=200, t2=250, ds="#personal"),
            dict(key="r3", mt=110, t1=300, t2=350, ds="#work #urgent"),
            dict(key="r4", mt=110, t1=400, t2=450, ds="#work #project1"),
            dict(key="r5", mt=110, t1=500, t2=550, ds="#personal #urgent"),
            dict(key="r6", mt=110, t1=600, t2=650, ds="no tags here"),
            dict(key="r7", mt=110, t1=700, t2=750, ds="#work #urgent #project1"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r1", "r2", "r3", "r4", "r5", "r6", "r7"]

        # Test without tag parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999", headers=HEADERS
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
            "r7",
        }

        # Test with single tag filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r1", "r3", "r4", "r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=personal",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r2", "r5"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=urgent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r3", "r5", "r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r7"}

        # Test with multiple tags - should return only records with ALL specified tags
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,urgent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r3", "r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,urgent,project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=personal,urgent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r5"}

        # Test with tag filter combined with specific timerange
        timerange_start = 50
        timerange_end = 499

        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3", "r4"}

        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&tag=work",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r3", "r4"}

        # Test with multiple tags and timerange
        timerange_start = 250
        timerange_end = 599

        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&tag=work,urgent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r3"}

        # Test empty tag parameter - should return all records
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
            "r7",
        }

        # Test with non-existent tags
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=nonexistent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == set()

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,nonexistent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == set()

        # Test tag matching at the end of description (without trailing space)
        records = [
            dict(key="r8", mt=110, t1=800, t2=850, ds="Some description #endtag"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert dejsonize(r)["accepted"] == ["r8"]

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=endtag",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert "r8" in keys

        # Test with whitespace in tag list - should trim whitespace
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work, urgent, project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r7"}

        # Test tag filtering with URL-encoded '#' prefix - should work the same as without prefix
        # Note: '#' is URL-encoded as '%23'
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r1", "r3", "r4", "r7"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23personal",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r2", "r5"}

        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23endtag",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert "r8" in keys

        # Test with URL-encoded '#' prefix on multiple tags
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work,%23urgent",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r3", "r7"}

        # Test with mixed URL-encoded '#' prefix and no prefix
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work,project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r4", "r7"}

        # Test with URL-encoded '#' prefix and whitespace
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work,%20%23urgent,%20%23project1",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        assert set(r["key"] for r in d["records"]) == {"r7"}


def test_records_get_combined_filters():
    """Test combining multiple query parameters (running, hidden, tag) together

    This test ensures that all filter combinations work correctly and safely,
    including protection against SQL injection attacks through parameterized queries.
    """

    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        now = int(time.time())

        # Create a comprehensive set of test records with various combinations
        records = [
            # Visible, stopped, work
            dict(key="r1", mt=110, t1=100, t2=150, ds="#work"),
            dict(key="r2", mt=110, t1=200, t2=250, ds="#work #urgent"),
            dict(key="r3", mt=110, t1=300, t2=350, ds="#work #project1"),
            # Visible, running, work
            dict(key="r4", mt=110, t1=now - 1000, t2=now - 1000, ds="#work"),
            dict(key="r5", mt=110, t1=now - 2000, t2=now - 2000, ds="#work #urgent"),
            # Hidden, stopped, work
            dict(key="r6", mt=110, t1=400, t2=450, ds="HIDDEN #work"),
            dict(key="r7", mt=110, t1=500, t2=550, ds="HIDDEN #work #urgent"),
            # Hidden, running, work
            dict(
                key="r8",
                mt=110,
                t1=now - 3000,
                t2=now - 3000,
                ds="HIDDEN #work",
            ),
            # Visible, stopped, personal
            dict(key="r9", mt=110, t1=600, t2=650, ds="#personal"),
            dict(key="r10", mt=110, t1=700, t2=750, ds="#personal #urgent"),
            # Visible, running, personal
            dict(key="r11", mt=110, t1=now - 4000, t2=now - 4000, ds="#personal"),
            # Hidden, stopped, personal
            dict(key="r12", mt=110, t1=800, t2=850, ds="HIDDEN #personal"),
            # No tags
            dict(key="r13", mt=110, t1=900, t2=950, ds="no tags"),
            dict(key="r14", mt=110, t1=now - 5000, t2=now - 5000, ds="no tags running"),
            dict(key="r15", mt=110, t1=1000, t2=1050, ds="HIDDEN no tags"),
        ]
        r = p.put(
            "http://localhost/api/v2/records",
            json.dumps(records).encode(),
            headers=HEADERS,
        )
        assert r.status == 200
        assert len(dejsonize(r)["accepted"]) == 15

        # Test: running=true + hidden=false (visible running records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=true&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r4", "r5", "r11", "r14"}

        # Test: running=true + hidden=true (hidden running records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=true&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r8"}

        # Test: running=false + hidden=false (visible stopped records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3", "r9", "r10", "r13"}

        # Test: running=false + hidden=true (hidden stopped records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&running=false&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r6", "r7", "r12", "r15"}

        # Test: tag=work + hidden=false (visible work records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3", "r4", "r5"}

        # Test: tag=work + hidden=true (hidden work records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r6", "r7", "r8"}

        # Test: tag=work + running=true (running work records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r4", "r5", "r8"}

        # Test: tag=work + running=false (stopped work records)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3", "r6", "r7"}

        # Test: ALL THREE - tag=work + running=true + hidden=false (visible running work)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=true&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r4", "r5"}

        # Test: ALL THREE - tag=work + running=true + hidden=true (hidden running work)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=true&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r8"}

        # Test: ALL THREE - tag=work + running=false + hidden=false (visible stopped work)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3"}

        # Test: ALL THREE - tag=work + running=false + hidden=true (hidden stopped work)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=false&hidden=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r6", "r7"}

        # Test: Multiple tags + running + hidden
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,urgent&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r2"}

        # Test: Multiple tags with running filter
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work,urgent&running=true",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r5"}

        # Test: Test with personal tag
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=personal&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r9", "r10"}

        # Test: Combine all filters with timerange
        # Timerange that excludes later records
        timerange_start = 50
        timerange_end = 499

        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&tag=work&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Only r1, r2, r3 are in this timerange and match all filters
        assert keys == {"r1", "r2", "r3"}

        # Test: Combining filters with timerange that includes running records
        timerange_start = 0
        timerange_end = now + 1000

        r = p.get(
            f"http://localhost/api/v2/records?timerange={timerange_start}-{timerange_end}&tag=work&running=true&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r4", "r5"}

        # Test: Test edge case - no results when combining incompatible filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=nonexistent&running=true&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == set()

        # Test: Test with empty values for some filters (should be ignored)
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should include both running and stopped visible work records
        assert keys == {"r1", "r2", "r3", "r4", "r5"}

        # Test: Test case insensitivity with combined filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work&running=TRUE&hidden=FALSE",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r4", "r5"}

        # Test: Test alternative boolean values with combined filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=personal&running=yes&hidden=no",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r11"}

        # Test: SQL injection safety test - special characters in tags
        # These should be safely escaped and not cause SQL errors or injection
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=work%27%20OR%20%271%27=%271&running=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        # Should find no records because no tag matches the escaped string
        assert keys == set()

        # Test: URL-encoded tag with combined filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work&running=false&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r1", "r2", "r3"}

        # Test: Multiple URL-encoded tags with combined filters
        r = p.get(
            "http://localhost/api/v2/records?timerange=0-99999999999&tag=%23work,%23urgent&running=true&hidden=false",
            headers=HEADERS,
        )
        assert r.status == 200
        d = dejsonize(r)
        keys = set(r["key"] for r in d["records"])
        assert keys == {"r5"}


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


def test_version():
    """Test the version API endpoint."""
    clear_test_db()

    with MockTestServer(our_api_handler) as p:
        # Test GET version endpoint
        r = p.get("http://localhost/api/v2/version", headers=HEADERS)
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"version"}
        assert isinstance(d["version"], str)
        assert d["version"] == timetagger_version

        # Test that only GET is allowed
        r = p.put("http://localhost/api/v2/version", headers=HEADERS)
        assert r.status == 405
        r = p.post("http://localhost/api/v2/version", headers=HEADERS)
        assert r.status == 405


if __name__ == "__main__":
    run_tests(globals())
