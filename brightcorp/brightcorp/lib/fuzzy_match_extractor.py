from field_extractor import FieldExtractor

class FuzzyMatchExtractor(FieldExtractor):
    ''' Extract title, location, etc. using a fuzzy match (e.g. ngram) text parser '''

    def __init__(self, html, parser):
        super(FuzzyMatchExtractor, self).__init__(html)
        self.parser = parser

    def calculate_score(self, element):
        ''' Use a text parser and search for the best fuzzy match in the element '''

        text = element['text']
        search = self.parser.search(text.lower())
        if len(search) > 0:
            top_search = search[0]
            element['score'] = top_search[1]
            return element
