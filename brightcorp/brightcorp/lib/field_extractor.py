import lxml.html
import lxml.etree

class FieldExtractor(object):

    def __init__(self, html, skip_tags = [], parsed_html = None):
        ''' Attempt to parse the raw html string '''

        self.skip_tags = skip_tags
        self.parsed_html = None
        self.html_tree = None

        try:
            if parsed_html:
                self.parsed_html = parsed_html
            else:
                self.parsed_html = lxml.html.fromstring(html)

            self.html_tree = lxml.etree.ElementTree(self.parsed_html)
        except:
            pass

    def iterate_html(self):
        ''' Generator to yield elements in the parsed html tree '''

        if self.parsed_html is not None:
            for element in self.parsed_html.iter():
                if element.tag in self.skip_tags:
                    continue

                try:
                    text = element.text_content()
                    html_string = lxml.html.tostring(element)
                    xpath = self.html_tree.getpath(element)
                    result = {
                        'text': text,
                        'html_string': html_string,
                        'xpath': xpath
                    }
                    yield result
                except ValueError:
                    continue

    def calculate_score(self, element):
        ''' Attempt to extract the field from the given html element and assign a score'''

        raise NotImplementedError()

    def extract(self):
        ''' Iterate through the html tree and process each element '''

        results = []
        for element in self.iterate_html():
            result = self.calculate_score(element)
            if result and result.has_key('score'):
                results.append(result)

        if len(results) > 0:
            return max(results, key=lambda x: x['score'])
        else:
            return None

