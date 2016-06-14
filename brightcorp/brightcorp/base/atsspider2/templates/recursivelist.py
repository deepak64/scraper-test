from scrapy.selector import Selector
from scrapy.http import FormRequest
from scrapy.exceptions import CloseSpider
from scrapy.utils.misc import arg_to_iter
from scrapy.loader import ItemLoader

from brightcorp.base.atsspider2.templates import SimpleList
from brightcorp.lib.utils import validate


class ATSSpider2_RecursiveList(SimpleList):
    '''
    Exetends the SimpleList templates by adding another set of rules called `recursive`

    condition - rule that returns whether or not there is a next page
    url - rule that returns the url of the next page
    formdata -  rule that returns the formdata for the pagination FormRequest
    dont_filter/dont_click/from_response - rules that determine whether to enable these options for the recursive request.

    parse_job_index_rules = [{
        ...
        ...
        'recursive': {
            'condition': {
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
        for job in super(ATSSpider2_RecursiveList, self).parse_job_index(response):
            yield job

        if self.ruleindex is None:
            raise CloseSpider('No jobs found.')

        sel = Selector(response)
        sel.remove_namespaces()

        loader = ItemLoader(selector=sel)

        rule = arg_to_iter(self.parse_job_index_rules)[self.ruleindex].get('recursive')

        if rule is None:
            raise CloseSpider('parse_job_index_rules has no recursive rules')

        if self.extract_from_rule(loader, rule.get('condition')):
            if self.extract_from_rule(loader, rule.get('from_response', {'static': False})):
                url = self.extract_from_rule(loader, rule.get('url'))
                if url:
                    yield FormRequest.from_response(
                        response,
                        url=url,
                        formdata=self.extract_from_rule(loader, rule.get('formdata')),
                        callback=self.parse_job_index,
                        dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False})),
                        dont_click=self.extract_from_rule(loader, rule.get('dont_click', {'static': False}))
                    )
                else:
                    yield FormRequest.from_response(
                        response,
                        formdata=self.extract_from_rule(loader, rule.get('formdata')),
                        callback=self.parse_job_index,
                        dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False})),
                        dont_click=self.extract_from_rule(loader, rule.get('dont_click', {'static': False}))
                    )
            else:
                yield FormRequest(
                    url=self.extract_from_rule(loader, rule.get('url')),
                    formdata=self.extract_from_rule(loader, rule.get('formdata')),
                    callback=self.parse_job_index,
                    dont_filter=self.extract_from_rule(loader, rule.get('dont_filter', {'static': False}))
                )