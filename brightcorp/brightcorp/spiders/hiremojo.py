"""
scrapy crawl hiremojo -a extract=1 -a url="http://hiremojo.com/find-a-job/"
"""

# import here
from brightcorp.base.atsspiders import ATSSpider
from brightcorp.items import BrightcorpItemLoader
from scrapy.http import Request


class Hiremojo(ATSSpider):

	name = 'hiremojo'

	# def start_requests(self):
	# 	print "jzfhsdh"
	# 	self.start_urls.append("http://hiremojo.com/find-a-job/")
		

	def parse(self, response):
		print "djzkgfksjgvjbhn"
		# pass
		# parse jobs list
		# pagination

		# pages= response.xpath("//div[@class='x-paging-info']/text()").re(r'\d+')
		# pages=int(pages)
		# print pages


		# if (pages%20)==0:
		# 	pages=int(pages/20)
		# else:
		# 	pages=int(pages/20)+1



		# for i in range(0,pages,20):
		# 	yield FormRequest(url="https://hiring.accolo.com/jobseeker/job/list.htm",
		# 	formdata={'start':i,
		# 	'limit':20,
		# 	'sort':'launchDate',
		# 	'dir':'DESC'},
		# 	callback=self.parse_job) 
		pass


	def parse_job(self, response):
		print response.url
		pass
