import pytest
from scraper import scraper

# verify that we get some data
def test_get():
    company_data = scraper.get()
    assert len(company_data) > 0
