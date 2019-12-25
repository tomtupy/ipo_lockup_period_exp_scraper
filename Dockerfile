FROM python:3.7-slim-stretch

# Setup environment
RUN apt-get update -yqq \
    && apt-get install -yqq --no-install-recommends \
        python3-dev \
        libxml2-dev \
        libxslt-dev \
        gcc \
        python-lxml \
        libz-dev \
        curl \
        build-essential \
        firefox-esr

# Build librdkafka
RUN curl -L https://github.com/edenhill/librdkafka/archive/v1.2.2.tar.gz | tar xzf -
WORKDIR /librdkafka-1.2.2
RUN ./configure --prefix=/usr
RUN make -j
RUN make install
WORKDIR /

# Install geckodriver
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.26.0/geckodriver-v0.26.0-linux64.tar.gz | tar xzf -
RUN mv geckodriver /usr/local/bin/

RUN pip install pipenv

ADD Pipfile /Pipfile
RUN pipenv install

ADD scraper /scraper
ADD test /test

ADD kafka-config.yml /kafka-config.yml
