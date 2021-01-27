"""
Misc utils.
"""

import os
import asyncio
import concurrent
from base64 import urlsafe_b64encode as b64encode, urlsafe_b64decode as b64decode


ROOT_USER_DIR = os.path.expanduser("~/_timetagger/users")
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
    encoded = b64encode(user.encode()).decode()
    fname = clean + "~" + encoded + ".db"

    return os.path.join(ROOT_USER_DIR, fname)


def filename2user(filename):
    """Convert a (relative or absolute) filename to the corresponding user id."""
    fname = os.path.basename(filename)
    encoded = fname.split("~")[-1].split(".")[0]
    return b64decode(encoded.encode()).decode()


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
