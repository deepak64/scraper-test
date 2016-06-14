import ngram
import string
import csv
import urllib2

LOCATIONS_URL = 'https://bright-forager.s3.amazonaws.com/autocrawl/top_raw_locations_us_500.csv'
TITLES_URL = 'https://bright-forager.s3.amazonaws.com/autocrawl/top_titles_us_500.csv'

# TODO: Dynamically tune these parameters
def locations_parser():
    locations = _load_csv_list(LOCATIONS_URL)
    return ngram.NGram(
        items = locations,
        N = 3,
        iconv = string.lower,
        threshold = 0.2
    )

def titles_parser():
    titles = _load_csv_list(TITLES_URL)
    return ngram.NGram(
        items = titles,
        N = 5,
        iconv = string.lower,
        threshold = 0.2
    )


def _load_csv_list(url):
    ''' Fetch csv from S3 url '''

    response = urllib2.urlopen(url)
    csv_reader = csv.reader(response)
    return [row[0] for row in csv_reader]
