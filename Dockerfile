FROM        python:3.8-alpine
COPY        . /src
WORKDIR     /src
VOLUME      ["src"]
RUN         apk add gcc g++ git bash make curl --no-cache \
                && pip install -Ur requirements.txt

