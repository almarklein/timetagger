"""
Misc utils.
"""

import os
import json
import secrets
import asyncio
import concurrent
from base64 import urlsafe_b64encode, urlsafe_b64decode

import jwt


ROOT_TT_DIR = os.path.expanduser("~/_timetagger")
ROOT_USER_DIR = os.path.join(ROOT_TT_DIR, "users")
if not os.path.isdir(ROOT_USER_DIR):
    os.makedirs(ROOT_USER_DIR)


executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=None, thread_name_prefix="asyncify"
)


# %% Username stuff

ok_chars = frozenset("-_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def user2filename(user):
    """Convert a user id (e.g. email address) to the corresponding absolute filename."""
    # The rules for characters in email addresses are quite complex,
    # but can at least contain !#$%&'*+-/=?^_`{|}~. Therefore we
    # agressively create a clean representation (for recognizability)
    # and a base64 encoded string (so that we can reverse this process).

    clean = "".join((c if c in ok_chars else "-") for c in user)
    encoded = urlsafe_b64encode(user.encode()).decode()
    fname = clean + "~" + encoded + ".db"

    return os.path.join(ROOT_USER_DIR, fname)


def filename2user(filename):
    """Convert a (relative or absolute) filename to the corresponding user id."""
    fname = os.path.basename(filename)
    encoded = fname.split("~")[-1].split(".")[0]
    return urlsafe_b64decode(encoded.encode()).decode()


# %% JWT


def _load_jwt_key():
    """Load the secret JWT key from file. If it does not exist, we
    simply create a new one. This means that by removing this key file
    and restarting the server, all issued tokens before that time will
    become invalid.
    """
    filename = os.path.join(ROOT_TT_DIR, "jwt.key")
    secret = ""
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            secret = f.read().decode().strip()
    if not secret:
        secret = secrets.token_urlsafe(32)
        with open(filename, "wb") as f:
            f.write(secret.encode())
    return secret


JWT_KEY = _load_jwt_key()


def create_jwt(payload):
    """Create a new JWT with the given payload."""
    if "exp" not in payload:
        raise ValueError("JWT must have an exp field.")
    return jwt.encode(payload, JWT_KEY, algorithm="HS256")


def decode_jwt(token):
    """Decode a JWT, validating it with our key and the exp claim.
    Returns the payload as a dict.
    """
    return jwt.decode(token, JWT_KEY, algorithms=["HS256"])


def decode_jwt_nocheck(token):
    """Get the payload (as a dict) from a JWT token without performing
    any validating.
    """
    payload_b64 = token.split(".")[1]
    missing_padding = len(payload_b64) % 4
    if missing_padding:
        payload_b64 += "=" * missing_padding
    payload_s = urlsafe_b64decode(payload_b64.encode()).decode()
    return json.loads(payload_s)


# %% Async -> sync (mostly for testing)


def swait(co):
    """Sync-wait for the given coroutine, and return the result."""
    return asyncio.get_event_loop().run_until_complete(co)


def swait_multiple(cos):
    """Sync-wait for the given coroutines."""
    if not isinstance(cos, (tuple, list)):
        raise TypeError("Need list if coroutines.")
    elif not len(cos):
        raise ValueError("list of coroutines must not be empty")
    asyncio.get_event_loop().run_until_complete(
        asyncio.gather(*cos, return_exceptions=True)
    )


# %% Sync -> Async


def asyncify(func):
    """Decorator that turns a function into an awaitable co-routine, which
    will be executed in a separate thread. This allows async code to execute
    io-bound code (like querying a sqlite database) without stalling.

    Note that the code in func must be thread-safe. It's probably best to
    isolate the io-bound parts of your code and only wrap these.
    """

    async def asyncify_wrapper(*args):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, func, *args)

    asyncify_wrapper.__name__ = "asyncified_" + func.__name__
    return asyncify_wrapper


async def asyncthis(func, *args):
    """Call given function in a separate thread and await the result. This
    is/returns a co-routine.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args)
