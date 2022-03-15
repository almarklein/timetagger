[![CI](https://github.com/almarklein/timetagger/workflows/CI/badge.svg)](https://github.com/almarklein/timetagger/actions)
[![Documentation Status](https://readthedocs.org/projects/timetagger/badge/?version=latest)](https://timetagger.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/timetagger.svg)](https://badge.fury.io/py/timetagger)

# TimeTagger

*Tag your time, get the insight* - an open source time tracker with a focus on
a simple and interactive user experience.

* Website: https://timetagger.app
* Docs: https://timetagger.readthedocs.io
* CLI tool: https://github.com/almarklein/timetagger_cli


## Introduction

TimeTagger is a web-based time-tracking solution that can be run locally
or on a server. In the latter case, you'll want to add authentication,
and also be aware of the license restrictions.

The server runs on async Python using
[uvicorn](https://github.com/encode/uvicorn) and
[asgineer](https://github.com/almarklein/asgineer) - which is fun and bloody fast.
It uses SQLite via [itemdb](https://github.com/almarklein/itemdb) to
store the data, making it easy to deploy.

The client is a mix of HTML, CSS, Markdown, and ... Python!
[PScript](https://github.com/flexxui/pscript) is used to compile the
Python to JavaScript. This may be a bit idiosyncratic, but it's fun!
Maybe I'll someday implement it in something that compiles down to Wasm :)


## Usage example

This repo is organized as a library, making it quite flexible to apply tweaks.
See `run.py` for an example of how to run it as a web app.
See the [docs](https://timetagger.readthedocs.io) for more info.

You can also see it in action at https://timetagger.app - you can
purchase an account for €3 per month so you don't have to worry about
maintaining a server, backups, and all that. Plus you'd sponsor this
project and open source in general.

## Installation

TimeTagger is a Python library and requires Python 3.6 or higher. The dependencies are listed in `requirements.txt` - these are installed automatically when you install TimeTagger with Pip.

```
# Latest release
pip install -U timetagger

# Latest from Github
pip install -U https://github.com/almarklein/timetagger/archive/main.zip

# Uninstall
pip uninstall timetagger
```

After installation, copy and execute  `python run.py` to get started.

## Copright and license

As usual, copyright applies to whomever made a particular contribution in this repository,
which can be inspected via e.g. git blame. The owner of the copyright (i.e. the author)
is free to use their code in any way.

This code is also subject to the GPL-3.0 License, to protect it from being used
commercially by other parties.

Contributors must agree to the
[Contributor License Agreement](https://github.com/almarklein/timetagger/blob/main/CLA.md)
to grant me (Almar) the right to use their contributions at e.g. the TimeTagger.app service.
By making a contribution to this project, you agree to this CLA.


## Developers

Additional developer dependencies:
```
pip install invoke black flake8 pytest pytest-cov requests
```

* `invoke -l` to see available invoke tasks
* `invoke clean` to remove temporary files
* `invoke format` to autoformat the code (using black)
* `invoke lint` to detect linting errors (using flake8)
* `invoke tests` to run tests (using pytest)
