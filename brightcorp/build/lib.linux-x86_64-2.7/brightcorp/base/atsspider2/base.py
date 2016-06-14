from scrapy.spiders import Spider
from scrapy.exceptions import CloseSpider
from scrapy.conf import settings


class ATSBaseSpider(Spider):
    aggregator = 0
    autocrawl = 0
    on_demand = 0
    name = None
    allowed_domains = []
    start_urls = []
    #expected_job_count = 'Not specified' # default value for the expected job count stat
    DEFAULT_EXPECTED_JOB_COUNT = "Not specified"
    _expected_job_count = DEFAULT_EXPECTED_JOB_COUNT # default value for the expected job count stat
    _expected_job_count_set = False

    def __init__(self, *args, **kwargs):
        Spider.__init__(self)

        self._set_config(**kwargs)

    def _set_config(self, **kwargs):
        self.mining_job_id = kwargs.get('mining_job_id', '99999')

        self.iteration = kwargs.get('iteration', '1')

        self.management_node = kwargs.get('management_node', '')

        self.username = kwargs.get('username', '')

        self.password = kwargs.get('password', '')

        self.protocol = kwargs.get('protocol', 'http')

        self.extract = kwargs.get('extract', '0')

        self.on_demand = kwargs.get('on_demand', '0')

        try:
            self.preview = int(kwargs.get('preview', 0))
        except ValueError:
            raise CloseSpider("You have to provide an integer value as preview parameter.")

        try:
            self.maxjobs = int(kwargs.get('maxjobs', '1'))
        except ValueError:
            raise CloseSpider("You have to provide an integer value as maxjobs parameter.")

        try:
            self.maximum_try = int(kwargs.get('maximum_try', '0'))
        except ValueError:
            raise CloseSpider("You have to provide an integer value as maximum_try parameter.")

        try:
            # Obey robots.txt by default
            settings.overrides['ROBOTSTXT_OBEY'] = int(kwargs.get('robots_obey', '1'))
        except ValueError:
            raise CloseSpider("You have to provide an integer value as robots_obey parameter.")

        try:
            # Enable cookies by default
            settings.overrides['COOKIES_ENABLED'] = int(kwargs.get('cookies', '1'))
        except ValueError:
            raise CloseSpider("You have to provide an integer value as cookies parameter.")

    def parse_job(self, response):
        pass

    def parse_raw(self, response):
        pass

    @property
    def expected_job_count_set(self):
        return self._expected_job_count_set

    @property
    def expected_job_count(self):
        return self._expected_job_count

    @expected_job_count.setter
    def expected_job_count(self, value):
        self._expected_job_count = value
        self._expected_job_count_set = True