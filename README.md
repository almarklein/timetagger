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

```
# Latest release
pip install -U timetagger

# Latest from Github
pip install https://github.com/almarklein/timetagger/archive/main.zip
```


## License

This code is subject to the GPL-3.0 License.

Note that this code is used as part of a closed-source application at
https://timetagger.app. If you make contributions to this project, you
also provide me the right to use these contributions as such. I'm not
sure how well this holds legally, to be honest. Therefore, I'd be
reluctant to accept larger contributions.


## Developers

Additional developer dependencies:
```
pip install black flake8 pytest requests
```

* `black .` to autoformat.
* `flake8 .` to check for linting errors.
* `pytest .` to run the unit tests.


## API

TODO
