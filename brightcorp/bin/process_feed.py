#!/usr/bin/env python
""" Process input URLs feed, filters out duplicates, checks dead links
"""
import sys

import requests

try:
    input_feed = sys.argv[1]
    output_feed = sys.argv[2]
except Exception:
    print "Usage: %s <input feed> <output feed>" % sys.argv[0]
    sys.exit()

urls_list = []
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:11.0) Gecko/20100101 Firefox/11.0"
}

SKIP_URLS = [
    "https://icims.com/",
    "https://www2.icims.com/",
    "https://www3.icims.com/",
    "https://taleo.net/",
]

with open(input_feed) as fin:
    with open(output_feed, "w") as fout:
        for url in fin:
            url = url.strip()
            url = url.replace("http://", "https://")
            url = url.replace("//www.", "//")
            if not url in urls_list and not url in SKIP_URLS:
                try:
                    print "Open %s" % url
                    response = requests.get(url, allow_redirects=True, headers=headers)
                    if response.status_code != 200:
                        print "Received %s status, skip %s" % (response.status_code, url)
                        continue
                except Exception:
                    # requests lib can't handle expired SSL certs
                    print "Can't check %s" % url

                urls_list.append(url)

        fout.write('\n'.join(urls_list))
