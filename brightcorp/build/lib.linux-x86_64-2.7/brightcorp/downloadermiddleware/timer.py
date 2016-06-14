"""
Downloader middleware for logging request timing
@author: gwintrob@linkedin.com
"""

from time import time

import logging

class TimerMiddleware(object):

    def __init__(self):
        self._log = logging.getLogger(self.__class__.__name__)

    def process_request(self, request, spider):
        request.meta['start_time'] = time()
        return None

    def process_response(self, request, response, spider):
        request.meta['end_time'] = time()
        request_time = request.meta['end_time'] - request.meta['start_time']
        self._log.info("TimerEvent,request=%s,time=%.2f", request, request_time)
        return response
