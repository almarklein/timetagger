# Dockerfile to build an image from the repo.
# Note that the build context must be the root of the repo.
# Used by CI to build the image that is pushed to ghcr.

FROM python:3.10-slim-buster

# Switch to unpriviliged user
RUN groupadd -g 1000 timetagger && \
    useradd -r -u 1000 -m -g timetagger timetagger && \
    mkdir /opt/timetagger && \
    chown timetagger:timetagger /opt/timetagger

USER 1000

# Install dependencies (including optional ones that make uvicorn faster)
RUN pip --no-cache-dir install --no-warn-script-location pip --upgrade && pip --no-cache-dir install --no-warn-script-location \
    uvicorn uvloop httptools \
    fastuaparser itemdb asgineer requests \
    jinja2 markdown pscript \
    pyjwt cryptography

WORKDIR /opt/timetagger
COPY . /opt/timetagger

RUN pip install -e .

CMD ["python", "-m", "timetagger"]
