import time
import asyncio

from pytest import raises

from _common import run_tests
from timetagger.server._utils import swait, swait_multiple, asyncify, asyncthis


# %% Helpers

side_effect = [0]


async def a_coroutine(x):
    await asyncio.sleep(1)
    side_effect[0] += 1
    return x + 5


async def a_coroutine_that_errors(x):
    raise ValueError(x)


def plain_func(x):
    time.sleep(1)  # emulate io
    side_effect[0] += 10
    return x + 5


def plain_func_that_errors(x):
    raise ValueError(x)


# %% Tests


def test_swait():
    side_effect[0] = 0

    # It really is a co-routine :)
    res = a_coroutine(2)
    assert res != 7 and side_effect[0] == 0
    res.close()  # avoid "never awaited" warning

    # Now with swait
    res = swait(a_coroutine(2))
    assert res == 7 and side_effect[0] == 1

    # Run a coro that errors
    with raises(ValueError) as err:
        swait(a_coroutine_that_errors(3))
    assert err.value.args[0] == 3


def test_swait_multiple():
    side_effect[0] = 0

    # Need arg and must be nonzero cos
    with raises(TypeError):
        swait_multiple()
    with raises(ValueError):
        swait_multiple([])

    # OK to run with one co
    res = swait_multiple([a_coroutine(2)])
    assert res is None and side_effect[0] == 1

    # Also OK to run with loads
    t0 = time.perf_counter()
    res = swait_multiple([a_coroutine(2) for i in range(999)])
    assert res is None and side_effect[0] == 1000
    t1 = time.perf_counter()
    assert (t1 - t0) < 2


def test_asyncthis():
    side_effect[0] = 0

    # Test the plain func
    t0 = time.perf_counter()
    assert plain_func(3) == 8
    t1 = time.perf_counter()
    assert (t1 - t0) > 0.99
    assert side_effect[0] == 10

    # Get that it rerturns a co
    co = asyncthis(plain_func, 3)
    assert asyncio.iscoroutine(co)

    # Run it
    assert swait(co) == 8
    assert side_effect[0] == 20

    # Run a func that errors
    with raises(ValueError) as err:
        swait(asyncthis(plain_func_that_errors, 3))
    assert err.value.args[0] == 3


def test_asyncify():
    side_effect[0] = 0

    # Test that the decorator produces a co
    func = asyncify(plain_func)
    assert callable(func)
    assert "plain_func" in func.__name__
    co = func()
    assert asyncio.iscoroutine(co)
    co.close()  # avoid "never awaited" warning

    # Run it - note that we have a limited number of threads
    t0 = time.perf_counter()
    swait_multiple([func(3) for i in range(5)])  # nthreads = nprocesses * 5
    assert side_effect[0] == 50
    t1 = time.perf_counter()
    assert (t1 - t0) < 2


if __name__ == "__main__":
    run_tests(globals())
