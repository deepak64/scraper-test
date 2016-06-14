import urlparse
import urllib
from datetime import datetime
from functools import wraps

from scrapy.exceptions import DropItem, CloseSpider
from scrapy.utils.misc import arg_to_iter
from scrapy.item import Item
from scrapy.selector import Selector
from brightcorp.items import BrightcorpItem
from types import GeneratorType

class MissingJobField(Exception):
    """Drop a job that is missing a required field"""
    def __init__(self, field, url):
        super(Exception, self).__init__()
        self.reason = 'Missing required field %s for job.\n URL: %s' % (field, url)

def get_hidden_inputs(response):
    """ Get hidden inputs. """
    formdata = {}
    sel = Selector(response)

    for hid in sel.xpath('//input[@type="hidden" and @name and @value]'):
        formdata[hid.xpath('@name').extract()[0]] = hid.xpath('@value').extract()[0]

    return formdata

def extract_first(sel, default=[], re=None):
    v = sel.extract()
    if not re:
        return v[0] if v else default
    if v:
        # Compile regex just in case it is not compiled
        regex = compile(re).search(v[0])
        if regex:
            return regex.group(1)
    return default

def add_get_params(url, params):
    """ Append additional GET query parameters to given URL.

    :param url: URL to append parameters to
    :param params: GET parameters as name-value pairs
    """
    if isinstance(params, dict): params = params.items()
    if isinstance(params, tuple): params = list(params)

    (scheme, netloc, path, query, fragment) = urlparse.urlsplit(url)
    query = urllib.urlencode(dict(urlparse.parse_qsl(query) + params))

    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))

def set_job_defaults(fields=['url', 'date', 'language'],
                     getters={}):
    """
    Set some default values on a job if we determine that they aren't already set
    """
    getters.update({'url': lambda self, response: response.url,
                    'date': lambda self, response: datetime.now().strftime('%Y/%m/%d'),
                    'language': lambda self, response: self.language if hasattr(self, 'language') else None
                    })
    def decorator(func):
        @wraps(func)
        def wrapper(self, response):
            item = func(self, response)
            if isinstance(item, GeneratorType):
                item = next(item)
            if isinstance(item, BrightcorpItem):
                # note that we are opting to directly set the fields on the item
                # which bypasses item processors. we could copy data into a new item loader
                # if we want processors.
                for field in filter(lambda k: k not in item and k in getters, fields):
                    v = getters[field](self, response)
                    if v:
                        item[field] = v
            return item
        return wrapper
    return decorator

def validate(errorstrings=None, fields_to_check=None):
    """
    Check if the status code is >=400 or the body contains an error message.

    :param errorstrings: error messages to be checked in response.body

    Usage::
        @validate(['No jobs found', 'No trabajos'])
        def parse(self, repsonse):
            # do stuff

        @validate(['Position has been filled'])
        def parse_raw(self, response):
            # do stuff

        @validate(['Position has been filled'])
        def parse_job(self, response):
            # do stuff
    """
    if errorstrings is None:
        errorstrings = []
    if fields_to_check is None:
        fields_to_check = ['title', 'description', 'referencenumber', 'location', 'url']

    def decorator(func):
        @wraps(func)
        def wrapper(self, response):
            if not hasattr(self, 'debug'):
                self.debug = False
            if self.debug:
                if not hasattr(self, 'failed_urls'):
                    self.failed_urls = []
                if not hasattr(self, 'missing_fields'):
                    self.missing_fields = {}
                self.crawler.stats.set_value('DEBUG MODE', 'TRUE')

            result = func(self, response)
            for result in arg_to_iter(func(self, response)):
                if isinstance(result, Item):
                    exception = DropItem
                else:
                    exception = CloseSpider

                if response.status >= 400 or any(error in response.body for error in errorstrings):
                    if self.debug:
                        self.crawler.stats.inc_value('DEBUG: failed_urls_count')
                        self.failed_urls.append(response.url)
                        self.crawler.stats.set_value(
                            'DEBUG: failed_urls', self.failed_urls)
                    if exception == DropItem:
                        self.crawler.stats.inc_value('items_dropped_count')
                    if response.status >= 400:
                        raise exception(
                            'Status Code Error: %s\nURL: %s'
                            % (response.status, response.url))
                    else:
                        errors = [error for error in errorstrings if error in response.body]
                        raise exception(
                            'Response Body Error: %s\nURL: %s'
                            % (', '.join(errors), response.url))
                    yield None

                if isinstance(result, Item):
                    if self.debug:
                        job_misses_a_required_field = False
                        for field in arg_to_iter(fields_to_check):
                            if not result.get(field):
                                if field not in self.missing_fields:
                                    self.missing_fields[field] = []
                                self.missing_fields[field].append(response.url)
                                job_misses_a_required_field = True
                        for key in self.missing_fields.keys():
                            self.crawler.stats.set_value('DEBUG: missing_%s_field' % key, self.missing_fields[key])

                        if job_misses_a_required_field:
                            self.crawler.stats.inc_value(
                                'DEBUG: jobs_missing_required_field_count')

                    else:
                        if not result.get('referencenumber'):
                            self.crawler.stats.inc_value('items_dropped_count')
                            raise MissingJobField('referencenumber', response.url)

                yield result
        return wrapper
    return decorator

def is_absolute(url):
    return bool(urlparse.urlparse(url).netloc)
