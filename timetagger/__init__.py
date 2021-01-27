"""
Timetagger - Tag your time, and see where it has gone.
"""

__version__ = "21.1.1"

version_info = tuple(map(int, __version__.split(".")))


from . import server  # noqa
