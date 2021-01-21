# Dockerfile to run the example timetagger script.
#
# Example props for MyPaas (https://github.com/almarklein/mypaas):
# mypaas.service = timetaggertest
# mypaas.url = https://example.com
# mypaas.scale = 0
# mypaas.maxmem = 1024m

FROM python:3.8-slim-buster

# Install timetagger and dependencies. You may want to tag to a specific
# version here (instead of main), or make sure that this line always
# executes (is not cached by Docker).
RUN pip --no-cache-dir install pip --upgrade && \
    pip --no-cache-dir install -U https://github.com/almarklein/timetagger/archive/main.zip

WORKDIR /root
COPY . .
CMD ["python", "run.py"]
