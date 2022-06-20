# Dockerfile to build an image from the repo.
# Note that the build context must be the root of the repo.
# Used by CI to build the image that is pushed to ghcr.

FROM python:3.10-slim-buster

# Install dependencies (including optional ones that make uvicorn faster)
RUN pip --no-cache-dir install pip --upgrade && pip --no-cache-dir install \
    uvicorn uvloop httptools \
    fastuaparser itemdb>=1.1.1 asgineer requests \
    jinja2 markdown pscript \
    pyjwt cryptography

WORKDIR /root
COPY . .

RUN pip install -e .

CMD ["python", "-m", "timetagger"]
