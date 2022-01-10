# Dockerfile to run TimeTagger in a container.
#
# Note that the default authentication handler only works on localhost,
# so when deploying remotely, only the demo and sandbox work. This file
# serves two purposes:
#
# * It's an example to help users run TimeTagger in a Docker container.
# * I may use this to quickly deploy temporary builds during testing.
#
# Below are the MyPaas paramaters that I use for deploying test builds.
# You can ignore/remove these if you do not use MyPaas.
#
# mypaas.service = timetagger.test1
# mypaas.url = https://test1.timetagger.app
# mypaas.maxmem = 256m


FROM python:3.10-slim-buster

# Install dependencies (including optional ones that make uvicorn faster)
RUN pip --no-cache-dir install pip --upgrade && pip --no-cache-dir install \
    uvicorn uvloop httptools \
    fastuaparser itemdb>=1.1.1 asgineer requests \
    jinja2 markdown pscript \
    pyjwt cryptography

# This causes the cache to skip, so that we get the latest TimeTagger version.
# If this occasionally does not work (e.g. ramdom.org is out), simply comment.
ADD "https://www.random.org/cgi-bin/randbyte?nbytes=10&format=h" skipcache

# If you extend TimeTagger in your own app that uses TimeTagger as a library,
# uncomment either of these to install the latest TimeTagger.
# RUN pip install -U timetagger
# RUN pip install -U https://github.com/almarklein/timetagger/archive/main.zip

WORKDIR /root
COPY . .
CMD ["python", "run.py"]
