FROM arm64v8/python:3.7-slim-stretch

# Setup environment
RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        python3-dev \
        libxml2-dev \
        libxslt-dev \
        gcc \
        python-lxml \
        libz-dev
RUN pip install pipenv

ADD Pipfile /Pipfile
RUN pipenv install

ADD scraper /scraper
ADD test /test

