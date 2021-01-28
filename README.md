[![CI](https://github.com/almarklein/timetagger/workflows/CI/badge.svg)](https://github.com/almarklein/timetagger/actions)

# TimeTagger

*Tag your time, get the insight* - an open source time tracker with a focus on
a simple and interactive user experience.


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

You can also see it in action at https://timetagger.app - you can also
purchase an account for $2 per month so you don't have to worry about
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

## License

This code is subject to the GPL-3.0 License. Contributors must agree to the
[Contributor License Agreement](https://github.com/almarklein/timetagger/blob/main/CLA.md)
to grant the right to use contributions at e.g. the TimeTagger.app service.


## Developers

Additional developer dependencies:
```
pip install invoke black flake8 pytest requests
```

* `invoke -l` to see available invoke tasks
* `invoke clean` to remove temporary files
* `invoke format` to autoformat the code (using black)
* `invoke lint` to detect linting errors (using flake8)
* `invoke tests` to run tests (using pytest)


## API

TODO
