"""
Timetagger - Tag your time, get the insight.
"""

__version__ = "22.2.2"

version_info = tuple(map(int, __version__.split(".")))


from ._config import config  # noqa
from . import server  # noqa - server logic
from . import common  # noqa - common assets
from . import images  # noqa - image assets
from . import app  # noqa - app assets
from . import pages  # noqa - pages
