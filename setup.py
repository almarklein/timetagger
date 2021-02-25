import re

from setuptools import find_packages, setup


with open("timetagger/__init__.py") as fh:
    VERSION = re.search(r"__version__ = \"(.*?)\"", fh.read()).group(1)


with open("requirements.txt") as fh:
    runtime_deps = [x.strip() for x in fh.read().splitlines() if x.strip()]


short_description = (
    "Tag your time, get the insight - an open source time tracker for individuals"
)
long_description = """
# Timetagger

An open source time tracker with a focus on a simple and interactive user experience.

* Website: https://timetagger.app
* Github: https://github.com/almarklein/timetagger

<br />
<img src='https://timetagger.app/screenshot1.png' width='400px' />
"""

setup(
    name="timetagger",
    version=VERSION,
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    package_data={
        f"timetagger.{x}": ["*"] for x in ["common", "images", "app", "pages"]
    },
    python_requires=">=3.6.0",
    install_requires=runtime_deps,
    license="GPL-3.0",
    description=short_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Almar Klein",
    author_email="almar.klein@gmail.com",
    url="https://github.com/almarklein/timetagger",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
