# Dockerfile to build/run TimeTagger in a container, by installing
# timegagger using pip (from PyPi or GitHub) at build time.
#
# Below are the MyPaas parameters that I use for deploying test builds.
# You can ignore/remove these if you do not use MyPaas. You're probably
# more interested in the docker-compose.yml :)
#
# mypaas.service = timetagger.test1
# mypaas.url = https://test1.timetagger.app
# mypaas.volume = /root/_timetagger:/root/_timetagger
# mypaas.maxmem = 256m
# mypaas.env = TIMETAGGER_CREDENTIALS

FROM python:3.13-slim-bookworm

# Install dependencies (including optional ones that make uvicorn faster)
RUN pip --no-cache-dir install pip --upgrade && pip --no-cache-dir install \
    uvicorn uvloop httptools \
    fastuaparser itemdb>=1.1.1 asgineer requests \
    jinja2 markdown pscript \
    pyjwt cryptography

# This causes the cache to skip, so that we get the latest TimeTagger version.
# If this occasionally does not work (e.g. ramdom.org is out), simply comment.
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" skipcache

# Install the latest release, or the bleeding edge from GitHub
RUN pip install -U timetagger
# RUN pip install -U https://github.com/almarklein/timetagger/archive/main.zip

WORKDIR /root

CMD ["python", "-m", "timetagger"]
