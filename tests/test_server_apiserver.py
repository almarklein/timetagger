import os
import json

from asgineer.testutils import MockTestServer

from _common import run_tests
from timetagger.server import _apiserver as apiserver
from itemdb import ItemDB


USER = "test"


def clear_test_db():
    filename = apiserver.user2filename(USER)
    if os.path.isfile(filename):
        os.remove(filename)


def get_from_db(what):
    filename = apiserver.user2filename(USER)
    return ItemDB(filename).select_all(what)


async def our_api_handler(request):
    """Wrapper handler."""
    apipath = request.path[len("/api/v1/") :]
    return await apiserver.api_handler(request, apipath, USER)


def dejsonize(r):
    return json.loads(r.body.decode())


def test_auth():
    clear_test_db()

    # There is not auth - this is something to be implemented yourself
    with MockTestServer(our_api_handler) as p:
        r = p.get("/api/v1/updates?since=0")
        assert r.status == 200


def test_fails():

    with MockTestServer(our_api_handler) as p:

        # Invalid API version
        r = p.get("http://localhost/api/v99/")
        assert r.status == 404

        # Invalid API path
        r = p.get("http://localhost/api/v1/records_xxx")
        assert r.status == 404

        # Can only GET updates
        r = p.put("http://localhost/api/v1/updates?since=0")
        assert r.status == 405
        r = p.post("http://localhost/api/v1/updates?since=0")
        assert r.status == 405
        # Can only PUT records
        r = p.get("http://localhost/api/v1/records")
        assert r.status == 405
        r = p.post("http://localhost/api/v1/records")
        assert r.status == 405
        # Get only GET or PUT settings
        r = p.post("http://localhost/api/v1/settings")
        assert r.status == 405
        # ...
        r = p.post("http://localhost/api/v1/forcereset")
        assert r.status == 405


def test_api_main():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:

        # Get API root
        r = p.get("/api/v1/")

        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d, dict)
        assert d["version"] == 1


def test_settings():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:

        # Initially the settings list is empty
        r = p.get("http://localhost/api/v1/settings")
        assert r.status == 200
        d = dejsonize(r)
        assert set(d.keys()) == {"server_time", "settings"}
        x = d["settings"]
        assert isinstance(x, list) and len(x) == 0

        # Put some settings in
        settings = [
            dict(key="pref1", mt=110, value="xx"),
            dict(key="pref2", mt=110, value="xx"),
        ]
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 200
        assert "ok" in r.body.decode().lower()

        # Now there are two
        r = p.get("http://localhost/api/v1/settings")
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
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "ok"
        assert len(dejsonize(r)["accepted"]) == 3

        # Now there are three
        r = p.get("http://localhost/api/v1/settings")
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
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == ["pref4"]
        assert "missing" in dejsonize(r)["errors"][0]

        # Try adding setting with wrong field type
        settings = [dict(key="pref6", mt="xx", value=42)]
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == []
        assert "invalid literal" in dejsonize(r)["errors"][0]

        # Try adding data over 10 MiB
        settings = [dict(key="pref8", mt=100, value=42)] * 600000
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 500
        assert "too large" in r.body.decode().lower()

        # Try adding settings with too long fields
        settings = [
            dict(key="p" * 256, mt=100, value=42),
            dict(key="pref10", mt=100, value="x" * 256),
        ]
        r = p.put("http://localhost/api/v1/settings", json.dumps(settings).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == []
        assert "less than 256" in dejsonize(r)["errors"][0]
        assert "less than 256" in dejsonize(r)["errors"][1]

        # Check status. This checks that all the above requests
        # failed without adding settings in the same request
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["settings"]) == 4


def test_records():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:

        # Currently no records
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        records = dejsonize(r)["records"]
        assert records == []

        # Add records
        records = [
            dict(key="r11", mt=110, t1=100, t2=150, ds="#p1"),
            dict(key="r12", mt=110, t1=310, t2=350, ds="#p1"),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "ok"
        assert dejsonize(r)["accepted"] == ["r11", "r12"]
        assert dejsonize(r)["errors"] == []

        # Check status
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 2

        # Now add more records
        records = [
            dict(key="r13", mt=120, t1=100, t2=150, ds="#p2"),
            dict(key="r14", mt=120, t1=310, t2=350, ds="#p2"),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert "ok" in r.body.decode().lower()

        # Check status
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 4

        # Try adding record with OK missing fields
        records = [dict(key="r22", mt=120, t1=100, t2=150)]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "ok"
        assert dejsonize(r)["accepted"] == ["r22"]

        # -- fails

        # Try adding with a dict
        r = p.put("http://localhost/api/v1/records", json.dumps({}).encode())
        assert r.status == 500
        assert "TypeError" in r.body.decode()

        # Actually, not really a fail, but you can send an empty list ...
        r = p.put("http://localhost/api/v1/records", json.dumps([]).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "ok"
        assert dejsonize(r)["accepted"] == []

        # Try adding record with BAD missing fields
        records = [
            dict(key="r21", mt=120, t1=310, t2=350, ds="xx"),
            dict(key="r22", mt=120, t1=100, ds="xx"),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == ["r21"]
        assert dejsonize(r)["fail"] == ["r22"]
        assert "missing" in dejsonize(r)["errors"][0]

        # Try adding record with wrong field type
        records = [
            dict(key="r23", mt="xx", t1=310, t2=350, ds="xx"),
            dict(key="r24", mt=120, t1="xx", t2=150, ds="xx"),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["fail"] == ["r23", "r24"]
        assert "invalid literal" in dejsonize(r)["errors"][0]
        assert "invalid literal" in dejsonize(r)["errors"][1]

        # Try adding records over 10 MiB
        records = [dict(key="r25", mt=120, t1=310, t2=350, ds="xx")] * 200000
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 500
        assert "too large" in r.body.decode().lower()

        # Try adding records with too long fields
        records = [
            dict(key="r26", mt=120, t1=310, t2=350, ds="x" * 1000),
            dict(key="r27", mt=120, t1=310, t2=350, ds="x" * 257),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["fail"] == ["r26", "r27"]
        assert "less than 256" in dejsonize(r)["errors"][0]
        assert "less than 256" in dejsonize(r)["errors"][1]

        # Try adding records that are not even dicts or missing a key
        records = [
            dict(key="r28", mt=120, t1="xx", t2=350, ds="x"),
            ["r17"],
            dict(mt=120, t1=310, t2=350, ds="x"),  # no key
            dict(key="r29", mt=120, t1="xx", t2=350, ds="x"),
        ]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert dejsonize(r)["status"] == "fail"
        assert dejsonize(r)["accepted"] == []
        assert dejsonize(r)["fail"] == ["r28", "r29"]
        assert "invalid literal" in dejsonize(r)["errors"][0]
        assert "invalid literal" in dejsonize(r)["errors"][1]
        assert "not a dict with str" in dejsonize(r)["errors"][2]
        assert "not a dict with str" in dejsonize(r)["errors"][3]

        # Check status. This checks that all the above requets
        # failed without adding records in the same request
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert len(d["records"]) == 6


def test_updates():
    clear_test_db()

    with MockTestServer(our_api_handler) as p:

        # Get updates
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert isinstance(d, dict)
        assert "server_time" in d
        assert "reset" in d
        assert d["records"] == []
        assert d["settings"] == []

        # Post a record
        records = [dict(key="r1", mt=110, t1=100, t2=110, ds="A record 1!")]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert "ok" in r.body.decode().lower()

        # Post another record
        records = [dict(key="r2", mt=110, t1=200, t2=210, ds="A record 2!")]
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert "ok" in r.body.decode().lower()

        # Get updates again
        r = p.get("http://localhost/api/v1/updates?since=0")
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
        r = p.put("http://localhost/api/v1/records", json.dumps(records).encode())
        assert r.status == 200
        assert "ok" in r.body.decode().lower()

        # If we query all updates, we get 3
        r = p.get("http://localhost/api/v1/updates?since=0")
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 3
        assert set(x["key"] for x in d["records"]) == {"r1", "r2", "r3"}
        st2 = d["server_time"]

        # If we query updates since st1, we get 2
        r = p.get("http://localhost/api/v1/updates?since=" + str(st1))
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 2
        assert set(x["key"] for x in d["records"]) == {"r1", "r3"}

        # If we query updates since st2, we get 0
        r = p.get("http://localhost/api/v1/updates?since=" + str(st2))
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 0

        # Force reset
        r = p.put("http://localhost/api/v1/forcereset")
        assert r.status == 200

        # If we query updates since st2 again, we NOW get 3
        r = p.get("http://localhost/api/v1/updates?since=" + str(st2))
        assert r.status == 200
        d = dejsonize(r)
        assert d["reset"] is True
        assert len(d["records"]) == 3
        st3 = d["server_time"]

        # If we query updates since st3, its zero again
        r = p.get("http://localhost/api/v1/updates?since=" + str(st3))
        assert r.status == 200
        d = dejsonize(r)
        assert not d["reset"]
        assert len(d["records"]) == 0

        # If we query yet a bit later, we can be sure that the update was quick
        r = p.get("http://localhost/api/v1/updates?since=" + str(st3 + 1))
        assert r.status == 200
        d = dejsonize(r)
        assert d["reset"] == 0 and d["reset"] is not False  #

        # -- fails

        # Get updates wrong
        r = p.get("http://localhost/api/v1/updates")
        assert r.status == 400
        assert "updates needs" in r.body.decode() and "since" in r.body.decode()
        #
        r = p.get("http://localhost/api/v1/updates?since=foo")
        assert r.status == 400
        assert "updates needs float" in r.body.decode() and "since" in r.body.decode()


if __name__ == "__main__":
    run_tests(globals())
