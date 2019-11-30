import requests
from lxml import html
from re import sub

# contants
BASE_URL = "https://pro.edgar-online.com"
BASE_PAGE = "IPO.aspx"
BASE_MENU_ITEM_ID = "ucIPOLeftNavLPExpirations"
TABLE_CLASS = "mainContent"
TABLE_ROW_ID = "rptExpectedIPO"

def get()-> 'list':
	# Get Link to lockup expirations page
	page = requests.get(f'{BASE_URL}/{BASE_PAGE}')
	tree = html.fromstring(page.content)

	side_menu = tree.xpath(f'//*[contains(@id,"{BASE_MENU_ITEM_ID}")]')
	assert(len(side_menu) != 0)
	assert('href' in side_menu[0].attrib)

	# Follow link to lockup expirations page
	page = requests.get(f'{BASE_URL}/{side_menu[0].attrib["href"]}')
	tree = html.fromstring(page.content)

	# Get the main table
	main_table = tree.xpath(f'//table[@class="{TABLE_CLASS}"]')[0]

	# Get table rows
	main_table_rows = main_table.xpath(f'tr[contains(@id,"{TABLE_ROW_ID}")]')
	assert(len(main_table_rows) > 0)

	# Process table rows
	companies = []
	for row in main_table_rows:
		row_data = row.xpath(f'td/font')
		companies.append({"expiration_date": row_data[0].text.strip(),
							"priced_date": row_data[1].text.strip(),
							"company_name": row_data[2].xpath(f'a')[0].text.strip(),
							"symbol": row_data[3].text.strip(),
							"market": row_data[4].text.strip(),
							"price_usd": sub(r'[^\d.]', '', row_data[5].text.strip()),
							"shares": row_data[6].text.strip().replace(",", ""),
							"offer_amount_usd": sub(r'[^\d.]', '', row_data[7].text.strip())})
	assert(len(companies) > 0)
	return companies

if __name__ == "__main__":
	from optparse import OptionParser
	import yaml
	import json
	import logging
	logging.basicConfig(level=logging.DEBUG)
	parser = OptionParser()
	parser.add_option("-k", "--kafka-config", type="string", dest="kafka_config")
	(options, args) = parser.parse_args()

	# retrieve data
	ipo_data = get()
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
