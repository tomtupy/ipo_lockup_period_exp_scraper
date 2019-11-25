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
