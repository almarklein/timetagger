# Dockerfile to build an image from the repo.
# Note that the build context must be the root of the repo.
# Used by CI to build the image that is pushed to ghcr.
# Unpriviliged version that installs and runs as UID 1000.

FROM python:3.13-slim-bookworm

# Create unpriviliged user and group, including directory structure
RUN groupadd -g 1000 timetagger && \
    useradd -r -u 1000 -m -g timetagger timetagger && \
    mkdir /opt/timetagger && \
    chown timetagger:timetagger /opt/timetagger

# Switch to unpriviliged user
USER 1000

WORKDIR /opt/timetagger
COPY . /opt/timetagger

# Install dependencies (including optional ones that make uvicorn faster)
# Upgrade pip to the lastest version
RUN pip --no-cache-dir install pip --upgrade && \
    # Install optional depedencies that make uvicorn faster
    pip --no-cache-dir install uvicorn uvloop httptools && \
    # Install timetagger depedencies defined via setup.py
    pip install --no-cache-dir --no-warn-script-location -e .

CMD ["python", "-m", "timetagger"]
