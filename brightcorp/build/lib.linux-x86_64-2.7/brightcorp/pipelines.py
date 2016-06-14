import json
import time
import urllib
import socket
import requests
import hmac, hashlib, base64

from datetime import datetime

import zmq
import msgpack
context = zmq.Context()
zmq_socket = context.socket(zmq.REQ)
zmq_socket.connect("ipc:///tmp/pipeline")


hostname = socket.gethostname()


import urllib2

class PrePostPipeline(object):

    def open_spider(self, spider):
        if hasattr(spider, 'management_node') and spider.management_node != "":
            api_query = "/api/v1/mining-job/start"
            if spider.preview == 1:
                api_query = "/api/v1/temp-job/start"
            elif spider.aggregator == 1:
                api_query = "/api/v1/aggregator-job/start"
            elif spider.autocrawl == 1:
                api_query = "/api/v1/autocrawl/start"

            tempdata = {}
            tempdata['mining_job_id'] = spider.mining_job_id
            tempdata['iteration'] = spider.iteration
            tempdata['extract'] = spider.extract
            tempdata['spidername'] = spider.name
            tempdata['start_url'] = spider.start_urls[0]
            tempdata['on_demand'] = spider.on_demand
            if hasattr(spider, 'site_id'):
                tempdata['site_id'] = spider.site_id

            self.call_api(spider, api_query, tempdata, start=True)


    def start_spider(self, data, url, token):
        """send the start to the mgm node"""
        try:
            request = urllib2.Request(url, data)
            request.add_header("Authorization", "Basic %s" % token)
            resp = urllib2.urlopen(request)
            response = resp.read()
            response_code = resp.getcode()
        except:
            time.sleep(3)
            self.start_spider(data, url, token)


    def close_spider(self, spider):
        if hasattr(spider, 'management_node') and spider.management_node != "":
            api_query = "/api/v1/mining-job/stop"
            tempdata = {}

            if spider.preview == 1:
                api_query = "/api/v1/temp-job/stop"
            elif spider.aggregator == 1:
                api_query = "/api/v1/aggregator-job/stop"
            elif spider.autocrawl == 1:
                api_query = "/api/v1/autocrawl/stop"
                tempdata['end_message'] = spider.end_message
                spider.set_output_config()
                tempdata['output_config'] = spider.output_config

            tempdata['mining_job_id'] = spider.mining_job_id
            tempdata['iteration'] = spider.iteration
            tempdata['spidername'] = spider.name
            tempdata['start_url'] = spider.start_urls[0]
            tempdata['on_demand'] = spider.on_demand
            if hasattr(spider, 'site_id'):
                tempdata['site_id'] = spider.site_id

            self.call_api(spider, api_query, tempdata)


    def call_api(self, spider, api_query, tempdata, start=False):

        str_job_data = encoded_dict(tempdata)
        str_job_data['key'] = hostname

        str_job_data_json_64 = clean_64(json.dumps(str_job_data).encode('base64'))
        digest = hmac.new(hashlib.sha1(str_job_data['key'] + "bright1234").hexdigest(), msg = str_job_data_json_64, digestmod=hashlib.sha256).digest()
        signature = clean_64(base64.b64encode(digest).decode())

        post_stuff = {}
        post_stuff['key'] = str_job_data['key']
        post_stuff['signed_request'] =  signature + "." + str_job_data_json_64
        data = urllib.urlencode(post_stuff)

        #api_url = spider.protocol + "://" + spider.management_node + api_query
        api_url = "http://internal-private-forager-403834374.us-west-1.elb.amazonaws.com/" + api_query
        base64string = base64.encodestring('%s:%s' % (spider.username, spider.password)).replace('\n', '')

        if start:
            self.start_spider(data, api_url, base64string)
        else:
            zmq_socket.send(msgpack.dumps({'data':data,
                                           'url': api_url,
                                           'type': 'api',
                                           'sign': base64string,
                                           'scrape_id': spider.mining_job_id}))
            zmq_socket.recv()


class PHPPipeline(object):

    def __init__(self):
        self.items_scraped = 0

    def __del__(self):
        zmq_socket.close()

    def process_item(self, item, spider):
        item.setdefault('date', str(datetime.now()))
        item.setdefault('mining_job_id', spider.mining_job_id)
        item.setdefault('spidername', spider.name)
        item.setdefault('iteration', spider.iteration)
        item.setdefault('on_demand', spider.on_demand)
        if hasattr(spider, 'site_id'):
            item.setdefault('site_id', spider.site_id)

        if not item.get('location') and item.get('zip_code'):
            item['location'] = item['zip_code']

        if spider.language:
            item.setdefault('language', spider.language)

        if spider.management_node != "":

            api_query = ("/api/v1/rpc/job" if hasattr(spider, 'extract') and spider.extract == "1" else "/api/v1/rpc/raw")
            if spider.preview == 1:
                api_query = ("/api/v1/rpc/temp-job" if hasattr(spider, 'extract') and spider.extract == "1" else "/api/v1/rpc/temp-raw")
            elif spider.aggregator == 1:
                api_query = "/api/v1/aggregator-job/item"
            elif spider.autocrawl == 1:
                api_query = "/api/v1/autocrawl/item"

            str_job_data = encoded_dict(item)
            str_job_data['key'] = hostname

            str_job_data_json_64 = clean_64(json.dumps(str_job_data).encode('base64'))
            digest = hmac.new(hashlib.sha1(str_job_data['key'] + "bright1234").hexdigest(), msg = str_job_data_json_64, digestmod=hashlib.sha256).digest()
            signature = clean_64(base64.b64encode(digest).decode())

            post_stuff = {}
            post_stuff['key'] = str_job_data['key']
            post_stuff['signed_request'] = signature + "." + str_job_data_json_64
            data = urllib.urlencode(post_stuff)
            base64string = base64.encodestring('%s:%s' % (spider.username, spider.password)).replace('\n', '')

            zmq_socket.send(msgpack.dumps({'data':data,
                                       'url': 'http://internal-private-forager-403834374.us-west-1.elb.amazonaws.com/' + api_query,
                                       'type': 'job',
                                       'sign': base64string,
                                       'scrape_id': spider.mining_job_id}))
            zmq_socket.recv()
        return item



def clean_64(str_input):
    return str_input.replace('+', '-').replace('/', '_').replace('\n', '')


def encoded_dict(in_dict):
    out_dict = {}

    if 'encoding_body_inferred' in in_dict:
        enc = in_dict['encoding_body_inferred']
    else:
        enc = 'utf-8'

    for k, v in in_dict.iteritems():
        if isinstance(v, str):
            if not isinstance(v, unicode):
                v = unicode(v, enc)
            v = v.encode('utf-8')
        out_dict[k] = v
    return out_dict
