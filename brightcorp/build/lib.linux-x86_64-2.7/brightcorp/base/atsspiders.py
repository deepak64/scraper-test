""" Base spider for ATS
"""
import collections
import logging
import urllib
import re
import urlparse
from datetime import datetime

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.selector import Selector
from scrapy.spiders import CrawlSpider
from scrapy.exceptions import DropItem, CloseSpider
from scrapy.conf import settings

from brightcorp.items import BrightcorpItemLoader, BrightcorpItem
from brightcorp.lib.utils import validate
from brightcorp.lib.autoextraction import get_emails, get_logos, get_salaries, get_websites, get_body_text

from hdrh.histogram import HdrHistogram

RE_PATTERN = {
    'language': re.compile('^.{0,2}')
}


RequestMock = collections.namedtuple('RequestMock', ['meta'])


class ATSSpider(CrawlSpider):
    """ This is base spider
    """
    mining_job_id = "99999"
    site_id = "0"
    start_urls = []
    preview = 0
    aggregator = 0
    autocrawl = 0
    iteration = "1"
    management_node = ""
    username = ""
    password = ""
    proxy = ""
    extract = "0"
    maxjobs = 0
    el_raw_html = '.' # default root element
    language = ''
    protocol = 'http'
    maximum_try = 0
    allowed_domains = [] # initialize list of domain allowed to crawl
    allowed_domain_bynetloc = False # if True, append URL netloc to allowed_domains
    url_fragmentanchor = "" # append fragment or anchor
    on_demand = 0 #flg is on_demand was sent via scheduling
    stale_limit = 0
    debug_id = None

    extract_logo = True
    extract_email = True
    extract_salary = True
    extract_website = True
    disable_default_field_extractors = False

    # histogram to track time spent parsing jobs in milliseconds. 1% precision for values from 1 to 5000.
    job_parsing_histogram = HdrHistogram(1, 5 * 1000, 2)

    DEFAULT_EXPECTED_JOB_COUNT = "Not specified"
    _expected_job_count = DEFAULT_EXPECTED_JOB_COUNT # default value for the expected job count stat
    _expected_job_count_set = False

    loader = {}
    default_job_field_getters = {}

    download_delay = 0 # default value for download delay
    required_fields = ['title', 'description', 'referencenumber', 'location', 'url', 'company']
    time_limit = None

    subspider_detector= False # check if spider running by a subspider_detector
    items_scraped_count = 0 # scraped item count for subspider_detector
    max_items_count = 0 # max item count to be checked from subspider_detector
    valid_spider = False # if the url is valid or not for the spider
    # seperate required fild for subspider detector
    subspider_detect_fields = ['title', 'description', 'referencenumber', 'location']
    valid_job_count = 0 # jobs having all fields in the subspider_detect_fields

    body_text = ""

    # limit for the max number of industry codes and functions
    # this should always be an integer or the code will break
    max_industry_codes = 3
    max_functions = 3

    def __init__(self, *args, **kwargs):
        CrawlSpider.__init__(self)
        if 'mining_job_id' in kwargs:
            self.mining_job_id = kwargs['mining_job_id']
        if 'site_id' in kwargs:
            self.site_id = kwargs['site_id']
        if 'preview' in kwargs:
            self.preview = 1
        if 'iteration' in kwargs:
            self.iteration = kwargs['iteration']
        if 'management_node' in kwargs:
            self.management_node = kwargs['management_node']
        if 'username' in kwargs:
            self.username = kwargs['username']
        if 'password' in kwargs:
            self.password = kwargs['password']
        if 'proxy' in kwargs:
            self.proxy = kwargs['proxy']
        if 'robots_obey' in kwargs:
            settings.set('ROBOTSTXT_OBEY', int(kwargs['robots_obey']), priority='cmdline')
        if 'url' in kwargs:
            self.start_urls.append(kwargs['url'] + self.url_fragmentanchor)
        if 'extract' in kwargs:
            self.extract = kwargs['extract']
        if 'maxjobs' in kwargs:
            self.maxjobs = int(kwargs['maxjobs'])
        if 'protocol' in kwargs:
            self.protocol = kwargs['protocol']
        if 'maximum_try' in kwargs:
            self.maximum_try = kwargs['maximum_try']
        if 'on_demand' in kwargs:
            self.on_demand = kwargs['on_demand']
        if 'debug_id' in kwargs:
            self.debug_id = kwargs['debug_id']
        if 'stale_limit_seconds' in kwargs:
            self.stale_limit = int(kwargs['stale_limit_seconds'])
        if 'subspider_detector' in kwargs:
            self.subspider_detector = True
            self.required_fields = self.subspider_detect_fields
            # Sending max items to be scraped.
            if 'max_items_count' in kwargs:
                self.max_items_count = int(kwargs['max_items_count'])
                # set spider_valid_cutoff, default 80 percent of max_items_count
                spider_valid_cutoff = kwargs.get("valid_cutoff")
                if spider_valid_cutoff:
                    self.spider_valid_cutoff = int(spider_valid_cutoff)
                else:
                    self.spider_valid_cutoff = int(self.max_items_count * 0.8)

                # this will reduce extra requstes after a close_spider call
                settings.overrides['CONCURRENT_REQUESTS'] = 1

        self.debug = int(kwargs.get('debug', '0'))
        if 'download_delay' in kwargs or hasattr(self, 'download_delay'):
            download_delay = float(kwargs.get('download_delay', getattr(self, 'download_delay', 0)))
            settings.set('DOWNLOAD_DELAY', download_delay, priority='cmdline')
            if download_delay > 0:
                settings.set('AUTOTHROTTLE_ENABLED', True, priority='cmdline')
        if self.allowed_domain_bynetloc:
            self.allowed_domains.append(urlparse.urlparse(kwargs['url']).netloc) # set list of domain allowed to crawl

        self.default_job_field_getters.update({
                                               'url': lambda self, response, item: response.url,
                                               'date': lambda self, response, item: datetime.now().strftime('%Y/%m/%d'),
                                               'language': lambda self, response, item: self.language if hasattr(self, 'language') else None
                                               })
        if self.extract_logo:
            self.default_job_field_getters.update({'autoextracted_logo_urls': self.get_logos})
        if self.extract_email:
            self.default_job_field_getters.update({'autoextracted_emails': self.get_emails})
        if self.extract_salary:
            self.default_job_field_getters.update({'autoextracted_salaries': self.get_salaries})
        if self.extract_website:
            self.default_job_field_getters.update({'autoextracted_company_websites': self.get_websites})
        self.default_fields = self.default_job_field_getters.keys()
        self.validate_parse_job_wrapper = validate(fields_to_check=self.required_fields)(type(self).parse_job_wrapper)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def parse_raw(self, response):
        """ This function parses a response.

        @scrapes mining_job_id, site_id, iteration, url, raw_html, encoding_scrapy_guess, encoding_headers, encoding_body_declared, encoding_body_inferred
        """
        msg = self.validate_parse_job(response)
        if msg:
            raise DropItem(msg)

        sel = Selector(response)
        self.loader = BrightcorpItemLoader(selector=sel)

        self.loader.add_value('mining_job_id', self.mining_job_id)
        self.loader.add_value('site_id', self.site_id)
        self.loader.add_value('iteration', self.iteration)
        self.loader.add_value('url', response.url)
        self.loader.add_value('raw_html', response.body)
        self.loader.add_value('encoding_scrapy_guess', response.encoding)
        self.loader.add_value('encoding_headers', response._headers_encoding())
        self.loader.add_value('encoding_body_declared', response._body_declared_encoding())
        self.loader.add_value('encoding_body_inferred', response._body_inferred_encoding())

        self.set_custom_item(response)

        yield self.loader.load_item()

    def validate_parse_job(self, response):
        pass

    def set_custom_item(self, response):
        pass

    #@set_job_defaults()
    def parse_job_wrapper(self, response):
        if self.maxjobs and self.crawler.stats.get_value('item_scraped_count') >= self.maxjobs:
            item_count = self.crawler.stats.get_value('item_scraped_count')
            raise CloseSpider("Closing spider since it has already crawled %s items and has a limit of %s" % (item_count, self.maxjobs))

        start_time = datetime.now()

        # we set defaults here instead of in wrapper so it's more explicit
        if self.extract_default_fields(response) and (self.extract_email or self.extract_salary or self.extract_website):
            self.body_text = get_body_text(response)

        item = self.parse_job(response)
        if isinstance(item, collections.Iterator):
            for i in item:
                yield self._set_item_defaults(i, response)
        else:
            yield self._set_item_defaults(item, response)

        end_time = datetime.now()
        parse_time = end_time - start_time
        parse_time_ms = parse_time.total_seconds() * 1000
        self.job_parsing_histogram.record_value(parse_time_ms)

    def _set_item_defaults(self, item, response):
        if self.extract_default_fields(response) and isinstance(item, BrightcorpItem):
            getters = self.default_job_field_getters
            fields = self.default_fields
            # note that we are opting to directly set the fields on the item
            # which bypasses item processors. we could copy data into a new item loader
            # if we want processors.
            for field in filter(lambda k: k not in item and k in getters, fields):
                item.setdefault(field, getters[field](self, response, item))
            # validate some fields
            ref_num = item.get('referencenumber')
            if ref_num and len(ref_num) > 50:
                self.crawler.stats.inc_value('invalid_reference_number_too_long')
                if not self.management_node:
                    raise DropItem('Dropping item since the reference number of %s chars is too long %s' % (
                        len(ref_num), ref_num))
        return item

    def parse_job_callback(self):
        if self.extract == "1":
            callback = lambda response: self.parse_job_wrapper(response) if not self.debug else self.validate_parse_job_wrapper(self, response)
        else:
            callback = lambda response: self.parse_raw(response)

        return callback

    def set_meta_language(self, response):
        """ Set site meta language. """
        sel = Selector(response)

        language = ""
        if sel.xpath("//html/@lang"):
            language = sel.xpath("//html/@lang")
        elif sel.xpath("//meta[contains(@http-equiv, 'anguage')]/@content"):
            language = sel.xpath("//meta[contains(@http-equiv, 'anguage')]/@content")
        elif sel.xpath("//meta[contains(@http-name, 'anguage')]/@content"):
            language = sel.xpath("//meta[contains(@http-name, 'anguage')]/@content")
        elif sel.xpath("//@xml:lang"):
            language = sel.xpath("//@xml:lang")

        if language:
            # extract first two char and assign as meta language
            self.language = RE_PATTERN['language'].search(language.extract()[0]).group()

    def add_get_parameter(self, url, params):
        """ Append additional GET query parameters to given URL.

        :param url: URL to append parameters to
        :param params: GET parameters as name-value pairs
        """
        if isinstance(params, dict): params = params.items()
        if isinstance(params, tuple): params = list(params)

        (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
        query = urllib.urlencode(dict(urlparse.parse_qsl(query) + params))

        return urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    def spider_closed(self, spider):
        """ Call when a spider quits. """
        total_time = 0
        for item in self.job_parsing_histogram.get_recorded_iterator():
            total_time += item.count_added_in_this_iter_step * item.value_iterated_to
        total_count = self.job_parsing_histogram.get_total_count()
        avg_time = total_time / total_count if total_count > 0 else 0
        self.log('Total parsing time: %sms' % str(total_time), level=logging.INFO)
        self.log('Average parsing time: %sms' % str(avg_time), level=logging.INFO)
        self.log('50th percentile parsing time: %sms' % (str(self.job_parsing_histogram.get_value_at_percentile(50))),
                 level=logging.INFO)
        self.log('90th percentile parsing time: %sms' % str(self.job_parsing_histogram.get_value_at_percentile(90)),
                 level=logging.INFO)

    def validate_item_fields(self, item):
        # default item validation
        return [f for f in self.required_fields if not item.get(f)]

    @property
    def expected_job_count_set(self):
        return self._expected_job_count_set

    @property
    def expected_job_count(self):
        return self._expected_job_count

    def extract_default_fields(self, response):
        return not (self.disable_default_field_extractors or isinstance(response, RequestMock))

    @expected_job_count.setter
    def expected_job_count(self, value):
        self._expected_job_count = value
        self._expected_job_count_set = True

    def get_logos(self, that, response, item):
        return get_logos(response)

    def get_emails(self, that, response, item):
        return get_emails(self.body_text)

    def get_salaries(self, that, response, item):
        return get_salaries(self.body_text)

    def get_websites(self, that, response, item):
        return get_websites(response, self.body_text)
