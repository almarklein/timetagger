import subprocess

import pscript
from pscript import py2js, evaljs as _evaljs

from _common import run_tests
from timetagger.app import dt
from timetagger.app.dt import to_time_int, time2str


def evaljs(code, final=None):
    if final:
        code += "\n\nconsole.log(" + final + ");"
    return _evaljs(code, print_result=False)


try:
    subprocess.check_output([pscript.functions.get_node_exe(), "-v"])
    HAS_NODE = True
except Exception:  # pragma: no cover
    HAS_NODE = False


def test_to_time_int():

    t1 = to_time_int("2018-04-24 13:18:00")
    t2 = to_time_int("2018-04-24 13:18:00Z")
    t3 = to_time_int("2018-04-24 13:18:00+0200")

    for t in (t1, t2, t2):
        assert isinstance(t, int)

    # Tests that don't work always/anywhere :/
    # assert t1 != t2  # This can be invalid in the winter in the UK
    # assert t1 == t3  # This is only valid in e.g. summer in Amsterdam

    # Verify that T does not matter
    assert to_time_int("2018-04-24 13:18:00") == to_time_int("2018-04-24T13:18:00")
    assert to_time_int("2018-04-24 13:18:00Z") == to_time_int("2018-04-24T13:18:00Z")
    assert to_time_int("2018-04-24 13:18:00+0200") == to_time_int(
        "2018-04-24T13:18:00+0200"
    )

    if not HAS_NODE:
        print("skipping tests that use node")
        return

    # Verify that JS and Python produce the same results
    js = py2js(open(dt.__file__, "rb").read().decode(), docstrings=False)
    js1 = evaljs(js, "to_time_int('2018-04-24 13:18:00')")
    js2 = evaljs(js, "to_time_int('2018-04-24 13:18:00Z')")
    js3 = evaljs(js, "to_time_int('2018-04-24 13:18:00+0200')")
    assert js1 == str(t1)
    assert js2 == str(t2)
    assert js3 == str(t3)

    # Again with T
    js1 = evaljs(js, "to_time_int('2018-04-24T13:18:00')")
    js2 = evaljs(js, "to_time_int('2018-04-24T13:18:00Z')")
    js3 = evaljs(js, "to_time_int('2018-04-24T13:18:00+0200')")
    assert js1 == str(t1)
    assert js2 == str(t2)
    assert js3 == str(t3)


def test_time2str():

    t1 = to_time_int("2018-04-24 13:18:00")
    t2 = to_time_int("2018-04-24 13:18:00Z")
    t3 = to_time_int("2018-04-24 13:18:00+0200")

    for t in (t1, t2, t2):
        assert isinstance(t, int)

    # Get outputs
    assert time2str(t1) == time2str(t1, None)
    s1 = time2str(t1, None)
    s2 = time2str(t2, 0)
    s3 = time2str(t3, 2)

    # Verify first. Exact output depends on timezone and summertime policy
    assert s1.startswith(("2018-04-24T13:18:00", "2018-04-24T12:48:00"))
    # Verify output in Python
    assert s2 == "2018-04-24T13:18:00Z"
    assert s3 == "2018-04-24T13:18:00+0200"

    if not HAS_NODE:
        print("skipping tests that use node")
        return

    # Verify that JS and Python produce the same results
    js = py2js(open(dt.__file__, "rb").read().decode(), docstrings=False)
    js1 = evaljs(js, f"time2str({t1})")
    js2 = evaljs(js, f"time2str({t2}, 0)")
    js3 = evaljs(js, f"time2str({t3}, 2)")
    assert js1 == s1
    assert js2 == s2
    assert js3 == s3


def test_duration_string():
    js = py2js(open(dt.__file__, "rb").read().decode(), docstrings=False)
    js += "\n\nwindow = {};"

    js1 = evaljs(js, f"duration_string(5, false)")
    js2 = evaljs(js, f"duration_string(5, true)")
    js3 = evaljs(js, f"duration_string(65, false)")
    js4 = evaljs(js, f"duration_string(65, true)")
    js5 = evaljs(js, f"duration_string(7265, false)")
    js6 = evaljs(js, f"duration_string(7265, true)")

    assert js1 == "0m"
    assert js2 == "0m05s"
    assert js3 == "1m"
    assert js4 == "1m05s"
    assert js5 == "2h01m"
    assert js6 == "2h01m05s"

    js1 = evaljs(js, f"duration_string_colon(5, false)")
    js2 = evaljs(js, f"duration_string_colon(5, true)")
    js3 = evaljs(js, f"duration_string_colon(65, false)")
    js4 = evaljs(js, f"duration_string_colon(65, true)")
    js5 = evaljs(js, f"duration_string_colon(7265, false)")
    js6 = evaljs(js, f"duration_string_colon(7265, true)")

    assert js1 == "0:00"
    assert js2 == "0:00:05"
    assert js3 == "0:01"
    assert js4 == "0:01:05"
    assert js5 == "2:01"
    assert js6 == "2:01:05"


if __name__ == "__main__":
    run_tests(globals())
