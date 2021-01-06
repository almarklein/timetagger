from pkg_resources import resource_filename

from timetagger.server import create_assets_from_dir
import asgineer

from asgineer.testutils import MockTestServer
from _common import run_tests


# Create asset server
assets = {}
assets.update(create_assets_from_dir(resource_filename("timetagger.client", ".")))
assets.update(create_assets_from_dir(resource_filename("timetagger.static", ".")))
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
        r = p.get("timetagger192.png")
        assert r.status == 200
        assert r.headers["content-type"] == "image/png"
        assert r.headers["etag"]
        assert r.headers["cache-control"]
        # Test caching with etag
        r = p.get("timetagger192.png", headers={"if-none-match": r.headers["etag"]})
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


if __name__ == "__main__":
    run_tests(globals())
