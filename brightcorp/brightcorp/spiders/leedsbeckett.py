"""
scrapy crawl leedsbeckett -a url="https://vacancies.leedsbeckett.ac.uk"
"""
from brightcorp.base.atsspiders import ATSSpider
from brightcorp.items import BrightcorpItemLoader
from scrapy.http import FormRequest
from scrapy.http import Request

class LeedsBeckett(ATSSpider):

    name = 'leedsbeckett'

    def parse(self, response):
    	
      yield FormRequest(url="https://vacancies.leedsbeckett.ac.uk/trenprod_webrecruitment/wrd/run/ETREC105GF?USESSION=0C8FF60419CC11E6B6A0F7269FB6B9A1&WVID=7412577lKO&LANG=USA",
      formdata={'%25.OUTER_DIV.DIV.1':'',
           ' %25.VAC_SRCHUSP.DUMMY.1-1':'',
            'SEARCH_TYPE.VAC_SRCHUSP.DUMMY.1-1':'',
            'HF_PREF_LST.VAC_SRCHUSP.DUMMY.1-1':'',
            'WVID.VAC_SRCHUSP.DUMMY.1-1':'7412577lKO',
            'NEW_REC_I.VAC_SRCHUSP.DUMMY.1-1':'',
            'DUM_LOCN_LIST.VAC_SRCHUSP.DUMMY.1-1':'',
            'JOB_TITLE.VAC_SRCHUSP.DUMMY.1-1':'',
            'KEYWORDS.VAC_SRCHUSP.DUMMY.1-1':'',
            'SALARY_BAND.VAC_SRCHUSP.DUMMY.1-1':'',
            'REGION_ID.VAC_SRCHUSP.DUMMY.1-1':'',
            'LOCATION_ID.VAC_SRCHUSP.DUMMY.1-1':'',
            'VAC_TYPES.VAC_SRCHUSP.DUMMY.1-1':'',
            'ORDER_BY.VAC_SRCHUSP.DUMMY.1-1':'VACANCY_D',
            'RESULTS_PP.VAC_SRCHUSP.DUMMY.1-1':'',
            'BU_SEARCH.FRM_BUTTON.ET_BASE.1-1':'Search',
            '%25.FRM_BUTTON.ET_BASE.1-1':'',
            'HID_UUID.STD_HID_FLDS.ET_BASE.1-1':'0CB3D0BA-19CC-11E6-B6A0-F7269FB6B9A1',
            'HID_RESUBMIT.STD_HID_FLDS.ET_BASE.1-1':'0CBFA232-19CC-11E6-B6A0-F7269FB6B9A1',
            'HID_LOGIN_OK_I.STD_HID_FLDS.ET_BASE.1-1':'',
            'WVID.STD_HID_FLDS.ET_BASE.1-1':'7412577lKO',
            '%25.STD_HID_FLDS.ET_BASE.1-1':'',
            '%25.OUTER_DIV.DIV.1':'' },
      callback=self.parse_job) 
       

    def parse_job(self, response):
    	print "sgdfgsjZhjasshghb"
    	links = response.xpath("//h2/a/@href").extract()
    	for link in links:
            link = "https://vacancies.leedsbeckett.ac.uk/trenprod_webrecruitment/wrd/run/" + link
            yield Request(url = link ,callback =self.parse_details)

    def parse_details(self,response):
        # print "response",response.body

        title = response.xpath('//dl/dt[contains(text(),"title")]/following-sibling::dd[1]/text()').extract()
        print "title",title
        loader = BrightcorpItemLoader(response=response)
        loader.add_xpath('title', '//dl/dt[contains(text(),"title")]/following-sibling::dd[1]/text()')
        loader.add_xpath('date','//dl/dt[contains(text(),"posted")]/following-sibling::dd[1]/text()')
        loader.add_xpath('referencenumber', '//dl/dt[contains(text(),"reference")]/following-sibling::dd[1]/text()')
        loader.add_value('url', response.url)
        loader.add_value('company', '')
        loader.add_value('company_description', '')
        loader.add_xpath('location', '//dl/dt[contains(text(),"Location")]/following-sibling::dd[1]/text()')
        loader.add_xpath('zip_code', '//td//text()')
        loader.add_xpath('description', '//dl/dt[contains(text(),"description")]/following-sibling::dd[1]//text()')
        loader.add_xpath('jobcategory', '//dl/dt[contains(text(),"category/type")]/following-sibling::dd[1]/text()')
        loader.add_value('jobtype', '')
        loader.add_value('org_name', '')
        loader.add_value('apply_url', response.url)
        loader.add_xpath('salaryCurrency','//dl/dt[contains(text(),"Salary")]/following-sibling::dd[1]/text()')
        loader.add_xpath('expiration_date','//dl/dt[contains(text(),"closing")]/following-sibling::dd[1]/text()')

        return loader.load_item()
