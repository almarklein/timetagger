# Dockerfile to build an image from the repo, suited for the Raspberry-pi
# Note that the build context must be the root of the repo.

FROM python:3.10-slim-bullseye

ARG DEBIAN_FRONTEND=noninteractive
ARG CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Install dependencies (including optional ones that make uvicorn faster)
RUN apt-get update && \ 
         apt-get -qq install build-essential libssl-dev libffi-dev gcc &&  \
         pip --no-cache-dir install pip --upgrade && \
         pip --no-cache-dir install -U "bcrypt<4.0.0" && \
         pip --no-cache-dir install \
         uvicorn uvloop httptools \
         fastuaparser itemdb>=1.1.1 asgineer requests \
         jinja2 markdown pscript \
         pyjwt cryptography==3.4.6

WORKDIR /root
COPY . .

RUN pip install -e .
# Example docker-compose file for TimeTagger that uses the published

CMD ["python", "-m", "timetagger"]
