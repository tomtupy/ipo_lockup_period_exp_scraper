import requests
from lxml import html
from re import sub
import time
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import *
# Set the threshold for selenium to WARNING
from selenium.webdriver.remote.remote_connection import LOGGER as seleniumLogger
seleniumLogger.setLevel(logging.WARNING)
# Set the threshold for urllib3 to WARNING
from urllib3.connectionpool import log as urllibLogger
urllibLogger.setLevel(logging.WARNING)

# contants
DEFAULT_MONTHS_LOOKAHEAD = 2
BASE_URL = "https://pro.edgar-online.com"
BASE_PAGE = "IPO.aspx"
IPO_MENU_LP_EXP_ITEM_ID = "ucIPOLeftNavLPExpirations"
TABLE_CLASS = "mainContent"
TABLE_ROW_ID = "rptExpectedIPO"
LINK_NEXT_MONTH_ID = "lnkNextMonth"
LINK_NEXT_RESULTS_ID = "lnkNext"
LINK_NEXT_MORE_ID = "lnkNextMore"

def process_rows(elem_table_rows, companies)-> 'list':
	row_count = 0
	for row in elem_table_rows:
		row_data = row.find_elements_by_xpath(f'td/font')
		companies.append({"expiration_date": row_data[0].text.strip(),
							"priced_date": row_data[1].text.strip(),
							"company_name": row_data[2].find_element_by_xpath('a').text.strip(),
							"symbol": row_data[3].text.strip(),
							"market": row_data[4].text.strip(),
							"price_usd": sub(r'[^\d.]', '', row_data[5].text.strip()),
							"shares": row_data[6].text.strip().replace(",", ""),
							"offer_amount_usd": sub(r'[^\d.]', '', row_data[7].text.strip())})
		row_count += 1
	logging.debug(f" * process_rows got {row_count} items")
	return companies

def get_rows_from_table(driver):
	# Get main table
	elem_main_table = driver.find_element_by_xpath(f"//table[@class='{TABLE_CLASS}']")

	# Get table rows
	elem_table_rows = elem_main_table.find_elements_by_xpath(f"//tr[contains(@id,'{TABLE_ROW_ID}')]")
	assert(len(elem_table_rows) > 0)
	return elem_table_rows

def get_next_month_link(driver):
	# Get main table 
	elem_main_table = driver.find_element_by_xpath(f"//table[@class='{TABLE_CLASS}']")
	# Get next month link
	elem_link_lpexp = elem_main_table.find_element_by_xpath(f"//a[contains(@id,'{LINK_NEXT_MONTH_ID}')]")
	assert(elem_link_lpexp is not None)
	return elem_link_lpexp.get_attribute("href")

def get_next_results_link(driver):
	# Get main table
	elem_main_table = driver.find_element_by_xpath(f"//table[@class='{TABLE_CLASS}']")
	# Get next link
	next_link = None
	try:
		elem_link_lpexp = elem_main_table.find_element_by_xpath(f"//a[(contains(@id,'{LINK_NEXT_RESULTS_ID}')) and not(contains(@id,'{LINK_NEXT_MONTH_ID}')) and not(contains(@id,'{LINK_NEXT_MORE_ID}'))]")
		assert(elem_link_lpexp is not None)
		if elem_link_lpexp.text.strip():
			next_link = elem_link_lpexp.get_attribute("href")
	except NoSuchElementException:
		logging.info("* Next link not found")
	return next_link

def get(months = DEFAULT_MONTHS_LOOKAHEAD)-> 'list':
	# Load webdriver
	options = Options()
	options.headless = True
	logging.info("Loading Driver")
	driver = webdriver.Firefox(options=options)
	# Get Link to lockup expirations page
	driver.get(f'{BASE_URL}/{BASE_PAGE}')

	# Get main table
	logging.info(" * Getting main table")
	elem_main_table = driver.find_element_by_xpath("/html/body/form/table")

	# Get left column div
	elem_column_left_div = elem_main_table.find_element_by_xpath("//div[@id='columnLeft']")

	# Get lockup expirations link
	logging.info(" * lockup expirations link")
	elem_menu_item_lpexp = elem_column_left_div.find_element_by_xpath(f"//a[contains(@id,'{IPO_MENU_LP_EXP_ITEM_ID}')]")
	elem_link_lpexp = elem_menu_item_lpexp.get_attribute("href")
	assert(elem_link_lpexp is not None)

	# Navigate to lockup expirations page
	logging.info(" * Navigating to lockup expirations page")
	driver.get(elem_link_lpexp)

	# Process table rows
	companies = []

	for month_idx in range(months):
		print(month_idx)
		if month_idx != 0:
			# Navigate to next month
			logging.info(" * Getting next month link")
			elem_link = get_next_month_link(driver)
			logging.info(f" * Navigating to next month {elem_link}")
			driver.execute_script(f'{elem_link}')
			time.sleep(5)

		next_link = "current"
		while next_link is not None:
			# Get main table
			logging.info(f" * Parsing {month_idx} month's table")
			elem_table_rows = get_rows_from_table(driver)
			companies = process_rows(elem_table_rows, companies)
			logging.info(" * Getting next page link")
			# Check for next page
			next_link = get_next_results_link(driver)
			if next_link is not None:

				logging.info(f" * Navigating to next page {next_link}")
				driver.execute_script(f'{next_link}')
				time.sleep(5)

	# Kill driver
	driver.quit()

	# Sanity check on data
	assert(len(companies) > 0)
	assert(len(companies[0]["expiration_date"]) > 0)
	assert(len(companies[0]["priced_date"]) > 0)
	assert(len(companies[0]["company_name"]) > 0)
	assert(len(companies[0]["symbol"]) > 0)
	assert(len(companies[0]["market"]) > 0)
	assert(len(companies[0]["price_usd"]) > 0)
	assert(len(companies[0]["shares"]) > 0)
	assert(len(companies[0]["offer_amount_usd"]) > 0)
	return companies

if __name__ == "__main__":
	from optparse import OptionParser
	import yaml
	import json
	import logging
	logging.basicConfig(level=logging.DEBUG)
	parser = OptionParser()
	parser.add_option("-k", "--kafka-config", type="string", dest="kafka_config")
	parser.add_option("-m", "--months", type="int", dest="months_lookahead", default=DEFAULT_MONTHS_LOOKAHEAD)
	(options, args) = parser.parse_args()

	# retrieve data
	ipo_data = get(options.months_lookahead)
	logging.info(ipo_data)

	# publish to kafka if config is specified
	if options.kafka_config is not None:
		from confluent_kafka import avro
		from confluent_kafka.avro import AvroProducer

		config = None
		with open(options.kafka_config) as f:
			try:
				config = yaml.safe_load(f)
			except yaml.YAMLError as exc:
				logging.error(exc)
				exit(1)

		value_schema = avro.loads(json.dumps(config['value-schema']))

		avroProducer = AvroProducer({
			  'bootstrap.servers': f"{config['connection']['kafka-host']}:{config['connection']['kafka-port']}",
			  'schema.registry.url': f"http://{config['connection']['schema-registry-host']}:{config['connection']['schema-registry-port']}"
			  }, default_value_schema=value_schema)

		for ipo_record in ipo_data:
			# sample ipo record
			# {'expiration_date': '11/4/2019',
			#  'priced_date': '5/7/2019',
			#  'company_name': 'LANDCADIA HOLDINGS II, INC.',
			#  'symbol': 'LCAHU',
			#  'market': 'NASDAQ Capital',
			#  'price_usd': '10.00',
			#  'shares': '27500000',
			#  'offer_amount_usd': '275000000.00'}

			# skip priced date
			ipo_record.pop('priced_date')

			# cast types
			ipo_record['price_usd'] = float(ipo_record['price_usd'])
			ipo_record['offer_amount_usd'] = float(ipo_record['offer_amount_usd'])
			ipo_record['shares'] = int(ipo_record['shares'])

			logging.debug("Publising", ipo_record)

			avroProducer.produce(topic=config['topic'], value=ipo_record)

		# Flush messages
		avroProducer.flush()
