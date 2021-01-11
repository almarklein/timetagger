import re

from setuptools import find_packages, setup


with open("timetagger/__init__.py") as fh:
    VERSION = re.search(r"__version__ = \"(.*?)\"", fh.read()).group(1)


with open("requirements.txt") as fh:
    runtime_deps = [x.strip() for x in fh.read().splitlines() if x.strip()]


setup(
    name="timetagger",
    version=VERSION,
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    package_data={f"timetagger.{x}": ["*"] for x in ["client", "images", "static"]},
    python_requires=">=3.6.0",
    install_requires=runtime_deps,
    license="GPL-3.0",
    description="An open source time tracker - tag your time, and see where it has gone",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Almar Klein",
    author_email="almar.klein@gmail.com",
    url="https://github.com/almarklein/timetagger",
    data_files=[("", ["LICENSE"])],
)
