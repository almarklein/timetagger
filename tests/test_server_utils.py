import os

from _common import run_tests
from timetagger.server import _utils as utils


def test_user2filename_and_filename2user():

    fnamechars = "".join(utils.ok_chars) + "=~."

    examples = [
        "foo@bar.com",
        "a.typical.name@someprovider.com",
        "does not have to be email",
        "john.do+spam$%^@somedo.main.co.uk",
        "with~~tilde.too@do.main",
        "unicode€éö ?@grr.com",
    ]

    for email in examples:
        filename = utils.user2filename(email)
        fname = os.path.basename(filename)
        print(fname)

        assert fname.endswith(".db")
        assert fname.count("~") == 1
        assert fname.count(".") == 1

        assert all(c in fnamechars for c in fname)

        assert fname != filename
        assert utils.filename2user(fname) == email
        assert utils.filename2user(filename) == email


if __name__ == "__main__":
    run_tests(globals())
