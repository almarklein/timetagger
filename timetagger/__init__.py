"""
Timetagger - Tag your time, get the insight.
"""

__version__ = "21.7.2"

version_info = tuple(map(int, __version__.split(".")))


from . import server  # noqa - server logic
from . import common  # noqa - common assets
from . import images  # noqa - image assets
from . import app  # noqa - app assets
from . import pages  # noqa - pages
