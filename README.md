# SEC EDGAR IPO Lockup Period Expirations Scraper
This package scrapes the lockup period expirations 
from the SEC EDGAR website.
Optionally, the results can be sent to [Kafka](https://kafka.apache.org/).

# Build
```
docker build -t ipo_lockup_period_exp_scraper:latest .
```
Optionally, a Dockerfile for ARM64 is also available:
```
docker build -t ipo_lockup_period_exp_scraper:latest -f Dockerfile.arm64 .
```

# Run
```
docker run -i -t ipo_lockup_period_exp_scraper:latest pipenv run python scraper/scraper.py
```
To specify the number of months to scrape, use the -m option:
```
docker run -i -t ipo_lockup_period_exp_scraper:latest pipenv run python scraper/scraper.py -m <number of months>
```
To send the output of the scraper to Kafka, specify a config file:
```
docker run -i -t ipo_lockup_period_exp_scraper:latest pipenv run python scraper/scraper.py --kafka-config kafka-config.yml
```

# Testing
```
docker run -i -t ipo_lockup_period_exp_scraper:latest pipenv run pytest
```