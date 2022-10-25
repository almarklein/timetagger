# Welcome to the TimeTagger docs

[TimeTagger](https://timetagger.app) is an open source time tracker
with a focus on a simple and interactive user experience.

These docs are intended for developers who want to either
communicate with the server via the [web API](webapi.md), or
run their own server using the [library](libapi.md).


## Using the public web API

The [web API](webapi.md) provides a way to communicate with the TimeTagger server
(either the one at timetagger.app, or one you host yourself). It allows you
to query, create, and update time-records outside of the web interface.
Any changes you make will be visible in the web client almost directly (the client syncs every 10s).

This makes it possible to create alternative clients, like the [TimeTagger CLI](https://github.com/almarklein/timetagger_cli),
or to automate the tracking of certain processes by writing a script.


## Run your own server

TimeTagger provides an example/default script to run the TimeTagger app locally
in [`__main__.py`](https://github.com/almarklein/timetagger/blob/main/timetagger/__main__.py).
You can also integrate TimeTagger into a larger web application, or extend
it in your own ways using the [library](libapi.md).
One prerequisite is that the web-server framework is
async. Examples can be [Asgineer](https://github.com/almarklein/asgineer),
[Responder](https://github.com/taoufik07/responder),
[Starlette](https://github.com/encode/starlette), and
[Quart](https://pgjones.gitlab.io/quart/).


You can do whatever you want when you run things locally. When you host it
on the web, you should take care of authentication, and make sure that you
comply to the TimeTagger license (GPLv3).

Note that when you run your own server, you probably want to make sure that it's
always on. See [this article](https://tderflinger.com/en/using-systemd-to-start-a-python-application-with-virtualenv)
for autostarting TimeTagger on Linux systems. The TimeTagger client has a local
cache and stays working even when the server is off. In this case the
sync indicator icon in the top left will show an exclamation mark.

Also check [this article](https://timetagger.app/articles/selfhost/) about self-hosting TimeTagger.

If you're interested in including TimeTagger into a larger product,
contact [me](https://almarklein.org) for information about an OEM license.
