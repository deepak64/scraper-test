#!/usr/bin/env python
"""
Christophe Boudet 2014
Linkedin

Asynchronous consumer for Scrapy Pipepline
"""


# Pool size per scraper
from time import time


POOL_SIZE = 15
# Pool size for closing operations
POOL_CLOSE_SIZE = 100

from gevent import monkey, subprocess


monkey.patch_all()

import zmq.green as zmq
import json
import gevent
import msgpack
import logging
import zlib
from gevent.pool import Pool
import sys

import urllib2

logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s',
                    level=logging.DEBUG, stream=sys.stdout)

KILL_CMD = 'pgrep -f "mining_job_id=%s" | xargs kill -9 '

# maximum amount of time since a job was last seen for a mining task.
MAX_AGE_SECONDS = 30 * 60
KILL_JOBS_INTERVAL_SECONDS = 60


class JobStats(object):
    def __init__(self, mining_job_id):
        self.last_seen = time()
        self.mining_job_id = mining_job_id
        self.attempts_to_kill = 0

    def __str__(self):
        return "JobStats(mining_job=%s, last_seen=%s, age_seconds=%s)" % (self.mining_job_id, self.last_seen,
                                                                          time() - self.last_seen)
    def __repr__(self):
        return self.__str__()

    def update(self):
        self.last_seen = time()

    def maybe_kill(self):
        if time() - self.last_seen > MAX_AGE_SECONDS:
            return self._kill()
        return False

    def _kill(self):
        try:
            self.attempts_to_kill += 1
            kill_result = subprocess.check_output(KILL_CMD % self.mining_job_id, shell=True)
            logging.info("Killed mining task %s with result %s" % (self.mining_job_id, kill_result))
            return True
        except Exception as e:
            logging.error("Unable to kill mining_job %s" % self.mining_job_id, exc_info=e)
            return False


class Consumer:

    def __init__(self):
        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("ipc:///tmp/pipeline")
        self.pools = {}
        self.pool_close = Pool(POOL_CLOSE_SIZE)
        # dictionary to hold stats about running scrapy jobs
        self.job_stats = {}
        self.last_processed_stale_jobs = time()

    def post(self, url, data, token, attempt=0, compress=False):
        """post a job"""
        if False and attempt > 3:
            # for now we retry forever
            logging.error('FAILED ATTEMPTS EXCEEDED data=%s token=%s' % (data, token))
            return
        try:
            headers = {'Authorization': 'Basic %s' % token}
            raw_data = data
            if compress:
                headers['Content-Encoding'] = 'deflate'
                data = zlib.compress(data)
            request = urllib2.Request(url, data, headers)

            resp = urllib2.urlopen(request)
            response = resp.read()
            response_code = resp.getcode()
            content = json.loads(response)
            if not ('success' in content and content['success']):
                logging.warning('MGM FAILED response_code=%s raw_data=%s content=%s ' %
                                (response_code, raw_data, content))
                if ('error_message' in content and 'Duplicate entry' in content['error_message'].get('exception', '')):
                    logging.warning('DUPLICATE content=%s' % content)
                gevent.sleep(3)
                self.post(url, raw_data, token,
                          attempt=attempt+1, compress=compress)
        except urllib2.URLError as e:
            response = e.reason
            logging.error('HTTP ERROR error=%s reason=%s raw_data=%s' % (e, response, raw_data))
            if 'Signature is invalid' in response:
                logging.error('Invalid signature')
            gevent.sleep(3)
            self.post(url, raw_data, token,
                      attempt=attempt+1, compress=compress)
        except Exception as e:
            logging.error('POST ERROR type=%s error=%s raw_data=%s' % (type(e), e, raw_data))
            gevent.sleep(3)
            self.post(url, raw_data, token, attempt=attempt+1, compress=compress)

    def close(self, msg):
        """close a scraper to Forager"""
        sid = msg['scrape_id']
        if sid in self.pools:
            self.pools[sid].join()
        logging.info('job posting done msg=%s' % msg)
        gevent.sleep(3)
        self.post(msg['url'],
                  msg['data'],
                  msg['sign'])
        logging.info('close spider post done msg=%s' % msg)
        # remove the pool from the dict
        if sid in self.pools:
            self.pools.pop(sid, None)

    def run(self):
        """consume"""
        while True:
            msg_ser = self.socket.recv()
            self.check_for_stale_jobs()
            msg = msgpack.loads(msg_ser)
            sid = msg['scrape_id']
            if msg['type'] == 'api':
                # Close
                logging.info('closing msg=%s' % msg)
                self.pool_close.spawn(self.close, msg)
                gevent.sleep(0)
                self.socket.send('')
                self.job_stats.pop(sid, None)
            else:
                # Job
                # Create the pool if new
                if sid not in self.pools:
                    self.pools[sid] = Pool(POOL_SIZE)
                    self.job_stats[sid] = JobStats(sid)
                self.pools[sid].spawn(self.post,
                                      msg['url'],
                                      msg['data'],
                                      msg['sign'],
                                      attempt=0, compress=True)
                self.job_stats[sid].update()

                self.socket.send('')
                gevent.sleep(0)

    def check_for_stale_jobs(self):
        # if we have been blocked on the spawn for a while, then all the jobs
        # will look stale even if the crawl is working
        # If we haven't processed any jobs we could just set all mining job last_seen the current time.
        # For now we don't do that since the forager watch process isn't aware of a blocker and will
        # still try to cancel these tasks.
        cur_time = time()
        """
        if cur_time - self.last_processed_stale_jobs > MAX_AGE_SECONDS:
            self.last_seen = cur_time
            map(lambda x: x.update(), self.job_stats.values())
        """
        # every 60 seconds attempt to kill stale jobs
        if cur_time - self.last_processed_stale_jobs > KILL_JOBS_INTERVAL_SECONDS:
            logging.info("Looking for stale jobs")
            for stat in self.job_stats.values():
                if stat.maybe_kill():
                    logging.warn("Killed job %s" % stat.mining_job_id)
                    self.job_stats.pop(stat.mining_job_id, None)
                elif self.job_stats[stat.mining_job_id].attempts_to_kill > 3:
                    logging.error("Unable to kill job %s after 4 attempts" % stat.mining_job_id)
                    self.job_stats.pop(stat.mining_job_id, None)
            self.last_processed_stale_jobs = cur_time


if __name__ == '__main__':
    c = Consumer()
    c.run()
