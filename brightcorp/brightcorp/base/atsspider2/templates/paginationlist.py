from math import ceil

from scrapy.selector import Selector
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.utils.misc import arg_to_iter
from scrapy.loader import ItemLoader

from brightcorp.base.atsspider2.templates import SimpleList
from brightcorp.lib.utils import validate


class ATSSpider2_PaginationList(SimpleList):
    '''
    Exetends the SimpleList templates by adding another set of rules called `pagination`

    totalpages - rule that returns the total pages of the job index if possible
    totalitems - rule that returns the total number of items if possible
    itemsperpage - rule that returns the number of items per page if possible
    url - rule that returns the url of each page
    formdata -  rule that returns the formdata for the pagination FormRequest
    dont_filter/dont_click/from_response - rules that determine whether to enable these options for the pagination request.

    parse_job_index_rules = [{
        ...
        ...
        'pagination': {
            'totalpages': {
                'xpath': [
                    {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                ],
                'function': foo,
                'value': {
                    'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                }
            },
            'totalitems': {
                'xpath': [
                    {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                ],
                'function': foo,
                'value': {
                    'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                }
            },
            'itemsperpage': {
                'xpath': [
                    {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                ],
                'function': foo,
                'value': {
                    'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                }
            },
            'url': {
                'xpath': [
                    {'xpaths': ['xpath1', 'xpath2', 'xpath3'], 'processors': [proc1, proc2], 're': regex},
                ],
                'function': foo,
                'value': {
                    'values': 'foo', 'processors': [proc1, proc2, proc3], 're': regex
                }
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
    }]
    '''
    no_jobs_message = []

    @validate(no_jobs_message)
    def parse_job_index(self, response):
        for job in super(ATSSpider2_PaginationList, self).parse_job_index(response):
            yield job

        if self.ruleindex is None:
            raise CloseSpider('No jobs found.')

        loader = ItemLoader(selector=Selector(response))

        rule = arg_to_iter(self.parse_job_index_rules)[self.ruleindex].get('pagination')

        if rule is None:
            raise CloseSpider('parse_job_index_rules has no pagination rules')

        if rule.get('totalpages'):
            totalpages = int(self.extract_from_rule(loader, rule.get('totalpages')))
        else:
            itemsperpage = self.extract_from_rule(loader, rule.get('itemsperpage'))
            totalitems  = self.extract_from_rule(loader, rule.get('totalitems'))
            totalpages = int(ceil(float(totalitems)/float(itemsperpage)))

        for page in xrange(2, totalpages+1):
            if self.extract_from_rule(loader, rule.get('from_response', {'static': False}), page=page):
                yield FormRequest.from_response(
                    response,
                    formdata=self.extract_from_rule(loader, rule.get('formdata'), page=page),
                    callback=self.parse_job_index2,
                    dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False}), page=page),
                    dont_click=self.extract_from_rule(loader, rule.get('dont_click', {'static': False}), page=page)
                )
            else:
                yield FormRequest(
                    url=self.extract_from_rule(loader, rule.get('url'), page=page),
                    formdata=self.extract_from_rule(loader, rule.get('formdata'), page=page),
                    callback=self.parse_job_index2,
                    dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False}), page=page)
                )

    @validate(no_jobs_message)
    def parse_job_index2(self, response):
        for job in super(ATSSpider2_PaginationList, self).parse_job_index(response):
            yield job