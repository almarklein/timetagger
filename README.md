[![CI](https://github.com/almarklein/timetagger/workflows/CI/badge.svg)](https://github.com/almarklein/timetagger/actions)
[![Documentation Status](https://readthedocs.org/projects/timetagger/badge/?version=latest)](https://timetagger.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/timetagger.svg)](https://badge.fury.io/py/timetagger)

# TimeTagger

*Tag your time, get the insight* - an open source time-tracker with an
interactive user experience and powerful reporting.

* Website: https://timetagger.app
* Demo: https://timetagger.app/demo
* Docs: https://timetagger.readthedocs.io
* CLI tool: https://github.com/almarklein/timetagger_cli


## Introduction

TimeTagger is a web-based time-tracking solution that can run locally
or on a server. It's aimed at individuals and freelancers, and has the
following features:

* Intuitive UI based around an interactive timeline.
* Lightweight feel by use of tags rather than projects.
* Reporting in PDF and CSV.
* Set daily/weekly/monthly targets.
* Integrated Pomodoro method (experimental).
* Responsive: works well on small and large screens.
* Sync between devices.


## Under the hood

The server runs on async Python using
[uvicorn](https://github.com/encode/uvicorn) and
[asgineer](https://github.com/almarklein/asgineer) - which is fun and bloody fast.
It uses SQLite via [itemdb](https://github.com/almarklein/itemdb) to
store the data, making it easy to deploy.

The client is a mix of HTML, CSS, Markdown, and ... Python!
[PScript](https://github.com/flexxui/pscript) is used to compile the
Python to JavaScript. This may be a bit idiosyncratic, but it's fun!
Maybe I'll someday implement it in something that compiles down to Wasm :)


## Install and run

TimeTagger is implemented as a Python library that requires Python 3.6 or higher. The dependencies are listed in `requirements.txt` - these are installed automatically when you install TimeTagger with Pip.

```
# Install
pip install -U timetagger

# Run
python -m timetagger
```

If the server runs on your local machine, you can use single-user mode out-of-the-box.


## Self-hosting your time tracker

Docker images are provided via the [Github container registry](https://github.com/almarklein/timetagger/pkgs/container/timetagger),
so you can use e.g. Docker-compose to easily host your own server.

There are two variants, one that runs the server as root inside the container and a nonroot variant
that runs as user 1000:
- [docker-compose.yml](https://github.com/almarklein/timetagger/blob/main/deploy/docker-compose.yml)
- [docker-compose.nonroot.yml](https://github.com/almarklein/timetagger/blob/main/deploy/docker-compose.nonroot.yml)
 
See [this article](https://timetagger.app/articles/selfhost2/) for more information about self hosting.

### Authentication using credentials

If you want multiple users, or if the server is not on localhost, you
may want to provide the server with user credentials using an
environment variable or a command line arg (see the
[docs on config](https://timetagger.readthedocs.io/en/latest/libapi/)).

```
# Using command-line args
python -m timetagger --credentials=test:$2a$08$0CD1NFiIbancwWsu3se1v.RNR/b7YeZd71yg3cZ/3whGlyU6Iny5i

# Using environment variables
export TIMETAGGER_CREDENTIALS='test:$2a$08$0CD1NFiIbancwWsu3se1v.RNR/b7YeZd71yg3cZ/3whGlyU6Iny5i'
python -m timetagger
```

The credentials take the form "<username>:<hash>", where the hash is a
(salted) BCrypt hash of the password. You can generate credentials using
e.g. https://timetagger.app/cred.


### Authentication using a reverse proxy

If you have a reverse proxy which already authenticates users (e.g. [Authelia](https://www.authelia.com)) and provides the username through a HTTP header, you can tell TimeTagger to use this information. To configure it there are three environment variables and command line arguments (see the
[docs on config](https://timetagger.readthedocs.io/en/latest/libapi/)).

```
# Using command-line args
python -m timetagger --proxy_auth_enabled=True --proxy_auth_trusted=127.0.0.1 --proxy_auth_header=X-Remote-User

# Using environment variables
export TIMETAGGER_PROXY_AUTH_ENABLED=True TIMETAGGER_PROXY_AUTH_TRUSTED=127.0.0.1 TIMETAGGER_PROXY_AUTH_HEADER=X-Remote-User
python -m timetagger
```


## Show your support

If you're self-hosting TimeTagger and want to support the project, you can:

* Write something about TimeTagger in a blog post or social media (and link to `https://timetagger.app`). This helps search engines find it better.
* Contribute improvements via Github.
* For financial support you can take a subscription or donate (see the donation links on the side).


## Using the hosted version

You can also make use of https://timetagger.app so you don't have to worry about
maintaining a server, backups, and all that. An account is just €3 per month.
With that you'd also sponsor this project and open source in general.


## Copyright and license

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

Clone the repo and install in development mode:

```sh
git clone https://github.com/almarklein/timetagger.git
cd timetagger
pip install -e .
```

Install additional developer dependencies:

```
pip install invoke black flake8 pytest pytest-cov requests
```

Then these commands can be used during development:

* `invoke -l` to see available invoke tasks
* `invoke clean` to remove temporary files
* `invoke format` to autoformat the code (using black)
* `invoke lint` to detect linting errors (using flake8)
* `invoke tests` to run tests (using pytest)
