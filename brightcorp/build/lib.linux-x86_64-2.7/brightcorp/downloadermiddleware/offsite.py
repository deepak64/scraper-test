"""
Custom offsite middleware for filtering requests
@author: gwintrob@linkedin.com
"""

import re
import scrapy.exceptions
import scrapy.signals
import scrapy.utils.httpobj
import logging

class OffsiteMiddleware(object):
    """
    Note: scrapy.contrib.spidermiddleware.offsite.OffsiteMiddleware does not
          execute soon enough, thus this DownloaderMiddleware.
    @seealso: https://github.com/scrapy/scrapy/issues/15
    """
    stats = dict()
    host_regex = None
    domains_seen = set()

    def __init__(self, stats):
        self._log = logging.getLogger(self.__class__.__name__)
        self.stats = stats

    def _get_host_regex(self, spider):
        """Override this method to implement a different offsite policy"""
        allowed_domains = getattr(spider, 'allowed_domains', ())

        if allowed_domains:
            # Example: ^(.*\.)?(example\.org|example\.com)$
            regex = r'^(.*\.)?(%s)$' % '|'.join(
                re.escape(d)
                for d in allowed_domains if d is not None)
        else:
            regex = ''

        return re.compile(regex)

    @classmethod
    def from_crawler(cls, crawler):
        o = cls(crawler.stats)
        crawler.signals.connect(o.spider_opened, signal=scrapy.signals.spider_opened)
        return o

    def spider_opened(self, spider):
        self.host_regex = self._get_host_regex(spider)

    def process_request(self, request, spider):
        # If this condition is false, we return None which allows the request
        if not request.dont_filter and not self.should_follow(request, spider):
            domain = scrapy.utils.httpobj.urlparse_cached(request).hostname
            if domain and domain not in self.domains_seen:
                self.domains_seen.add(domain)
                self._log.info("Filtered offsite request to %r: %s" % (domain, request))
                self.stats.inc_value('offsite/domains', spider=spider)
            self.stats.inc_value('offsite/filtered', spider=spider)

            raise scrapy.exceptions.IgnoreRequest()

    def should_follow(self, request, spider):
        # Only enable filtering if allow_offsite is explicitly set to 0
        if not hasattr(spider, 'allow_offsite') or spider.allow_offsite != 0:
            return True

        # hostname can be None for wrong urls (like javascript links)
        host = scrapy.utils.httpobj.urlparse_cached(request).hostname or ''
        return bool(self.host_regex.search(host))
