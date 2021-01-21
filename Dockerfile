# Dockerfile to run the example timetagger script.
#
# Example props for MyPaas (https://github.com/almarklein/mypaas):#
# mypaas.service = timetaggertest
# mypaas.url = https://example.com
# mypaas.scale = 0
# mypaas.maxmem = 1024m

FROM python:3.8-slim-buster

WORKDIR /root
COPY . .

# Install dependencies
RUN pip --no-cache-dir install pip --upgrade && pip --no-cache-dir install \
    -r requirements.txt

# If you have cloned the timetagger repo, you do not need to install it.
# RUN pip install -U https://github.com/almarklein/timetagger/archive/main.zip

CMD ["python", "run.py"]
