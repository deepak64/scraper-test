"""
scrapy crawl cvmail_uk -a extract=1 -a url="https://fsr.cvmailuk.com/nortonrosefulbright/"

Seed URL:
    https://fsr.cvmailuk.com/nortonrosefulbright/
    https://fsr.cvmailuk.com/dacb/


There are 2 seed urls, spider must be compatible to those 2 seed urls.
"""

# import modules here
from brightcorp.base.atsspiders import ATSSpider
from brightcorp.items import BrightcorpItemLoader
from scrapy.http import Request
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
import time


class CVMailUK(ATSSpider):

    name = 'cvmail_uk'
    company = ''

    def __init__(self, *args, **kwargs):
        super(CVMailUK, self).__init__(*args, **kwargs)
        # pass


    def parse(self, response):

        links = response.xpath('//tr[@class="odd"]/td/a/@href').extract()
        # print links
        for l in links:
            l="https://fsr.cvmailuk.com/nortonrosefulbright/"+l
            l="https://fsr.cvmailuk.com/nortonrosefulbright/main.cfm?page=jobSpecific&jobId=29485&rcd=1484516&queryString="
            yield Request(url=l,callback=self.parse_job)
        # jobs list page
        pass

    def parse_job(self, response):
        print "response.url----",response.url
        """
        Extract all required information.
        """
        # title=response.xpath('//td//text()').extract()
   
        sel = Selector(response)

        loader = BrightcorpItemLoader(selector=sel)
        loader.add_xpath('title','//tr/td[contains(text(),"Job Title")]/following-sibling::td[2]/text()')
        loader.add_xpath('location','//tr/td[contains(text(),"Job Location")]/following-sibling::td[2]/text()')
        loader.add_xpath('jobcategory','//tr/td[contains(text(),"Job Category")]/following-sibling::td[2]/text()')
        loader.add_xpath('description','//tr[td[contains(text(),"Description")]]/following-sibling::tr//text()')
        
        details=sel.xpath('//tr[td[contains(text(),"Description")]]/following-sibling::tr//text()').extract()
        details="".join(details).upper()
        jobtype=[]
        jobtype_list=["FULL TIME","PART TIME"]
        for jt in jobtype_list:
            if jt in details.upper():
                jobtype.append(jt)
                break

        loader.add_value('date',time.strftime("%Y/%m/%d"))
        loader.add_value('expiration_date','')
        loader.add_value('referencenumber','')
        loader.add_value('url',response.url)
        loader.add_value('apply_url',response.url)
        loader.add_value('org_name','')
        loader.add_value('zip_code','')
        loader.add_value('company','Norton Rose Fulbright')
        loader.add_value('company_description','')
        loader.add_value('jobtype',jobtype)
 
        
       

        # print jobtype
        # print description
        # print location
        # print title
        # print jobcategory
        # print date
        # print url

        return loader.load_item()
         
        # load all required data, i.e title, description, etc
