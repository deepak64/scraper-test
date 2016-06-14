# -*- coding: utf-8 -*-

import re
import urlparse
from collections import OrderedDict

tlds = {"com", "org", "net", "int", "edu", "gov", "mil", "arpa", "ac", "ad", "ae", "af", "ag", "ai", "al", "am", "an",
        "ao", "aq", "ar", "as", "at", "au", "aw", "ax", "az", "ba", "bb", "bd", "be", "bf", "bg", "bh", "bi", "bj",
        "bm", "bn", "bo", "bq", "br", "bs", "bt", "bv", "bw", "by", "bz", "ca", "cc", "cd", "cf", "cg", "ch", "ci",
        "ck", "cl", "cm", "cn", "co", "cr", "cs", "cu", "cv", "cw", "cx", "cy", "cz", "dd", "de", "dj", "dk", "dm",
        "do", "dz", "ec", "ee", "eg", "eh", "er", "es", "et", "eu", "fi", "fj", "fk", "fm", "fo", "fr", "ga", "gb",
        "gd", "ge", "gf", "gg", "gh", "gi", "gl", "gm", "gn", "gp", "gq", "gr", "gs", "gt", "gu", "gw", "gy", "hk",
        "hm", "hn", "hr", "ht", "hu", "id", "ie", "il", "im", "in", "io", "iq", "ir", "is", "it", "je", "jm", "jo",
        "jp", "ke", "kg", "kh", "kh", "ki", "km", "kn", "kp", "kr", "krd", "kw", "ky", "kz", "la", "lb", "lc", "li",
        "lk", "lr", "ls", "lt", "lu", "lv", "ly", "ma", "mc", "md", "me", "mg", "mh", "mk", "ml", "mm", "mn", "mo",
        "mp", "mr", "ms", "mt", "mu", "mv", "mw", "mx", "my", "mz", "na", "nc", "ne", "nf", "ng", "ni", "nl", "no",
        "np", "nr", "nu", "nz", "om", "pa", "pe", "pf", "pg", "ph", "pk", "pl", "pm", "pn", "pr", "ps", "pt", "pw",
        "py", "qa", "re", "ro", "rs", "ru", "rw", "sa", "sb", "sc", "sd", "se", "sg", "sh", "si", "sj", "sk", "sl",
        "sm", "sn", "so", "sr", "ss", "st", "su", "sv", "sx", "sy", "sz", "tc", "td", "tf", "tg", "th", "tj", "tk",
        "tl", "tm", "tn", "tn", "to", "tp", "tr", "tt", "tv", "tw", "tz", "ua", "ug", "uk", "us", "uy", "uz", "va",
        "vc", "ve", "vg", "vi", "vn", "vu", "wf", "ws", "ye", "yt", "yu", "za", "zm", "zr", "zw"}

# looks for a portion of a salary in the format "per {time units}" or "PER {time units} or "/ time units"
per_period = r'\s?(?:\/|per|PER)\s?(?:(?!(?:per|PER)\s)[a-zA-Z][a-z]+|(?:per|PER)\s[a-zA-Z][a-z]+)'

# negative lookbehind to make sure the string doesn't start with - or to, because this would indicate that it belongs
# to a range, and we want ranges to be checked separately by the salary range regex
cannot_start_with = r'(?<!-\s)(?<!-)(?<!to)(?<!to\s)'

# negative lookahead to make sure the string doesn't end with - or to or per or ',', because this would indicate it is
# part of either a range or per period salary or could be followed by more numbers, and we want those cases to be
# checked separately by their respective regexes
cannot_end_with = r'(?!\s?(?:-|\/|to|TO|per|PER|,))'

# matches a number between 10000 to 999900, in forms such as 10000, 10,000, and 10k
num_10000_to_999900 = r'[1-9][0-9](?:[0-9]?,[0-9]0{2}|[0-9]?\s?k|[0-9]{1,2}0{2})'

# matches a number between 10 to 999900, in forms such as 10000, 10,000, and 10k
num_10_to_999900 = r'[1-9][0-9](?:[0-9]?,[0-9]0{2}|[0-9]?\s?k|[0-9]{0,4})'

# matches a number between 1 to 9999999 with up to two decimal places, in forms such as 10000, 10,000, 10k, and 10000.00
num_1_to_999999_with_decimals = r'[1-9](?:[0-9]{0,2},[0-9]0{2}|[0-9]{0,2}\s?k|[0-9]{0,5}(?:\.[0-9]{2})?)'


# salary in the format "{salary}/{time units}" or "{salary} per {time units}", ranging from 1.00 to 999999.99
salary_per_period = r'{cannot_start_with}[\$£€¥₹]\s?{num_1_to_999999_with_decimals}{per_period}'.format(cannot_start_with=cannot_start_with, num_1_to_999999_with_decimals=num_1_to_999999_with_decimals, per_period=per_period)

# salary in the format "{salary_min} - {salary_max}" or "{salary_min} to {salary_max}", with each ranging from 10000 to 999900
salary_number_range = r'(?i)[\$£€¥₹]\s?{num_10_to_999900}\s?(?:-|to)\s?(?:[\$£€¥₹]?\s?)?{num_10000_to_999900}\b{cannot_end_with}'.format(num_10_to_999900=num_10_to_999900, num_10000_to_999900=num_10000_to_999900, cannot_end_with=cannot_end_with)

# salary in the format "{salary_min} - {salary_max}/{time_units}" or "{salary_min} - {salary_max} per {time_units}", with each ranging from 1.00 to 999999.99
salary_number_range_per_period = r'[\$£€¥₹]\s?{num_1_to_999999_with_decimals}\s?(?:-|to|TO)\s?(?:[\$£€¥₹]?\s?)?{num_1_to_999999_with_decimals}{per_period}'.format(num_1_to_999999_with_decimals=num_1_to_999999_with_decimals, per_period=per_period)

# salary in the format "{salary}", ranging from 30000 to 299900
salary_single_number = r'(?i){cannot_start_with}[\$£€¥₹]\s?(?:[1-2][0-9]{{2}}|[3-9][0-9])(?:,[0-9]0{{2}}|\s?k|[0-9]0{{2}})\b{cannot_end_with}'.format(cannot_start_with=cannot_start_with, cannot_end_with=cannot_end_with)

RE_PATTERN = {
    'email': re.compile(r"\b[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+\b"),
    'salary_number_range_per_period': re.compile(salary_number_range_per_period),
    'salary_per_period': re.compile(salary_per_period),
    'salary_number_range': re.compile(salary_number_range),
    'salary_single_number': re.compile(salary_single_number),
    'website': re.compile(r"(?:http[s]?://)?(?:www.)?([\da-zA-Z\.-]+\.[a-z]{2,})")
}

def get_logos(response):
    images = response.xpath("//img[re:test(@class, 'logo', 'i') or re:test(@id, 'logo', 'i') or re:test(@src, 'logo', 'i')]/@src").extract()

    if not images:
        return []

    base = response.xpath('//base/@href').extract()
    absolute_paths = []

    for image_path in images:
        if base:
            absolute_path = urlparse.urljoin(base[0], image_path).replace("../", "")
        else:
            absolute_path = urlparse.urljoin(response.url, image_path).replace("../", "")

        if absolute_path not in absolute_paths:
            absolute_paths.append(absolute_path)

    return absolute_paths

def get_emails(body_text):
    emails = []
    for word in body_text.split(' '):
        if '@' in word:
            for email in RE_PATTERN['email'].findall(word):
                if email not in emails:
                    emails.append(email)
    return emails

def get_salaries(body_text):
    salaries = RE_PATTERN['salary_number_range_per_period'].findall(body_text) + RE_PATTERN['salary_per_period'].findall(body_text) + RE_PATTERN['salary_number_range'].findall(body_text) + RE_PATTERN['salary_single_number'].findall(body_text)
    return list(OrderedDict.fromkeys(salaries))

def get_websites(response, body_text):
    found_websites = []
    for text in body_text.split(' '):
        if '.' in text:
            found_websites.extend(RE_PATTERN['website'].findall(text))

    websites = []
    for found_site in found_websites:
        if found_site.split('.')[-1] in tlds:
            site = found_site.lower().encode('ascii', 'ignore')
            if site not in websites:
                websites.append(site)

    found_links = response.xpath('//a/@href').extract()
    for extracted_link in found_links:
        if extracted_link.startswith('http'):
            link = urlparse.urlparse(extracted_link).hostname
            if link:
                if link.startswith('www.'):
                    link = link[4:]
                if link not in websites:
                    websites.append(link)

    return websites

def get_body_text(response):
    return response.xpath("string(//body)").extract_first()