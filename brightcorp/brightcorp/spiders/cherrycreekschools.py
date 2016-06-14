"""
scrapy crawl cherrycreekschools -a extract=1 -a url="http://www.cherrycreekschools.org/Pages/default.aspx"

sample url:
    http://www.cherrycreekschools.org/Pages/default.aspx
"""

from brightcorp.base.atsspiders import ATSSpider
from brightcorp.items import BrightcorpItemLoader
from scrapy.http import Request

class CherryCreekSchools(ATSSpider):

    name = 'cherrycreekschools'

    # def start_requests(self):
    #     pass
    #     # if it needed, use it

    def parse(self, response):
        link = response.xpath('//a[@title="Current Vacancies"]/@href').re(r'(.*)\?')
        # print "link",link
        yield Request(url = link[0],callback=self.parse_job)
        # code here
        # pass

    def parse_job(self, response):
        print "response",response.url
        # title=response.xpath('//td//text()').extract()
        # print title
        loader = BrightcorpItemLoader(response=response)
        loader.add_xpath('title', '//td//text()')
        loader.add_xpath('title', '//td//text()')
        loader.add_xpath('date', '//td//text()')
        loader.add_xpath('referencenumber', '//td//text()')
        loader.add_xpath('url', '//td//text()')
        loader.add_xpath('company', '//td//text()')
        loader.add_xpath('company_description', '//td//text()')
        loader.add_xpath('location', '//td//text()')
        loader.add_xpath('zip_code', '//td//text()')
        loader.add_xpath('description', '//td//text()')
        loader.add_xpath('jobcategory', '//td//text()')
        loader.add_xpath('jobtype', '//td//text()')
        loader.add_xpath('org_name', '//td//text()')
        loader.add_xpath('apply_url', '//td//text()')

        # loader.add_xpath('title', '//td//text()')
        # loader.add_xpath('title', '//td//text()')

        return loader.load_item()
        # pass
