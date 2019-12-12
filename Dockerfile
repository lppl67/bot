FROM        python:3.8-alpine
RUN         apk add gcc g++ git bash make curl
COPY        . /src
WORKDIR     /src
VOLUME      ["config"]
RUN         pip install poetry && poetry install
ENTRYPOINT  poetry run base /config/config.yaml
