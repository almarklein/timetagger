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
Any changes you make will be directly (the client syncs every 10s) visible in
the web client.

This makes it possible to create alternative clients, like the [TimeTagger CLI](https://github.com/almarklein/timetagger_cli),
or to automate the tracking of certain processes by writing a script.


## Run your own server

TimeTagger provides an example/default script to run the TimeTagger app locally
in [run.py](https://github.com/almarklein/timetagger/blob/main/run.py).
You can also integrate TimeTagger into a larger web application, or extend
it in your own ways using the [library](libapi.md).
One prerequisite is that the web-server framework is
async. Examples can be [Asgineer](https://github.com/almarklein/asgineer),
[Responder](https://github.com/taoufik07/responder),
[Starlette](https://github.com/encode/starlette),
[Quart](https://pgjones.gitlab.io/quart/), etc.

You can do whatever you want when you run things locally. When you host it
on the web, you should take care of authentication, and make sure that you
comply to the TimeTagger license (GPLv3).

Also check [this article](https://timetagger.app/articles/selfhost/) about setting up TimeTagger.

If you're interested in including TimeTagger into a larger product,
contact [me](https://almarklein.org) for information about an OEM license.
