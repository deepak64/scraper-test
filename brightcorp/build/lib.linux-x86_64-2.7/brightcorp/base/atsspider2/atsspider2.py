from datetime import datetime
from urlparse import urlsplit

from scrapy.exceptions import CloseSpider
from scrapy.selector import Selector
from scrapy import signals
from scrapy.utils.misc import arg_to_iter
from scrapy.xlib.pydispatch import dispatcher

from brightcorp.base.atsspider2 import ATSBaseSpider
from brightcorp.items import BrightcorpItemLoader
from brightcorp.lib.utils import validate


class ATSSpider2(ATSBaseSpider):
    """ ATS Base spider for site crawlers """
    # aggregator flag
    aggregator = 0

    # autocrawl flag
    autocrawl = 0

    # if True, append URL netloc to allowed_domains
    allowed_domain_by_netloc = False

    url_fragmentanchor = ""

    # raise a CloseSpider exception if there are no current job openings
    no_jobs_message = []

    # raise a DropItem exception if an error message is foundon the job page
    item_error_messages = []

    # set meta language
    language = ""

    # define base url for detail page
    detail_base_url = ""

    # debug variables
    failed_urls = []
    missing_fields = {}

    # extraction rules to be run on the job page itself
    parse_job_rules = {}

    # fields scraped even on raw mode
    raw_fields = ['referencenumber', 'url']
    time_limit = None
    subspider_detector= False
    
    def _set_config(self, **kwargs):
        super(ATSSpider2, self)._set_config(**kwargs)

        self.start_urls.append(kwargs.get('url', '') + self.url_fragmentanchor)

        if hasattr(self, 'allowed_domain_by_netloc') and self.allowed_domain_by_netloc:
            self.allowed_domains.append(urlsplit(kwargs.get('url', '')).netloc)

        try:
            self.debug = int(kwargs.get('debug', '0'))
        except ValueError:
            raise CloseSpider('You have to provide an integer value as debug parameter.')

        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_closed (self, spider):
        """ Call when a spider quits"""
        pass

    def extract_from_rule(self, loader=None, rule=None, response=None, *args, **kwargs):

        if not rule:
            return None

        if not loader:
            raise CloseSpider('extract_from_rule must include a loader')

        if response is None:
            response = loader.selector.response

        for ex in arg_to_iter(rule.get('xpath')):
            for xpath in arg_to_iter(ex.get('xpaths')):
                temp = loader.get_xpath(
                    xpath,
                    *arg_to_iter(ex.get('processors')),
                    re=ex.get('re')
                )
                if temp:
                    return temp

        for default in arg_to_iter(rule.get('value')):
            for val in arg_to_iter(default.get('values')):
                temp = loader.get_value(
                    val,
                    *arg_to_iter(default.get('processors')),
                    re=default.get('re')
                )
                if temp:
                    return temp

        for default in arg_to_iter(rule.get('responseurl')):
            temp = loader.get_value(
                response.url,
                *arg_to_iter(default.get('processors')),
                re=default.get('re')
            )
            if temp:
                return temp

        if callable(rule.get('function')):
            function = rule.get('function')
            temp = function(self, loader.selector, response, *args, **kwargs)
            if temp:
                return temp

        return rule.get('static')

    @validate(errorstrings=item_error_messages)
    def parse_job(self, response):
        """ Scrape job details and returns all the fields found. """
        self.set_meta_language(response)

        loader = BrightcorpItemLoader(selector=Selector(response))

        for field in self.parse_job_rules:
            loader.add_value(
                field,
                self.extract_from_rule(loader, self.parse_job_rules.get(field))
            )

        # load item between stages
        loader.load_item()
        custom_items = response.meta.get('custom_items', {})
        for field, custom_item in custom_items.iteritems():
            value = loader.item.get(field)
            # prioritize extracted values on the job page over custom items
            if not value and custom_item:
                loader.add_value(field, custom_item)

        # load item between stages
        loader.load_item()
        if not loader.item.get('url'):
            loader.add_value('url', response.url)

        if not loader.item.get('date'):
            loader.add_value('date', str(datetime.now()))

        if self.language:
            loader.add_value('language', self.language)

        yield loader.load_item()

    @validate(item_error_messages, 'referencenumber')
    def parse_raw(self, response):
        """ Extract raw data from the response.

        @scrapes mining_job_id iteration url raw_html encoding_scrapy_guess
                 encoding_headers encoding_body_declared encoding_body_inferred
                 referencenumber
        """
        self.set_meta_language(response)

        loader = BrightcorpItemLoader(selector=Selector(response))

        for field in self.raw_fields:
            loader.add_value(
                field,
                self.extract_from_rule(loader, self.parse_job_rules.get(field))
            )

        loader.add_value(None, {
            'mining_job_id': self.mining_job_id,
            'iteration': self.iteration,
            'raw_html': self.get_raw_page(response),
            'encoding_scrapy_guess': response.encoding,
            'encoding_headers': response._headers_encoding(),
            'encoding_body_declared': response._body_declared_encoding(),
            'encoding_body_inferred': response._body_inferred_encoding(),
        })

        custom_items = response.meta.get('custom_items', {})
        if custom_items:
            for field, value in custom_items.iteritems():
                loader.add_value(field, value)

        if not loader.item.get('url'):
            loader.add_value('url', response.url)

        if self.language:
            loader.add_value('language', self.language)

        yield loader.load_item()

    def parse_job_callback(self):
        if self.extract == '1':
            callback = lambda response: self.parse_job(response)
        else:
            callback = lambda response: self.parse_raw(response)

        return callback

    def set_meta_language(self, response):
        sel = Selector(response)

        language_sources = [
            "//html/@lang",
            "//meta[contains(@http-equiv, 'anguage')]/@content",
            "//meta[contains(@http-name, 'anguage')]/@content",
            "//@xml:lang"
        ]

        for source_path in language_sources:
            language = sel.xpath(source_path)
            if language:
                # extract the language part of a locale string
                self.language = language.extract()[0].split('-')[0]
                self.language = self.language.strip("\n")
                break

    def get_raw_page(self, response):
        """ Extract the whole page. """
        return response.body
