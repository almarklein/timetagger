import os
import time

from _common import run_tests
from timetagger.server import _utils as utils

from pytest import raises


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


def test_jwt_stuff():

    # The secret key must be a long enough string
    k = utils._load_jwt_key()
    assert isinstance(k, str) and len(k) > 10

    # Payload needs exp
    payload = {"name": "fooooo"}
    with raises(ValueError):
        token = utils.create_jwt(payload)

    # Get a JWT
    payload = {"name": "foo", "exp": time.time() + 100}
    token = utils.create_jwt(payload)
    assert isinstance(token, str) and token.count(".") == 2

    # Decode it
    assert utils.decode_jwt(token) == payload

    # Cannot decode an expired token - the many o's are to triffer b64 padding
    payload = {"name": "fooooo", "exp": time.time() - 1}
    token = utils.create_jwt(payload)
    with raises(Exception):
        utils.decode_jwt(token)

    # But we can always decode the unsafe way
    assert utils.decode_jwt_nocheck(token) == payload

    # Cannot decode bullshit
    with raises(Exception):
        utils.decode_jwt("not.a.token")


if __name__ == "__main__":
    run_tests(globals())
