# Dockerfile to build an image from the repo.
# Note that the build context must be the root of the repo.
# Used by CI to build the image that is pushed to ghcr.
# Unpriviliged version that installs and runs as UID 1000.

FROM python:3.10-slim-buster

# Switch to unpriviliged user
RUN groupadd -g 1000 timetagger && \
    useradd -r -u 1000 -m -g timetagger timetagger && \
    mkdir /opt/timetagger && \
    chown timetagger:timetagger /opt/timetagger

USER 1000

WORKDIR /opt/timetagger
COPY . /opt/timetagger

RUN pip install --no-cache-dir --no-warn-script-location -e .

CMD ["python", "-m", "timetagger"]
