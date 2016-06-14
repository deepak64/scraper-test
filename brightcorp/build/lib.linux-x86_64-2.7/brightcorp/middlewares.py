import re
import random
import logging
from urlparse import urlparse
from urllib import getproxies, urlopen

from scrapy import signals
from scrapy.conf import settings
from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from scrapy.exceptions import NotConfigured, IgnoreRequest
from scrapy.http import Request
from scrapy.utils.httpobj import urlparse_cached

from brightcorp.lib import robotparser, robotparser_nikkita

import time

digit_extractor = re.compile(r'\d+')

class ProxyMiddleware(HttpProxyMiddleware):
    """ Proxy midddleware child class of HttpProxyMiddleware
        See https://github.com/scrapy/scrapy/blob/master/scrapy/contrib/downloadermiddleware/httpproxy.py
    """
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        # Parent class will disable the middleware when no proxy
        # is configured in the mining node (raises NotConfigured exception)
        # Just copied the constructor code and removed the exception
        self.proxies = {}
        for key, url in getproxies().items():
            self.proxies[key] = self._get_proxy(url, key)

    def process_request(self, request, spider):
        # Accepts the following:
        # http://user:pass@192.168.1.1:80
        # http://192.168.1.1:80
        # http://192.168.1.1
        # user:pass@192.168.1.1:80
        # user:pass@192.168.1.1
        # 192.168.1.1:80
        # 192.68.1.1
        if hasattr(spider, 'proxy') and spider.proxy != "":
            proxies_dict = {}
            for proxy in spider.proxy.split(','):
                auth, url = self._get_proxy(proxy, None)
                schemes = urlparse(url).scheme
                schemes = [schemes] if schemes else ['http', 'https']

                # Proxy urls must have 'http', 'https', 'no' scheme for them to be used by scrapy
                # Default is http and https?
                for scheme in schemes:
                    if scheme in proxies_dict:
                        proxies_dict[scheme].append(tuple([auth, url]))
                    else:
                        proxies_dict.update({scheme: [tuple([auth, url])]})

            # Pick a random proxy from the ones set in scrapy command
            for scheme, proxies in proxies_dict.items():
                self.proxies.update({scheme: random.choice(proxies)})

        if self.proxies:
            # super() handles request.meta['proxy'], needs self.proxies to have values
            super(ProxyMiddleware, self).process_request(request, spider)

            self._log.info("REQUEST META: %s" % request.meta)


class RobotsTxtMiddleware(object):
    """
    This is a middleware to respect robots.txt policies. To activate it you must
    enable this middleware and enable the ROBOTSTXT_OBEY setting.
    """
    DOWNLOAD_PRIORITY = 1000

    def __init__(self, crawler):
        self._log = logging.getLogger(self.__class__.__name__)
        if not crawler.settings.getbool('ROBOTSTXT_OBEY'):
            raise NotConfigured

        self.crawler = crawler
        self._useragent = crawler.settings.get('USER_AGENT')
        self._parsers = {}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def process_request(self, request, spider):
        if request.meta.get('dont_obey_robotstxt'):
            return
        rp = self.robot_parser(request, spider)
        if rp and not rp.can_fetch(self._useragent, request.url):
            self._log.info("Forbidden by robots.txt: %s", request.url)
            self._log.debug("Robots.txt is %s", str(rp))
            raise IgnoreRequest

    def robot_parser(self, request, spider):
        url = urlparse_cached(request)
        netloc = url.netloc
        if netloc not in self._parsers:
            self._parsers[netloc] = None
            robotsurl = "%s://%s/robots.txt" % (url.scheme, url.netloc)
            if hasattr(spider, 'load_robots_separate') and getattr(spider, 'load_robots_separate'):
                self._parse_robots_txt(robotsurl, urlopen(robotsurl).readlines())
            else:
                robotsreq = Request(
                    robotsurl,
                    priority=self.DOWNLOAD_PRIORITY,
                    meta={'dont_obey_robotstxt': True}
                )
                dfd = self.crawler.engine.download(robotsreq, spider)
                dfd.addCallback(self._parse_robots)
        return self._parsers[netloc]

    def _parse_robots(self, response):
        #rp = robotparser.RobotFileParser(response.url)
        rp = robotparser_nikkita.RobotFileParserLookalike(response.url)
        rp.parse(response.body.splitlines())
        self._parsers[urlparse_cached(response).netloc] = rp

    def _parse_robots_txt(self, url, txt):
        rp = robotparser.RobotFileParser(url)
        rp.parse(txt)
        self._parsers[urlparse(url).netloc] = rp


class FullLogMiddleware(object):
    def __init__(self, crawler):
        self.crawler = crawler
        # if running in prod we also want ot start a debug level logger
        # we could consider moving this to spider_opened and spider_closed
        # that would give us access to spider.management node to verify we are on prod
        """if settings.get('PROD_RUN') and settings['LOG_FILE']:
            sflo = scrapy.log.start(settings['LOG_FILE'].replace('.log', '_full.log'),
                             scrapy.log.DEBUG, settings['LOG_STDOUT'], settings['LOG_ENCODING'],
                             self.crawler)
            crawler.signals.connect(sflo.stop, signals.engine_stopped)
        """
        if settings.get('PROD_RUN') and settings['LOG_FILE']:
            d_log_file = settings['LOG_FILE'].replace('.log', '_full.log')
            logging.info("Adding a different debug level logger at %s" % d_log_file)
            # create file handler which logs debug level to *_full.log
            d_logger = logging.FileHandler(d_log_file)
            d_logger.setLevel(logging.DEBUG)
            # create formatter with existing log setting
            formatter = logging.Formatter(settings['LOG_FORMAT'], settings['LOG_DATEFORMAT'])
            d_logger.setFormatter(formatter)
            # add the handler to the root logger
            logging.getLogger().addHandler(d_logger)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

class BrightStats(object):
    """aggregate stats about jobs scraped

        We could implement this as an extension by creating an ItemPipeline
        since for now we focus on item level pipeline.

        This approach enables more flexible logging of stats at the end.
        To cleanup keys into sub heirarchies
    """

    PATTERNS = {
                'item': re.compile('(?P<item>item)\|(?P<field>[^|]+)\|(?P<value>.+)')
                }

    ROLLUP_FIELDS = {}

    def __init__(self, stats):
        self._log = logging.getLogger(self.__class__.__name__)
        self.stats = stats

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.stats)

        # extract command line settings in format -s brightstats=key:count,key:count,key,key
        brightstats_settings = crawler.settings.get('brightstats') or crawler.settings.get('BRIGHT_STATS')
        if brightstats_settings:
            for k, _, v in [f.partition(':') for f in brightstats_settings.split(',')]:
                o.ROLLUP_FIELDS[k]= int(v) if v else -1
        o.ROLLUP_KEYS = o.ROLLUP_FIELDS.keys()
        logging.info('brightstats settings %s' % o.ROLLUP_FIELDS)

        # connect to signals
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        crawler.signals.connect(o.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(o.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(o.response_received, signal=signals.response_received)
        crawler.signals.connect(o.spider_error, signal=signals.spider_error)
        return o

    def spider_opened(self, spider):
        pass

    def spider_closed(self, spider, reason):
        # re-aggregate stats
        all_stats = spider.crawler.stats.get_stats()
        # convert all_stats fields like 'item|company|Acme = 10' and 'item|location|CA = 100' to
        # {company: {Acme: 10}, location: {CA: 100}}
        # then we can select top n by field according to ROLLUP_FIELDS dict
        item_stats = {}
        for kv in filter(None, [self.PATTERNS['item'].match(k) for k in all_stats.keys()]):
            f = kv.group('field')
            v = kv.group('value')
            if f in item_stats:
                item_stats[f][v] = all_stats[kv.string]
            else:
                item_stats[f] = {v: all_stats[kv.string]}
            del all_stats[kv.string]
        # get total uniques per tracked field
        fields = item_stats.keys()
        all_stats['item_uniques'] = {field: len(item_stats[field]) for field in fields}
        # limit some fields to just the top n results
        for field in [f for f in fields if self.ROLLUP_FIELDS.get(f, -1) > 0]:
            item_stats[field] = sorted(item_stats[field].items(),
                                          key=lambda x: x[1],
                                          reverse=True)[:10]
        all_stats['item_stats'] = item_stats
        if spider.time_limit is not None:
            all_stats['time_limit'] = spider.time_limit
        self._set_expected(all_stats, spider)
        spider.crawler.stats.set_stats(all_stats)

    def _set_expected(self, all_stats, spider):
        '''
        Get total job count stats, as reported by site
        !side-effect! modifies all_stats
        '''
        if spider.expected_job_count_set:
            ec = spider.expected_job_count
            if isinstance(ec, unicode):
                all_stats['expected_job_count'] = int(''.join([str(d) for d in digit_extractor.findall(ec)]))
            else:
                all_stats['expected_job_count'] = int(ec if isinstance(ec, int) or str(ec).isdigit()
                                                  else ''.join(digit_extractor.findall(str(ec))) or -1)

    def item_scraped(self, item, spider):
        for key in self.ROLLUP_KEYS:
            val = item.get(key)
            if not val:
                val = 'none'
            spider.crawler.stats.inc_value('item|%s|%s' % (key, val))
        missing_fields = self._validate_item_fields(item, spider)
        for field in missing_fields:
            spider.crawler.stats.inc_value('missing_field|%s' % field)
        if missing_fields:
            spider.crawler.stats.inc_value('missing_field_any')
        if spider.subspider_detector:
            # this will check each item and update the valid_spider value
            # so that subspider detector will know if this spider is valid or not
            spider.items_scraped_count += 1
            if spider.items_scraped_count <= spider.max_items_count:
                missing_fields = self._validate_item_fields(item, spider)
                if not missing_fields:
                    spider.valid_job_count = spider.valid_job_count + 1
                    if spider.valid_job_count == spider.spider_valid_cutoff:
                        spider.valid_spider = True
                        spider.crawler.engine.close_spider(
                            spider, 'closespider_valid_spider'
                            )
            elif not spider.valid_spider:
                spider.crawler.engine.close_spider(spider, 'closespider_itemcount')

    def response_received(self, spider):
        pass

    def item_dropped(self, item, spider, exception):
        pass

    def spider_error(self, failure, response, spider):
        pass

    def _validate_item_fields(self, item, spider):
        if hasattr(spider, 'validate_item_fields'):
            return spider.validate_item_fields(item)
        else:
            return []


class TimeLimitMiddleware(object):
    def process_request(self, request, spider):
        if hasattr(spider, 'end_time') and spider.end_time and time.time() > spider.end_time:
            logging.info("Canceling request due to time limit: %s", request.url)
            raise IgnoreRequest


class StaleCrawlMiddleware(object):
    """Monitors how frequently a crawler produces items and ends crawls that haven't produced jobs in a while.
    """
    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)
        self.last_seen = 0

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        # connect to signals
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider):
        if hasattr(spider, 'stale_limit') and spider.stale_limit > 0:
            self._log.info('StaleCrawlMiddleware enabled with limit seconds %d' % spider.stale_limit)
            self.last_seen = time.time()
            spider.crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        else:
            self._log.info('StaleCrawlMiddleware disabled')

    def process_request(self, request, spider):
        if self.last_seen > 0 and (time.time() - self.last_seen) > spider.stale_limit:
            self._log.info("Canceling request due to stale limit: %s", request.url)
            raise IgnoreRequest

    def item_scraped(self, item, response, spider):
        self.last_seen = time.time()

