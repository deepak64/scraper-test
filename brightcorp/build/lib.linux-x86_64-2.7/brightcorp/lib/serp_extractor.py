import json
import re
import lxml.html
import lxml.etree
from lxml.cssselect import CSSSelector

# TODO: Support xpath selectors
class SerpExtractor(object):

    REQUIRED_EXTRACTION_FIELDS = [
        'serp_job_link',
        'serp_location'
    ]

    EXTRACTION_FIELDS = [
        'serp_expected_job_count',
        'serp_job_link',
        'serp_company',
        'serp_title',
        'serp_location',
        'serp_salary'
    ]

    def __init__(self, html, options):
        if 'config' in options:
            self.config = json.loads(options['config'])
        else:
            self.config = {}

        try:
            self.parsed_html = lxml.html.fromstring(html)
            self.html_tree = lxml.etree.ElementTree(self.parsed_html)
        except:
            pass

    # Extract the expected job count from the SERP if the config includes a selector
    def extract_expected_job_count(self):
        items = [item for item in self.config if item.get('id') == 'serp_expected_job_count']

        if len(items) == 1:
            selector = items[0].get('selector')
            try:
                elements = self.parsed_html.cssselect(selector)
            except:
                elements = []

            if len(elements) > 0:
                value = elements[0].text_content()
                if value:
                    sub_re = re.compile(r'[^\d]')
                    numbers = [int(sub_re.sub('',  n)) for n in re.findall(r'[.,\d]+', value)]
                    return max(numbers)

        return 0

    # Update job details page requests from a SERP with related data
    def update_request(self, request):
        meta = {}

        for item in [item for item in self.config if item.get('id') in self.REQUIRED_EXTRACTION_FIELDS]:
            field = item.get('id')
            selector = item.get('selector')

            if field and selector:
                elements = self.parsed_html.cssselect(selector)
                if len(elements) > 0:
                    if field == 'serp_job_link':
                        value = elements[0].get('href')
                    else:
                        value = elements[0].text_content()  # TODO: Element joining

                    if value:
                        meta[field] = value

        if len(meta) == len(self.REQUIRED_EXTRACTION_FIELDS) and meta['serp_job_link'] == request.url:
            for key in meta:
                request.meta[key] = meta[key]

'''
    def generate_pair(self, selector1, selector2):
        """generate a pair of element selected via the selectors"""
        csssel1 = CSSSelector(selector1)
        csssel2 = CSSSelector(selector2)
        return zip(csssel1(self.parsed_html), csssel1(self.parsed_html))

    @staticmethod
    def get_intersection(pair):
        """get the dom intersection"""
        paths = []
        sorted_paths = []
        for el1, el2 in pair:
            a = list(el1.iterancestors())
            b = list(el2.iterancestors())
            a.reverse()
            b.reverse()
            i = 0
            local = []
            while i < min(len(a), len(b)) and a[i].tag == b[i].tag and \
                            a[i].attrib == b[i].attrib:
                name = a[i].tag
                if 'class' in a[i].attrib:
                    name += '.'+'.'.join(a[i].attrib['class'].split(' '))
                local.append(name)
                i += 1
            paths.append(set(local))
            sorted_paths.append(local)
        intersection = set.intersection(*paths)
        return (intersection, sorted_paths[0][::-1])

    @staticmethod
    def test_selector(sel, html, expected):
        """test the selector"""
        found = CSSSelector(sel)
        if len(set(found(html))) == expected:
            return True

    def __extract_container(self, sel1, sel2):
        pair = self.generate_pair(sel1, sel2)
        (intersection, sorted_paths) = self.get_intersection(pair)
        for el in sorted_paths:
            if el in intersection:
                if self.test_selector(el, self.html, len(pair)):
                    return el

    def extract(self):
        orig = self.selectors[0]
        i = 1
        while i < len(self.selectors):
            orig = self.__extract_container(orig, self.selectors[i])
            i += 1
        return orig
'''
