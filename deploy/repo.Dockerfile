# Dockerfile to build an image from the repo.
# Note that the build context must be the root of the repo.
# Used by CI to build the image that is pushed to ghcr.

FROM python:3.10-slim-buster

WORKDIR /root
COPY . .

RUN pip install --no-cache-dir --no-warn-script-location -e .

CMD ["python", "-m", "timetagger"]
