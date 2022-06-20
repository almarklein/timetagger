# Dockerfile that is simply based on the published Docker image.
#
# Some MyPaas args (ignore if you don't use MyPaas):
#
# mypaas.service = timetagger.test1
# mypaas.url = https://test1.timetagger.app
# mypaas.volume = /root/_timetagger:/root/_timetagger
# mypaas.maxmem = 256m
# mypaas.env = TIMETAGGER_CREDENTIALS

FROM ghcr.io/almarklein/timetagger
