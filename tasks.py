""" Invoke tasks for timetagger
"""

import os
import sys
import shutil
import importlib
import subprocess

from invoke import task

# ---------- Per project config ----------

NAME = "timetagger"
LIBNAME = NAME.replace("-", "_")

# ----------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(os.path.join(ROOT_DIR, LIBNAME)):
    sys.exit("package NAME seems to be incorrect.")


@task
def tests(ctx, cover=False):
    """Perform unit tests. Use --cover to open a webbrowser to show coverage."""
    import pytest  # noqa

    test_path = "tests"
    res = pytest.main(
        ["-v", f"--cov={LIBNAME}", "--cov-report=term", "--cov-report=html", test_path]
    )
    if res:
        sys.exit(res)
    if cover:
        import webbrowser

        webbrowser.open(os.path.join(ROOT_DIR, "htmlcov", "index.html"))


@task
def lint(ctx):
    """Validate the code style (e.g. undefined names)"""
    try:
        importlib.import_module("flake8")
    except ImportError:
        sys.exit("You need to ``pip install flake8`` to lint")

    # We use flake8 with minimal settings
    # http://pep8.readthedocs.io/en/latest/intro.html#error-codes
    cmd = [
        sys.executable,
        "-m",
        "flake8",
        ROOT_DIR,
        "--max-line-length=999",
        "--extend-ignore=N,E731,E203,F541,D,B",
        "--exclude=build,dist,*.egg-info",
    ]
    ret_code = subprocess.call(cmd, cwd=ROOT_DIR)
    if ret_code == 0:
        print("No style errors found")
    else:
        sys.exit(ret_code)


@task
def checkformat(ctx):
    """Check whether the code adheres to the style rules. Use autoformat to fix."""
    black_wrapper(False)


@task
def format(ctx):
    """Automatically format the code (using black)."""
    black_wrapper(True)


def black_wrapper(writeback):
    """Helper function to invoke black programatically."""

    check = [] if writeback else ["--check"]
    exclude = "|".join(["cangivefilenameshere"])
    sys.argv[1:] = check + ["--exclude", exclude, ROOT_DIR]

    import black

    black.main()


@task
def clean(ctx):
    """Clean the repo of temp files etc."""
    # Walk over all files and delete based on name
    for root, dirs, files in os.walk(ROOT_DIR):
        for dname in dirs:
            if dname in (
                "__pycache__",
                ".cache",
                ".hypothesis",
                "_build",
                ".mypy_cache",
            ):
                shutil.rmtree(os.path.join(root, dname))
                print("Removing", dname)
        for fname in files:
            if fname.endswith((".pyc", ".pyo")) or fname in (".coverage"):
                os.remove(os.path.join(root, fname))
                print("Removing", fname)
    # Delete specific files and directories
    for fname in [
        "docs/site",
        "htmlcov",
        ".pytest_cache",
        "dist",
        "build",
        LIBNAME + ".egg-info",
    ]:
        filename = os.path.join(ROOT_DIR, fname)
        if os.path.isfile(filename):
            os.remove(filename)
            print("Removing", filename)
        elif os.path.isdir(filename):
            shutil.rmtree(filename)
            print("Removing", filename)


@task
def bumpversion(ctx, version):
    """Bump the version. If no version is specified, show the current version."""
    version = version.lstrip("v")
    # Check that we're not missing any libraries
    for x in ("setuptools", "twine"):
        try:
            importlib.import_module(x)
        except ImportError:
            sys.exit(f"You need to ``pip install {x}`` to do a version bump")
    # Check that there are no outstanding changes
    lines = (
        subprocess.check_output(["git", "status", "--porcelain"]).decode().splitlines()
    )
    lines = [line for line in lines if not line.startswith("?? ")]
    if lines:
        print("Cannot bump version because there are outstanding changes:")
        print("\n".join(lines))
        return
    # Get the version definition
    filename = os.path.join(ROOT_DIR, LIBNAME, "__init__.py")
    with open(filename, "rb") as f:
        lines = f.read().decode().splitlines()
    for line_index, line in enumerate(lines):
        if line.startswith("__version__ = "):
            break
    else:
        raise ValueError("Could not find version definition")
    # Only show the version?
    if not version.strip("x-"):
        print(lines[line_index])
        return
    # Apply change
    lines[line_index] = lines[line_index].split("=")[0] + f'= "{version}"'
    with open(filename, "wb") as f:
        f.write(("\n".join(lines).strip() + "\n").encode())
    # Ask confirmation
    subprocess.run(["git", "diff"])
    while True:
        x = input("Is this diff correct? [Y/N]: ")
        if x.lower() == "y":
            break
        elif x.lower() == "n":
            print("Cancelling (git checkout)")
            subprocess.run(["git", "checkout", filename])
            return
    # Git
    print("Git commit and tag")
    subprocess.run(["git", "add", filename])
    subprocess.run(["git", "commit", "-m", f"Bump version to {version}"])
    subprocess.run(["git", "tag", f"v{version}"])
    print(f"git push origin main v{version}")
    subprocess.run(["git", "push", "origin", "main", f"v{version}"])
    # Pypi
    input("\nHit enter to upload to pypi: ")
    dist_dir = os.path.join(ROOT_DIR, "dist")
    if os.path.isdir(dist_dir):
        shutil.rmtree(dist_dir)
    subprocess.run([sys.executable, "setup.py", "sdist", "bdist_wheel"])
    subprocess.run([sys.executable, "-m", "twine", "upload", dist_dir + "/*"])
    # Bye bye
    print("Success!")
    print("Don't forget to write release notes!")
