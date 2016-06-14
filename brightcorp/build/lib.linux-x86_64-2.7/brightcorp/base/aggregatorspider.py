"""
Base class for Aggregator Crawlers
"""

from brightcorp.base.atsspiders import ATSSpider
from scrapy.http import Request

class AggregatorSpider(ATSSpider):

    aggregator = 1
    start_url = "" ##This must be defined by the child
    start_urls = []

    def __init__(self, *args, **kwargs):
        self.start_urls.append(self.start_url);
        super(AggregatorSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        yield Request(url=self.start_url, callback=self.parse)
