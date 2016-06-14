Feedwizard Scrapers
=======

### After creating a scraper

Don't forget to add a new guesser for the spider in scraper-ui repository. The guesser class if found at `application/models/guesser.php`

The spiders use [Scrapy](http://scrapy.org).

### Running tests

A limited number of spiders have `unittest` tests in the `brightcorp/test/spiders/` directory. For example:

    python -m unittest brightcorp.test.spiders.test_autocrawl

### Robots.txt

The [robotparser](https://github.com/brightjobs/scraper/blob/master/brightcorp/brightcorp/lib/robotparser.py) determines whether we can scrape a site according to its robots.txt.
This code is translated to JavaScript in the [Robots Tester chrome extension](https://gitli.corp.linkedin.com/gwintrob/robots-tester) and [Dharma](https://github.com/brightjobs/dharma).
Please propagate any changes to those repos.

### Deployment

See [go/foragerdeploy](http://go/foragerdeploy).

#### To check disk space of mining nodes

    ansible scraper -m shell -a df -i /scraper-ui/tmp/scraper.hosts

#### Delete logs
    for ip in `cat /scraper-ui/tmp/scraper.hosts`; do ssh -t $ip "sudo rm -rf /var/log/scrapyd/brightcorp/*"; done
