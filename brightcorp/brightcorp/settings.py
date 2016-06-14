import os
import logging


BOT_NAME = 'brightcorp'

SPIDER_MODULES = ['brightcorp.spiders']
NEWSPIDER_MODULE = 'brightcorp.spiders'

USER_AGENT = "LinkedInBot/1.0 (compatible; Mozilla/5.0; Jakarta Commons-HttpClient/3.1 +http://www.linkedin.com)"


COOKIES_ENABLED = True
ROBOTSTXT_OBEY = True
URLLENGTH_LIMIT = 50000

# Retry/Timeout
RETRY_ENABLED = True
RETRY_TIMES = 3
MAXIMUM_TRY = 1000
BACKOFF = 10


DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 1,
    'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
    'brightcorp.downloadermiddleware.offsite.OffsiteMiddleware': 1,
    # 'brightcorp.downloadermiddleware.timer.TimerMiddleware': 1,
    'brightcorp.middlewares.RobotsTxtMiddleware': 100,
    'brightcorp.middlewares.ProxyMiddleware': 750,
    'brightcorp.middlewares.TimeLimitMiddleware': 1,
    'brightcorp.middlewares.StaleCrawlMiddleware': 2
    # 'brightcorp.middlewares.RandomProxy': 101,
    # 'scrapy.contrib.downloadermiddleware.httpproxy.HttpProxyMiddleware': 110
}


EXTENSIONS = {
    'brightcorp.middlewares.BrightStats': 900,
    'scrapy.extensions.feedexport.FeedExporter': None
}

def file_get_contents(filename):
    with open(filename) as f:
        return f.read()

if os.path.isfile("/etc/cluster") == False or file_get_contents("/etc/cluster") == "local":
    ITEM_PIPELINES = {
        'brightcorp.vagrantpipelines.PHPPipeline': 500,
        'brightcorp.vagrantpipelines.PrePostPipeline': 500
    }
    BRIGHT_STATS='company:10,location:20,jobtype,functions'
else:
    ITEM_PIPELINES = {
        'brightcorp.pipelines.PHPPipeline': 500,
        'brightcorp.pipelines.PrePostPipeline': 500
    }
    # move main log file over to INFO and start an additional log file at level DEBUG
    PROD_RUN = True
    LOG_LEVEL = logging.INFO
    EXTENSIONS['brightcorp.middlewares.FullLogMiddleware'] = 1000


FEED_EXPORTERS = {
    'jsonlines': "brightcorp.exporters.BrightcorpItemExporter"
}
