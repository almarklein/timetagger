import sys
import subprocess
from pkg_resources import resource_filename

from timetagger.server import create_assets_from_dir
import asgineer

from asgineer.testutils import MockTestServer
from _common import run_tests


# Create asset handler
assets = {}
assets.update(create_assets_from_dir(resource_filename("timetagger.app", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.common", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.images", ".")))
asset_handler = asgineer.utils.make_asset_handler(assets, max_age=0)


def test_assets():
    with MockTestServer(asset_handler) as p:
        # Get root
        r = p.get("")
        assert r.status == 200
        body = r.body.decode()
        assert body.startswith("<!DOCTYPE html>")
        assert r.headers["content-type"] == "text/html"
        assert r.headers["etag"]
        assert r.headers["cache-control"]

        # Get root, but compressed
        r = p.get("", headers={"accept-encoding": "gzip"})
        assert r.status == 200
        assert len(r.body) < len(body.encode())
        assert r.headers["content-type"] == "text/html"
        assert r.headers["etag"]
        assert r.headers["cache-control"]

        # Get known page
        r = p.get("demo")
        assert r.status == 200
        assert r.body.decode().startswith("<!DOCTYPE html>")
        assert r.headers["content-type"] == "text/html"
        assert r.headers["etag"]
        assert r.headers["cache-control"]
        # Test caching with etag
        r = p.get("demo", headers={"if-none-match": r.headers["etag"]})
        assert r.status == 304
        assert not r.body

        # Test known file asset
        r = p.get("timetagger192_sl.png")
        assert r.status == 200
        assert r.headers["content-type"] == "image/png"
        assert r.headers["etag"]
        assert r.headers["cache-control"]
        # Test caching with etag
        r = p.get("timetagger192_sl.png", headers={"if-none-match": r.headers["etag"]})
        assert r.status == 304
        assert not r.body

        # Get a wrong page
        for page in (
            "foobarspam",
            "index",
            "index.html",
            "foobarspam.html",
            "foobarspam.png",
        ):
            r = p.get(page)
            assert r.status == 404
            assert "404" in r.body.decode() and "not found" in r.body.decode()


hash_checker_code = """
from pkg_resources import resource_filename
from timetagger.server import create_assets_from_dir, enable_service_worker
assets = {}
assets.update(create_assets_from_dir(resource_filename("timetagger.app", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.common", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.images", ".")))
enable_service_worker(assets)
cachename = assets["sw.js"].split("currentCacheName =")[1].split("\n")[0]
print(cachename)
"""


def test_consistent_hash_for_sw():
    # It's important that the hash is consistent so let's validate this

    oneliner1 = ";".join(hash_checker_code.strip().splitlines())
    different_code = hash_checker_code.replace("{}", """{"foo": "bar"}""")
    oneliner2 = ";".join(different_code.strip().splitlines())

    x1 = subprocess.check_output([sys.executable, "-c", oneliner1])
    x2 = subprocess.check_output([sys.executable, "-c", oneliner1])
    x3 = subprocess.check_output([sys.executable, "-c", oneliner2])

    x1 = x1.decode().strip().strip(" ';")
    x2 = x2.decode().strip().strip(" ';")
    x3 = x3.decode().strip().strip(" ';")

    assert len(x1) > 20
    assert len(x2) > 20
    assert len(x3) > 20
    assert x1.startswith("timetagger")
    assert x2.startswith("timetagger")
    assert x3.startswith("timetagger")

    assert x1 == x2
    assert x1 != x3


if __name__ == "__main__":
    run_tests(globals())
