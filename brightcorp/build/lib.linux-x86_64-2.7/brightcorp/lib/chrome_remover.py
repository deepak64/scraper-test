import lxml.html
import lxml.etree

class ChromeRemover(object):
    '''
        Remove common elements ("chrome") from a list of raw html strings
        Authors: arucker@linkedin.com, gwintrob@linkedin.com
    '''

    def __init__(self, raw_html = []):
        ''' Attempt to parse the raw html strings '''
        self.parsed_html = []
        self.chrome = []

        for html in raw_html:
            try:
                self.parsed_html.append(lxml.html.fromstring(html))
            except:
                pass

    def run(self):
        self.remove_chrome(self.parsed_html)
        self.remove_chrome(self.parsed_html, True)
        return self.parsed_html

    def remove_chrome(self, elements, reverse = False):
        contents = self.get_contents(elements)

        # Use DFS to traverse down the tree and evaluate if sub-elements are exact matches
        if all(len(c) > 0 for c in contents):
            min_length = min(len(c) for c in contents)
            for index in range(min_length):
                children = map(lambda x:x[index], contents)
                if reverse:
                    children = map(lambda x:x[-index], contents)
                self.remove_chrome(children)

        # Get contents again in case children have been removed
        contents = self.get_contents(elements)

        if all(len(c) == 0 for c in contents):
            current_element = elements[0]
            if self.same_elements(elements, current_element):
                self.chrome.extend([current_element])
                for element in elements:
                    element.getparent().remove(element)

    # Given an HTML element, returns the HTML sub-elements (not including text within the parent element)
    @staticmethod
    def get_contents(elements):
        contents = []
        for e in elements:
            contents.extend([[c for c in list(e)]])
        return contents

    # Checks if all elements are identical to comparison
    @staticmethod
    def same_elements(elements, comparison):
        if all(ChromeRemover.same_element(e, comparison) for e in elements):
            return True
        return False

    @staticmethod
    def same_element(element, comparison):
        if element.tag == comparison.tag and element.attrib == comparison.attrib and element.text == comparison.text:
            return True
        return False
