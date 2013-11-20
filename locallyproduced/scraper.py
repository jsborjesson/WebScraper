import requests
import re
from bs4 import BeautifulSoup, SoupStrainer
from urlparse import urljoin
from locallyproduced.models import Producer

class Scraper(object):

    def __init__(self):

        # define URL:s
        self.base_url = 'http://vhost3.lnu.se:20080/~1dv449/scrape/'
        self.login_url = self.base_url + 'check.php'
        self.product_url = self.base_url + 'secure/producenter.php'

        # log in
        credentials = {'username': 'admin', 'password': 'admin'}
        self.session = self.get_logged_in_session(credentials)

    def get_logged_in_session(self, login_data):
        """Returns requests session-object"""
        # log in
        s = requests.session()
        s.post(self.login_url, data=login_data)
        return s

    def get_html(self, url):
        """Returns correctly encoded html of url"""
        response = self.session.get(url)
        # TODO: Handle 404
        return response.text.encode('latin-1', 'ignore')

    def empty_database(self):
        """Delete all rows in db"""
        Producer.objects.all().delete()

    def scrape(self):
        """Scrapes the page"""

        # clear the table
        self.empty_database()

        # parse the html
        html = self.get_html(self.product_url)
        self.parse_main_page(html)

    def parse_main_page(self, html):
        """Parses the main list of producers"""

        soup = BeautifulSoup(html, parse_only=SoupStrainer('table'))

        # remove the annoying thead
        soup.table.thead.extract()

        # parse each row
        for row in soup.find_all('tr'):
            self.parse_producer(row)


    def parse_producer(self, row):
        """Parses a table row containing a Producer and saves it to the db"""

        producer = Producer()

        # link is in first td
        link = row.td.a

        # get the name
        producer.name = link.string.strip()

        # href
        href = link['href']

        # get the id
        match = re.search('producent_(\d+)\.php', href)
        if match:
            producer.producer_id = int(match.group(1))

        # go to details page
        details_link = urljoin(self.product_url, href)
        html = self.get_html(details_link)
        self.parse_details_page(html, producer)

        producer.save()


    def parse_details_page(self, html, producer):
        """Updates supplied producer with data from details page"""

        soup = BeautifulSoup(html)

        # get location
        location_tag = soup.find('span', {'class': 'ort'})
        if location_tag:
            # remove 'Ort: ' and fix case
            location = location_tag.string[5:].capitalize()
            producer.location = location

