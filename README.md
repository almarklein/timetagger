[![CI](https://github.com/almarklein/timetagger/workflows/CI/badge.svg)](https://github.com/almarklein/timetagger/actions)
[![Documentation Status](https://readthedocs.org/projects/timetagger/badge/?version=latest)](https://timetagger.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://badge.fury.io/py/timetagger.svg)](https://badge.fury.io/py/timetagger)

# TimeTagger

<a name="top"></a>

*Tag your time, get the insight* — an open source time-tracker with an
interactive user experience and powerful reporting.

* Website: https://timetagger.app  
* Demo: https://timetagger.app/demo  
* Docs: https://timetagger.readthedocs.io  
* CLI tool: https://github.com/almarklein/timetagger_cli  
* [TimeTagger_VSCodeExtension](https://github.com/Yamakaze-chan/TimeTagger_VSCodeExtension) (3rd party)

---

## Index (clickable)
- [Introduction](#introduction)  
- [Quick start — local (pip)](#quick-start)
- [Self-hosting (Docker & alternatives)](#self-hosting)
  - [Docker Compose example](#docker-compose-example)
  - [Using a custom startup script / MyPaas / Dokku](#other-deploy-options)
  - [HTTPS & security note](#security)
- [Authentication](#authentication)
  - [Credentials (bcrypt)](#credentials)
  - [Proxy / reverse-proxy auth](#proxy-auth)
- [Under the hood](#under-the-hood)
- [Documentation & links](#docs-and-links)
- [Using the hosted version](#hosted-version)
- [Show your support](#support)
- [Developers (contributing & dev setup)](#developers)
- [License, copyright & CLA](#license)
- [Acknowledgements](#acknowledgements)

---

<a name="introduction"></a>
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

[Back to top](#top)

---

<a name="quick-start"></a>
## Quick start — local (pip)

If you want to try TimeTagger quickly on your machine:

```bash
# Install
pip install -U timetagger

# Run (single-user mode on localhost)
python -m timetagger
```


Open your browser at `http://localhost:8080` (or the address printed by the server).  
Single-user mode works out-of-the-box for local testing.

For more advanced options and configuration see the docs linked below.

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Self-hosting (Docker & alternatives)

Docker images are provided via the GitHub Container Registry, so you can  
use Docker Compose to host your own server easily. There are two variants:  
one that runs the server as root inside the container and a non-root variant  
that runs as user `1000`:

- `deploy/docker-compose.yml` (root)
    
- `deploy/docker-compose.nonroot.yml` (non-root)
    

See [this article](https://timetagger.app/articles/selfhost2/) for more background.

### Docker Compose example

Here is a ready-to-use `docker-compose.yml` you can start from. (This  
example exposes the service on host port 80 — change the host port if you  
want to run alongside other services.)

```yaml

services:
  timetagger:
    image: ghcr.io/almarklein/timetagger
    ports:
      - "80:80"
    volumes:
      - ./_timetagger:/root/_timetagger
    environment:
      - TIMETAGGER_BIND=0.0.0.0:80
      - TIMETAGGER_DATADIR=/root/_timetagger
      - TIMETAGGER_LOG_LEVEL=info
      - TIMETAGGER_CREDENTIALS=test:$$2a$$08$$zMsjPEGdXHzsu0N/felcbuWrffsH4.4ocDWY5oijsZ0cbwSiLNA8.  # test:test
```

Notes:

- The `volumes` entry ensures data (SQLite DB) is persisted on the host.
    
- Replace the credentials example with your own bcrypt hashes (see below).
    
- In `docker-compose.yml` the dollar sign `$` in bcrypt hashes must be escaped as `$$` because Docker Compose does variable interpolation.
    

To deploy:

```bash
docker-compose up -d
```

Check logs with:

```bash
docker-compose logs -f timetagger
```

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

### Using a custom startup script / MyPaas / Dokku

If you want to customise startup behaviour you can mount/override the  
startup script:

```yaml
version: "3"
services:
  timetagger:
    image: ghcr.io/almarklein/timetagger
    volumes:
      - ./_timetagger:/root/_timetagger
      - ./run.py:/root/run.py    # include custom startup script
    command: python run.py       # use that instead of the default entry point
```

Alternatives to Docker Compose:

- Dokku, Swarmpit, or similar.
    
- MyPaas — you can host using a tiny Dockerfile with a few extra metadata comments.
    

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

### HTTPS & security note

Passwords are sent unencrypted from the browser to the server unless you run over HTTPS.  
It is **strongly recommended** to terminate TLS (letsencrypt) at a reverse proxy (Nginx,  
Traefik, Caddy, etc.) or use a host that handles HTTPS for you.

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Authentication

Two main ways to authenticate users:

- **Credentials** stored as bcrypt hashes (simple, built-in).
    
- **Reverse-proxy / header-based auth** where your proxy passes the username in a header.
    

### Credentials (bcrypt)

TimeTagger accepts a list of `<username>:<bcrypt-hash>` entries. You can  
provide them via an environment variable or command-line argument.

**Docker-compose example** (env var):

```yaml
environment:
  - TIMETAGGER_CREDENTIALS=alice:$$2a$$08$$abc...,bob:$$2a$$08$$xyz...
```

**Python (command-line) example**:

```bash
python -m timetagger --credentials=test:$2a$08$0CD1NFiI...
```

How to generate a bcrypt hash:

- Use [https://timetagger.app/cred](https://timetagger.app/cred) (convenient).
    
- Or use your favourite bcrypt tool/library to generate a salted hash.
    

**Important**: If you paste the hash into `docker-compose.yml`, replace each `$` with `$$` to avoid Docker Compose interpolation.

Multiple users can be added by comma-separating entries:

```
TIMETAGGER_CREDENTIALS=user1:$$hash1,user2:$$hash2
```

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

### Proxy / reverse-proxy auth

If you already authenticate at the proxy (e.g. Authelia, oauth2-proxy, etc.)  
and pass the username in a header, TimeTagger can be told to trust that header.

Example command-line:

```bash
python -m timetagger --proxy_auth_enabled=True --proxy_auth_trusted=127.0.0.1 --proxy_auth_header=X-Remote-User
```

Or as environment variables:

```bash
export TIMETAGGER_PROXY_AUTH_ENABLED=True
export TIMETAGGER_PROXY_AUTH_TRUSTED=127.0.0.1
export TIMETAGGER_PROXY_AUTH_HEADER=X-Remote-User
python -m timetagger
```

Make sure the `proxy_auth_trusted` addresses are set correctly — only trusted  
reverse proxies should be allowed to pass authentication headers.

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Under the hood

The server runs on async Python using [uvicorn](https://github.com/encode/uvicorn) and [asgineer](https://github.com/almarklein/asgineer) — which is fun and bloody fast. The app stores data in SQLite via [itemdb](https://github.com/almarklein/itemdb), making deployment simple.

The client is a mix of HTML, CSS, Markdown, and ... Python! [PScript](https://github.com/flexxui/pscript) is used to compile Python to JavaScript. This may be idiosyncratic, but it's fun!
Maybe I'll someday implement it in something that compiles down to Wasm :)

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Documentation & links

- Docs: [https://timetagger.readthedocs.io](https://timetagger.readthedocs.io/)
    
- Container image (GHCR): [https://github.com/almarklein/timetagger/pkgs/container/timetagger](https://github.com/almarklein/timetagger/pkgs/container/timetagger)
    
- Demo: [https://timetagger.app/demo](https://timetagger.app/demo)
    
- Article about self-hosting: [https://timetagger.app/articles/selfhost2/](https://timetagger.app/articles/selfhost2/)
    

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Using the hosted version

If you prefer not to self-host, you can use the hosted service at:  
[https://timetagger.app](https://timetagger.app/) — an account is €3 per month. Good if you don't want  
to maintain a server and want to support the project financially.

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Show your support

If you're self-hosting TimeTagger and want to support the project, you can:

- Write about TimeTagger in a blog post or on social media (link to `https://timetagger.app`).
    
- Contribute improvements via GitHub.
    
- Financially support by subscribing or donating (see donation links on the hosted site).
    

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Developers

If you want to hack on TimeTagger:

```sh
git clone https://github.com/almarklein/timetagger.git
cd timetagger
pip install -e .
```

Developer dependencies:

```sh
pip install invoke black flake8 pytest pytest-cov requests
```

Useful `invoke` tasks:

- `invoke -l` — list tasks
    
- `invoke clean` — remove temporary files
    
- `invoke format` — autoformat (black)
    
- `invoke lint` — flake8
    
- `invoke tests` — run pytest
    

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## License, copyright & CLA

This repository is distributed under the **GPL-3.0 License**.

Contributors must agree to the [Contributor License Agreement](https://github.com/almarklein/timetagger/blob/main/CLA.md)  
so the maintainer can use contributions in e.g. the TimeTagger.app service.  
By making a contribution to this project, you agree to the CLA.

Copyright is attributed to the specific contributors (inspect with `git blame`).

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)

---

## Acknowledgements

Thanks to everyone who contributes, files issues, tests the app, and says nice things.  
Badges up top show CI, docs, and PyPI status.

[Back to top](https://chatgpt.com/g/g-p-68baf8963a28819190b1e91ae76d9eb8-development/c/68d2e04e-4e54-832f-b4f6-4912969fcbfe#top)
