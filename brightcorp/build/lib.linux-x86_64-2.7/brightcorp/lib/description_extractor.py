from field_extractor import FieldExtractor

SKIP_TAGS = ['html', 'body', 'head', 'script']

class DescriptionExtractor(FieldExtractor):

    def __init__(self, html = None, parsed_html = None):
        super(DescriptionExtractor, self).__init__(html, skip_tags=SKIP_TAGS, parsed_html=parsed_html)

    def calculate_score(self, element):
        ''' Score elements based on the ratio of text to the raw html string in an element '''

        text_length = len(element['text'])
        html_length = len(element['html_string'])

        if text_length == 0 or html_length == 0:
            return None

        # TODO: Make this smarter
        score = text_length**2 / float(html_length)

        element['score'] = score
        return element
