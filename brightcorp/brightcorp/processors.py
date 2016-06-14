import re
from datetime import datetime
from urllib import urlencode,unquote
from urlparse import parse_qsl, urljoin
import ujson as json

from hashlib import md5
from lxml import html
from scrapy.utils.misc import arg_to_iter
from scrapy.utils.markup import remove_tags_with_content

STRIP_TAGS = (
    'head',
    'link',
    'meta',
    'script',
    'style',
    'title'
)


def md5_hash(values):
    """ MD5 hashes the input values"""
    if isinstance(values, basestring):
        return md5(values).hexdigest()
    return [md5(value).hexdigest() for value in values]


class Prefix(object):
    """ Prefixes each value with the given `prefix` string. """

    def __init__(self, prefix=u''):
        self.prefix = prefix

    def __call__(self, values):
        if isinstance(values, basestring):
            return self.prefix + values
        return [self.prefix + value for value in values]

class Postfix(object):
    """ Postfixes each value with the given `postfix` string. """

    def __init__(self, postfix=u'', strip=True):
        self.postfix = postfix
        self.strip = strip

    def __call__(self, values):
        if isinstance(values, basestring):
            return self._clean_value(values) + self.postfix
        return [self._clean_value(value) + self.postfix for value in values]

    def _clean_value(self, value):
        return value.strip() if self.strip else value


class RemoveBadElements(object):
    """ Removes all bad elements from a set of elements. Takes a list of strings
    that are valid HTML fragments/subtrees, removes the elements found in bad_elements, and
    converts everything back to strings for use in scrapy.

    Powered by lxml.html """

    def __init__(self, bad_elements):
        # this is a built-in list of bad tag names.
        # by default the processor will automatically search for these
        # and remove them when processing items.
        self.bad = set(["button", "script", "input",])
        if bad_elements:
            for element in bad_elements:
                self.bad.add(element)

    def remove_children(self, elem, badlist):
        """ Helper function created to keep __call__ easy to read.
        Takes two arguments, an Element object, and an iterable containing
        a list of tags.
        """
        for item in badlist:
            bad_children = elem.xpath("//%s" % item)
            if bad_children:
                for x in bad_children:
                    x.getparent().remove(x)

    def __call__(self, values):
        # first we convert the strings to Element objects
        list_of_elements = []
        for x in arg_to_iter(values):
            if not x.isspace():
                try:
                    list_of_elements.append(html.fromstring(x))
                except:
                    # invalid html(eg:comment tags)
                    pass
        # then, we go ahead and remove every higher-level 'bad' tag from the list
        processed_list = [x for x in list_of_elements if x.tag not in self.bad]
        # then we check each element for sub-elements, and
        # remove the 'bad' tags under each. this is because
        # sometimes the strings we get are full-on trees in their
        # own right, so we need to go and pick off the children
        # one by one.
        for elem in processed_list:
            # if the top level element is bad
            # we just remove it and all the children
            # should follow
            if elem.tag in self.bad:
                elem.getparent().remove(elem)
            else:
                # otherwise, we use the xpath
                # method to check if there are any
                # bad children using xpath.
                self.remove_children(elem, self.bad)

        return [html.tostring(x, encoding='unicode') for x in processed_list]


class Strip(object):
    """ Strips non-empty values using the given character list. """

    def __init__(self, chars=None):
        self.chars = chars

    def __call__(self, values):
        return [value.strip(self.chars) for value
                in arg_to_iter(values)
                if value.strip(self.chars)]


class Coalesce(object):
    """ Returns the first or last non-empty value from a list. """

    def __init__(self, last=False):
        self.index = -1 if last else 0

    def __call__(self, values):
        values = [value for value in values if bool(value)]
        return values[self.index] if len(values) > 0 else None

class NormalizedJoin(object):
    """ Strips non-empty values and joins them with the given separator. """

    def __init__(self, separator=u' ', return_list=False):
        self.separator = separator
        self.return_list = return_list

    def __call__(self, values):
        result = self.separator.join(
            [value.strip() for value in values if value and not value.isspace()])
        if self.return_list:
            return [result]
        else:
            return result

class NormalizedJoinWithoutTags(object):

    def __init__(self, separator='\n'):
        self.separator = separator

    def __call__(self, values):
        valid_values = (v for v in values if v and not v.isspace())
        result = self.separator.join(
            [strip_tags(v) for v in valid_values]
        )
        return result

class NL2BR(object):
    """ Replaces newlines with <br> tags. """

    def __call__(self, values):
        table = {'\r' : "", '\n': "<br>"}
        def translate(value):
            for from_, to in table.iteritems():
                value = value.replace(from_, to)
            return value

        if not isinstance(values, list):
            values = [values]

        return [translate(value) for value in values]


class ConvertDateString(object):
    """ Converts a date string to another format"""

    def __init__(self, informat, outformat='%m/%d/%Y'):
        self.informat=informat
        self.outformat=outformat

    def __call__(self, values):
        rvals = []
        for v in arg_to_iter(values):
            try:
                rvals.append(datetime.strptime(v.strip(), self.informat).strftime(self.outformat))
            except ValueError:
                pass
        return rvals

class ParseDate(object):
    """ Formats a date string into Python's datetime string representation. """

    def __init__(self, _format=None):
        self.format = _format

    def __call__(self, values):
        return [datetime.strptime(value.strip(), self.format) for value in values]


class Replace(object):
    """ Replaces text from each value in a list. """

    def __init__(self, regex, replacement=""):
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        self.regex = regex
        self.replacement = replacement

    def __call__(self, values):
        return [self.regex.sub(self.replacement, value) for value in arg_to_iter(values)]


class ConvertToHTMLEscape(object):
    """convert all ISO Latin-1 codes to corresponding HTML Escape codes"""
    """reference: http://www.utexas.edu/learn/html/spchar.html"""
    latin_html_map = {
        "&#8211;": "&ndash;",
        "&#8212;": "&mdash;",
        "&#8364;": "&euro;",
        "&#8220;": "&ldquo;",
        "&#8221;": "&rdquo;",
        "&#8216;": "&lsquo;",
        "&#8217;": "&rsquo;",
        "&#171;": "&laquo;",
        "&#187;": "&raquo;",
        "&#160;": "&nbsp;",
        "&#162;": "&cent;",
        "&#169;": "&copy;",
        "&#247;": "&divide;",
        "&#181;": "&micro;",
        "&#183;": "&middot;",
        "&#182;": "&para;",
        "&#177;": "&plusmn;",
        "&#163;": "&pound;",
        "&#174;": "&reg;",
        "&#167;": "&sect;",
        "&#153;": "&trade;",
        "&#165;": "&yen;",
        "&#176;": "&deg;",
        "&#225;": "&aacute;",
        "&#193;": "&Aacute;",
        "&#224;": "&agrave;",
        "&#192;": "&Agrave;",
        "&#226;": "&acirc;",
        "&#194;": "&Acirc;",
        "&#229;": "&aring;",
        "&#197;": "&Aring;",
        "&#227;": "&atilde;",
        "&#195;": "&Atilde;",
        "&#228;": "&auml;",
        "&#196;": "&Auml;",
        "&#230;": "&aelig;",
        "&#198;": "&AElig;",
        "&#231;": "&ccedil;",
        "&#199;": "&Ccedil;",
        "&#233;": "&eacute;",
        "&#201;": "&Eacute;",
        "&#232;": "&egrave;",
        "&#200;": "&Egrave;",
        "&#234;": "&ecirc;",
        "&#202;": "&Ecirc;",
        "&#235;": "&euml;",
        "&#203;": "&Euml;",
        "&#237;": "&iacute;",
        "&#205;": "&Iacute;",
        "&#236;": "&igrave;",
        "&#204;": "&Igrave;",
        "&#238;": "&icirc;",
        "&#206;": "&Icirc;",
        "&#239;": "&iuml;",
        "&#207;": "&Iuml;",
        "&#241;": "&ntilde;",
        "&#209;": "&Ntilde;",
        "&#243;": "&oacute;",
        "&#211;": "&Oacute;",
        "&#242;": "&ograve;",
        "&#210;": "&Ograve;",
        "&#244;": "&ocirc;",
        "&#212;": "&Ocirc;",
        "&#248;": "&oslash;",
        "&#216;": "&Oslash;",
        "&#245;": "&otilde;",
        "&#213;": "&Otilde;",
        "&#246;": "&ouml;",
        "&#214;": "&Ouml;",
        "&#223;": "&szlig;",
        "&#250;": "&uacute;",
        "&#218;": "&Uacute;",
        "&#249;": "&ugrave;",
        "&#217;": "&Ugrave;",
        "&#251;": "&ucirc;",
        "&#219;": "&Ucirc;",
        "&#252;": "&uuml;",
        "&#220;": "&Uuml;",
        "&#255;": "&yuml;   ",
        "&#180;": "'",
        "&#161;": "&iexcl;",
        "&#191;": "&iquest;",
        "&#96;": "'",
        "&#39;": "'",
        "&#34;": "&quot;",
        "&#38;": "&amp;",
        "&#62;": "&gt;",
        "&#60;": "&lt;",
        }

    def __call__(self, values):
        out = []
        for value in [x for x in arg_to_iter(values) if isinstance(x, basestring)]:
            for m in self.latin_html_map:
                value =  value.replace(m,self.latin_html_map[m])
            out.append(value)
        return out


class ShrinkURL(object):
    """reduce url size by removing some url query parameters"""
    def __init__(self, remove = []):
        self.remove = remove

    def __call__(self,values):
        out = []
        for value in arg_to_iter(values):
            try:
                unquoted_url = unquote(value).split("?")
                url_path, query_str = unquoted_url[0], '?'.join(unquoted_url[1:])
                query = dict(parse_qsl(query_str))
                for r in self.remove:
                    query.pop(r,"")
                if query:
                    out.append("%s?%s" % (url_path, urlencode(query)))
                else:
                     out.append(url_path)
            except Exception,e:
                out.append(value)  #cant shrink url, appending original url
        return out

class RemoveEmptyData(object):
    # Removing the empty spaces and tabs
    strip_data = Strip()
    # re to replace special characters like space and hypen ('-')
    special_chars_re = re.compile(ur'([^a-zA-Z0-9])', re.U)

    def __call__(self, values):
        output = []
        for val in arg_to_iter(values):
            val = self.remove_empty_spaces(val)
            val = self.remove_special_chars(val)
            output.extend(val)

        return val

    def remove_empty_spaces(self, value):
        """Removing extra spaces and tabs using existing Strip()"""
        return self.strip_data(value)

    def remove_special_chars(self, value):
        """Replacing all the special characters like hypen('-') and slash ('/') with space(' ') """
        return [self.special_chars_re.sub(" ", v) for v in arg_to_iter(value)]

    def remove_extra_words(self, value, remove_words=[]):
        """Removing all the extra words"""
        for temp in remove_words:
            temp = temp.lower()
            value = [v.lower().replace(temp, '') for v in arg_to_iter(value)]

        return value

class MapJobField(object):
    """
    Mapping of a job field. This processor tries to map a given value to a default linkedin value.
    Implementations should have a 'map' dictionary that is key (string) to linkedin mapping (this can be anything - depends on your map_final_data function logic).
    If a match is not found, the default behavior is to set the field value to input_string.upper().
    Note that you can modify the __call__ and map_final_data methods with custom logic.
    """
    map = {}
    empty_tags_processor = RemoveEmptyData()

    def __init__(self, remove=[], overriding_map = {}):
        if overriding_map:
            self.map = overriding_map
        self.remove = remove

    def __call__(self, values):
        output = []
        for value in arg_to_iter(values):
            value = str(value)
            value = self.remove_words(value)
            value = self.remove_empty_data(value)
            value = self.map_final_data(value)
            output.extend(value)
        return output

    def remove_words(self, value):
        return self.empty_tags_processor.remove_extra_words(value, self.remove)

    def remove_empty_data(self, value):
        """Removing Empty data"""
        return self.empty_tags_processor(value)


    def map_final_data(self, value):
        """
        Map data into the final desired format. The default behavior is to look at the map:
            1. if the value.lower() is found, add the value from the map to the array of mappings
            2. else, add value.upper() to the array of mappings
        """
        return [self.map[v.lower()] if v.lower() in self.map.keys() else v.upper() for v in arg_to_iter(value)]

class MapJobTypes(MapJobField):
    # Map jobtype if at all possible
    map = {
        'fulltime': 'FULL_TIME',
        'parttime': 'PART_TIME',
        'full time': 'FULL_TIME',
        'part time': 'PART_TIME',
        'f': 'FULL_TIME',
        'p': 'PART_TIME',
        'c': 'CONTRACT',
        't': 'TEMPORARY',
        'o': 'OTHER',
    }


class MapExperienceLevel(MapJobField):
    # Map experience levels if at all possible
    map = {
        '0': 'NOT_APPLICABLE',
        '1': 'INTERNSHIP',
        '2': 'ENTRY_LEVEL',
        '3': 'ASSOCIATE',
        '4': 'MID_SENIOR_LEVEL',
        '5': 'DIRECTOR',
        '6': 'EXECUTIVE',
    }

class MapFunctions(MapJobField):
    # Note that the functions map should always be string (function description) -> list of strings (function codes).
    # Do not alter this map. This is the official linkedin map (go/jfp for more details on the mapping).
    # If the spider needs a custom map, just call MapFunctions(overriding_map = spider_map) where spider_map is the overriding map.
    map = {
        "none": [''],
        "accounting/auditing": ['ACCT'],
        "administrative": ['ADMN'],
        "advertising": ['ADVR'],
        "analyst": ['ANLS'],
        "art/creative": ['ART'],
        "businessdevelopment": ['BD'],
        "consulting": ['CNSL'],
        "customerservice": ['CUST'],
        "distribution": ['DIST'],
        "design": ['DSGN'],
        "education": ['EDU'],
        "engineering": ['ENG'],
        "finance": ['FIN'],
        "generalbusiness": ['GENB'],
        "healthcareprovider": ['HCPR'],
        "humanresources": ['HR'],
        "informationtechnology": ['IT'],
        "legal": ['LGL'],
        "management": ['MGMT'],
        "manufacturing": ['MNFC'],
        "marketing": ['MRKT'],
        "other": ['OTHR'],
        "publicrelations": ["PR"],
        "purchasing": ['PRCH'],
        "productmanagement": ['PRDM'],
        "projectmanagement": ['PRJM'],
        "production": ["PROD"],
        "qualityassurance": ['QA'],
        "research": ['RSCH'],
        "sales": ['SALE'],
        "science": ['SCI'],
        "strategy/planning": ['STRA'],
        "supplychain": ['SUPL'],
        "training": ['TRNG'],
        "writing/editing": ['WRT']
    }

    def __call__(self, values):
        '''
        Note that for the functions map it is assumed that every element in the arguments is a string representation of a job
        function we want to map. We will iterate through all functions and set the return value to be a json array of function codes.
        '''
        functions = []
        for value in arg_to_iter(values):
            value = str(value)
            value = self.remove_words(value)
            value = self.remove_empty_data(value)
            value = self.map_final_data(value)
            if value:
                functions.extend(value)
        # Functions are a json array of function codes (pick the first 3 only)
        return [json.dumps(functions[:3])]

    def map_final_data(self, value):
        """
        Map data into the final desired format.
        Always return a list of functions (even if there is no match - return a list of [v.upper()])
        """
        functions = []
        for v in arg_to_iter(value):
            if v.lower() in self.map.keys():
                functions.extend(self.map[v.lower()])
            else:
                functions.extend([v.upper()])
        return functions


class MapIndustriesCode(MapJobField):
    # TODO - Need to add default linkedin industry codes
    map = {
        'retail': 47,
    }
    splitter = ','

    def __init__(self, remove=[], overriding_map = {}, custom_splitter=''):
        if overriding_map:
            self.map = overriding_map
        if custom_splitter:
            # sometimes we need splitter as ':'
            # defualt split ','
            self.splitter = custom_splitter
        self.remove = remove

    def __call__(self, values):
        indutries_codes = []
        # TODO - multiple string industry present
        # splitting up all values and process
        for value in arg_to_iter(values):
            value = self.string_strip(value)
            value = self.map_final_data(value)
            if value:
                indutries_codes.extend(value)

        return [json.dumps(indutries_codes[:3])]

    def string_strip(self, value):
        return value.strip()

    def map_final_data(self, value):
        indutries_codes = []
        for x in arg_to_iter(value):
            if x.lower() in self.map.keys():
                indutries_codes.extend([self.map[x.lower()]])
            else:
                indutries_codes.extend([x])
        return indutries_codes


def strip_tags(v):
    return remove_tags_with_content(v.strip(), STRIP_TAGS)


class RemoveEmptyTags(object):

    empty_tags_re = re.compile(
        r"<([a-zA-Z]*)[^>]*?>(\s|\xa0|\xc2|\&nbsp;)*</\1>"
        )

    def __call__(self, values):
        return [self.remove_tags(v) for v in arg_to_iter(values)]

    def remove_tags(self, v):
        s = self.empty_tags_re.sub('', v)
        while s != v:
            v = s
            s = self.empty_tags_re.sub('', s)
        return v


class HtmlFormatter(object):
    # Tags which will not remove,convert
    preserve_tags = ["div", "br", "p", "ul", "li", "b", "strong", "u", "i"]
    # Tags which will convert to strong
    strong_tags = ["h1", "h2", "h3", "h4", "strong", "th", "b"]
    # Tags which will convert to br
    newline_tags = ["tr", "dt"]

    # re to get all tags from raw html which are not in preseve_tags
    remove_re = re.compile("<(?!/?(?:%s)).*?>" % ("|".join(preserve_tags)), re.DOTALL)

    # re to get all opening tags to convert to strong
    bold_re = re.compile("(</?)(?:" + "|".join(["%s" % x for x in strong_tags]) + ")(?![a-zA-Z]).*?>", re.DOTALL)
    # re to get all attributes of html tags
    attr_re = re.compile("<([^>]*?) .*?>", re.DOTALL)
    # re to get all newline tags
    newline_re = re.compile("|".join(["<%s.*?>" % x for x in newline_tags]), re.DOTALL)
    # Tags which cannot be empty
    remove_empty_tags_processor = RemoveEmptyTags()
    # remove html comments
    comments_re = re.compile("<!--(.*?)-->", re.DOTALL)

    def __init__(self):
        pass

    def __call__(self, values):
        output = []
        for raw_html in arg_to_iter(values):
            raw_html = self.remove_comments(raw_html)
            raw_html = self.empty_tags(raw_html)
            raw_html = self.bold_tags(raw_html)
            raw_html = self.replace_newline(raw_html)
            # after converting tags to `strong`,`br` remove all unwanted tags
            raw_html = self.remove_tags(raw_html)
            # finally remove attributes
            raw_html = self.remove_attr(raw_html)
            output.append(raw_html)
        return output

    def remove_tags(self, raw_html):
        """all tags which are not preserved will remove, only tag is removing,
            its content will not remove"""
        return self.remove_re.sub(" ", raw_html)

    def bold_tags(self, raw_html):
        """"replace all tags in strong_tags to one single tag 'strong'"""
        return self.bold_re.sub(r"\1strong>", raw_html)

    def remove_attr(self, raw_html):
        """"Remove all tag attributes"""
        return self.attr_re.sub(r"<\1>", raw_html)

    def empty_tags(self, raw_html):
        return self.remove_empty_tags_processor.remove_tags(raw_html)

    def replace_newline(self, raw_html):
        """replace all tags in newline_tags to br"""
        raw_html = self.newline_re.sub("<br/>", raw_html)
        return raw_html

    def remove_comments(self, raw_html):
        return self.comments_re.sub(" ", raw_html)


class UrlJoin(object):
    """Wrapper for urljoin function to use with xpath"""

    def __init__(self, base_url):
        self.base_url = base_url

    def __call__(self, urls):

        out = []
        for urlval in arg_to_iter(urls):
            out.append(urljoin(self.base_url, urlval))
        return out