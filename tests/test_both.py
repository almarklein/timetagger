import os

from _common import run_tests

import timetagger


server_fname = os.path.dirname(timetagger.server.__file__)
client_fname = os.path.dirname(timetagger.app.__file__)


def get_common_lines_from_module(filename):
    t_begin = "# ----- COMMON PART"
    t_end = "# ----- END COMMON PART"
    if not isinstance(filename, str):
        filename = filename.__file__
    code = open(filename, "rb").read().decode()
    lines = code.split(t_begin)[1].split(t_end)[0].splitlines()
    lines.pop(0)
    lines = [line.rstrip() for line in lines if line.rstrip()]
    return lines


def test_matching_specs_and_reqs():
    """Ensure that both server and client use the same spec to
    validate items and to ensure the same required fields.
    """
    server_lines = get_common_lines_from_module(server_fname + "/_apiserver.py")
    client_lines = get_common_lines_from_module(client_fname + "/stores.py")

    assert len(server_lines) >= 4
    assert len(server_lines) == len(client_lines)
    for line1, line2 in zip(server_lines, client_lines):
        print("* " + line1 + "\n  " + line2)
        assert line1 == line2

    assert server_lines == client_lines


if __name__ == "__main__":
    run_tests(globals())
