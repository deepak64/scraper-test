import urllib,urllib2
import socket
import json
import time
import zlib

from datetime import datetime

import logging

_log = logging.getLogger('vagrantpipeline')

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

            self.call_api(spider, api_query, tempdata)

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

    def call_api(self, spider, api_query, tempdata):
        import hmac, hashlib, base64

        str_job_data = encoded_dict(tempdata)
        str_job_data['key'] = socket.gethostname()

        str_job_data_json_64 = clean_64(json.dumps(str_job_data).encode('base64'))
        digest = hmac.new(hashlib.sha1(str_job_data['key'] + "bright1234").hexdigest(), msg = str_job_data_json_64, digestmod=hashlib.sha256).digest()
        signature = clean_64(base64.b64encode(digest).decode())

        post_stuff = {}
        post_stuff['key'] = str_job_data['key']
        post_stuff['signed_request'] =  signature + "." + str_job_data_json_64
        data = urllib.urlencode(post_stuff)

        api_url = spider.protocol + "://" + spider.management_node + api_query
        request = urllib2.Request(api_url, data)
        base64string = base64.encodestring('%s:%s' % (spider.username, spider.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)

        _log.info('API URI: ' + api_url)

        maximum_try = int(spider.maximum_try) if int(spider.maximum_try) > 0 else spider.settings.get('MAXIMUM_TRY')
        tries = 0
        while True:
            tries += 1
            try:
                resp = urllib2.urlopen(request)
                response = resp.read()
                response_code = resp.getcode()
                content = json.loads(response)

                if 'success' in content and content['success']:
                    _log.info('Success: PrePostPipeline Item: %s' % tempdata)
                    break
                elif 'success' in content and content['success'] == False:
                    _log.info('Request went through but failed: PrePostPipeline Item: %s' % tempdata)
                    break

            except urllib2.HTTPError, e:
                _log.critical('The server couldn\'t fulfill the request.' + str(spider.management_node))
                _log.critical('Error code: ' + str(e.code))
                _log.critical('Error message: %s' % e.msg)
                _log.critical('Request Data: %s' % request.data)
                _log.critical('Request URL: %s' % request._Request__original)
                _log.critical('Request Headers: %s' % request.headers)
                _log.critical('Response Headers: %s' % e.headers)
                _log.critical('Response Body: %s' % e.fp.read())
            except urllib2.URLError, e:
                _log.critical('We failed to reach a server.' + str(spider.management_node))
                _log.critical('Reason: ' + str(e.reason))
                _log.critical('Request Data: %s' % request.data)
                _log.critical('Request URL: %s' % request._Request__original)
                _log.critical('Request Headers: %s' % request.headers)
            if tries >= maximum_try:
                _log.info('Item: %s' % tempdata)
                _log.critical('Exceeded the maximum (' + str(maximum_try) +') tries')
                break

            mdelay = tries * spider.settings.get('BACKOFF')

            _log.info("%d : Retrying in %d seconds..." % (tries, mdelay))

            time.sleep(mdelay)

class PHPPipeline(object):

    def __init__(self):
        self.items_scraped = 0
        pass

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
            import hmac, hashlib, base64

            api_query = ("/api/v1/rpc/job" if hasattr(spider, 'extract') and spider.extract == "1" else "/api/v1/rpc/raw")
            if spider.preview == 1:
                api_query = ("/api/v1/rpc/temp-job" if hasattr(spider, 'extract') and spider.extract == "1" else "/api/v1/rpc/temp-raw")
            elif spider.aggregator == 1:
                api_query = "/api/v1/aggregator-job/item"
            elif spider.autocrawl == 1:
                api_query = "/api/v1/autocrawl/item"

            str_job_data = encoded_dict(item)
            str_job_data['key'] = socket.gethostname()

            str_job_data_json_64 = clean_64(json.dumps(str_job_data).encode('base64'))
            digest = hmac.new(hashlib.sha1(str_job_data['key'] + "bright1234").hexdigest(), msg = str_job_data_json_64, digestmod=hashlib.sha256).digest()
            signature = clean_64(base64.b64encode(digest).decode())

            post_stuff = {}
            post_stuff['key'] = str_job_data['key']
            post_stuff['signed_request'] =  signature + "." + str_job_data_json_64
            data = urllib.urlencode(post_stuff)

            # begin log compression tracking
            compressed_data = zlib.compress(data)
            old_size = len(data.encode('utf-8'))
            new_size = len(compressed_data)
            ratio = float(new_size)/old_size
            msg = 'Compressing data: old size: %s new size: %s compression: %s' % (old_size, new_size, ratio)
            spider.log(msg, level=logging.DEBUG)
            # end log compression tracking
            #spider.management_node = '192.168.101.101'
            if spider.debug_id:
                api_query = api_query + '?XDEBUG_SESSION_START=' + spider.debug_id
            request = urllib2.Request(spider.protocol + "://" + spider.management_node + api_query, zlib.compress(data))
            request.add_header('Content-Encoding', 'deflate')
            base64string = base64.encodestring('%s:%s' % (spider.username, spider.password)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
            if spider.debug_id:
                request.add_header('Cookie', 'XDEBUG_SESSION=' + spider.debug_id)

            maximum_try = int(spider.maximum_try) if int(spider.maximum_try) > 0 else spider.settings.get('MAXIMUM_TRY')
            tries = 0
            while True:
                tries += 1
                try:
                    resp = urllib2.urlopen(request)
                    response = resp.read()
                    if spider.preview == 1:
                        content = json.loads(response)
                        if 'success' in content and content['success']:
                            self.items_scraped += 1
                            if (int(spider.maxjobs) < self.items_scraped):
                                # raise DropItem('%s - %s - Exceeded number of items to preview' % (spider.name, self.items_scraped))
                                spider.crawler.engine.close_spider(spider, 'preview_only')
                    break
                except urllib2.HTTPError, e:
                    _log.critical('The server couldn\'t fulfill the request.' + str(spider.management_node))
                    _log.critical('Error code: ' + str(e.code))
                    _log.critical('Error message: %s' % e.msg)
                    _log.critical('Request Data: %s' % request.data)
                    _log.critical('Request URL: %s' % request._Request__original)
                    _log.critical('Request Headers: %s' % request.headers)
                    _log.critical('Response Headers: %s' % e.headers)
                    _log.critical('Response Body: %s' % e.fp.read())
                except urllib2.URLError, e:
                    _log.critical('We failed to reach a server.' + str(spider.management_node))
                    _log.critical('Reason: ' + str(e.reason))
                    _log.critical('Request Data: %s' % request.data)
                    _log.critical('Request URL: %s' % request._Request__original)
                    _log.critical('Request Headers: %s' % request.headers)

                if tries >= maximum_try:
                    _log.critical('Exceeded the maximum (' + str(maximum_try) +') tries')
                    break

                mdelay = tries * spider.settings.get('BACKOFF')

                _log.info("%d : Retrying in %d seconds..." % (tries, mdelay))

                time.sleep(mdelay)

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
