from itertools import izip_longest

from scrapy.selector import Selector
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.loader import ItemLoader
from scrapy.utils.misc import arg_to_iter

from brightcorp.base.atsspider2 import ATSSpider2
from brightcorp.lib.utils import validate


class ATSSpider2_SimpleList(ATSSpider2):

    no_jobs_message = []

    def _set_config(self, **kwargs):
        super(ATSSpider2_SimpleList, self)._set_config(**kwargs)

        if not hasattr(self, 'parse_job_index_rules'):
            raise CloseSpider('parse_job_index_rules not found')

        self.ruleindex = None

    def parse(self, response):
        if hasattr(self, 'handle_meta_language') and \
                self.handle_meta_language == 'header':
            self.set_meta_language(response)

        return self.parse_job_index(response)

    @validate(no_jobs_message)
    def parse_job_index(self, response):
        '''
        Parses the job list page using the rules from `self.parse_job_index_rules`

        base - xpath that selects the job item group
        joburl - rule that returns the url from the job item group
        relative - set of rules that return the specified fields from the job item group.
        nonrelative - set of rules that return the specified fields from the page that are outside the job item group but are in the same order as them.
        formdata - rule that return the formdata for the job request.
        dont_filter/dont_click/from_response - rules that determine whether to enable these options for the job request.

        ex.

        parse_job_index_rules = [
            {
                'base': xpath,
                'joburl': {
                    'xpath': [
                        {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                    ],
                    'function': foo,
                    'value': {
                        'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                    }
                },
                'relative': {
                    'title': {
                        'xpath': [
                            {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                        ],
                        'function': foo,
                        'value': {
                            'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                        }
                    },
                    ...
                    ...
                },
                'nonrelative': {
                    'title': {
                        'xpath': [
                            {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                        ],
                        'function': foo,
                        'value': {
                            'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                        }
                    },
                    ...
                    ...
                },
                'formdata': {
                    'xpath': [
                        {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                    ],
                    'function': foo,
                    'value': {
                        'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                    }
                },
                'dont_filter': {'static': False},
                'dont_click': {'static': False},
                'from_response': {'static': False}
            }
        ]
        '''
        sel = Selector(response)
        sel.remove_namespaces()

        loader = ItemLoader(selector=sel)

        for i, r in enumerate(arg_to_iter(self.parse_job_index_rules)):
            jobs = sel.xpath(r.get('base'))
            if jobs:
                self.ruleindex = i
                rule = r
                break
        else:
            rule = {}

        customitems = []

        for count in rule.get('jobcount', {}):
            self.extract_from_rule(loader, rule.get('jobcount'), response)

        for field in rule.get('nonrelative', {}):
            value = self.extract_from_rule(loader, rule.get('nonrelative').get(field), response)
            customitems.append([(field, val) for val in value])

        for ji, u in enumerate(izip_longest(jobs, *customitems, fillvalue=None)):
            jobloader = ItemLoader(selector=u[0])
            formdata = {}
            meta = {'custom_items': response.meta.get('custom_items', {})}

            for i in xrange(1, len(u)):
                meta['custom_items'][u[i][0]] = u[i][1]

            for field in rule.get('relative', {}):
                meta['custom_items'][field] = self.extract_from_rule(jobloader, rule.get('relative').get(field), response)

            if self.extract_from_rule(loader, rule.get('from_response', {'static': False}), response, jobindex=ji):
                yield FormRequest.from_response(
                    response,
                    formdata=self.extract_from_rule(jobloader, rule.get('formdata'), response, jobindex=ji),
                    callback=self.parse_job_callback(),
                    meta=meta,
                    dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False}), response, jobindex=ji),
                    dont_click=self.extract_from_rule(loader, rule.get('dont_click', {'static': False}), response, jobindex=ji)
                )
            else:
                yield FormRequest(
                    url=self.extract_from_rule(jobloader, rule.get('joburl'), response, jobindex=ji),
                    formdata=self.extract_from_rule(jobloader, rule.get('formdata'), response, jobindex=ji),
                    callback=self.parse_job_callback(),
                    meta=meta,
                    dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False}), response, jobindex=ji)
                )