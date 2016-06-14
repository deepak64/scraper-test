#!/usr/bin/python
""" Custom scheduler and check errors script.
"""
import os
import sys
import optparse
from datetime import datetime

import boto
import scrapinghub

SH_APIKEY = "76c7f6ee4ef74611a9881e55191afb0e"

# Amazon SES - AWS KEY, AWS_SECRET  
SES_LOGIN = ('', '')

EMAIL_BODY = """
Hello from Scrapinghub!

Errors detected for %s spider.
Please investigate %s

Yours sincerly,
Scrapinghub team
"""

EMAIL_FROM = "Scrapinghub panel <info@scrapinghub.com>"

EMAIL_SUBJECT = "errors detected for %s spider"

ERROR_URL = "http://panel.scrapinghub.com/p/%s/jobs/logbrowser/%s/?level=error"

ERROR_CHECK_PERIOD = 2 # N hours since the job finished, if a job finished more than N hours ago - don't check it

DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

def parse_opts():
    op = optparse.OptionParser()
    op.add_option("-p", "--project", help="Project ID, required")
    op.add_option("-s", "--spider", help="Spider name, required")
    op.add_option("-m", "--mail", help="Send report email to given recepients, can be used with check_errors option", default=[], action="append")
    op.add_option("--schedule", help="Schedule a spider", default=False, action="store_true")
    op.add_option("--check_errors", help="Check errors for a spider. If set, only checks are performed and reported", default=False, action="store_true")

    opts, _ = op.parse_args()
    if not opts.project:
        op.error("A project ID is missed")

    if not opts.spider:
        op.error("A spider name is missed")

    if not (opts.schedule or opts.check_errors):
        op.error("--schedule or --check_errors options must be set")

    return opts

def get_job(project, spider):
    # get the latest job
    job = None
    for job in project.jobs(spider=spider, count=-1):pass

    if not job:
        print "Spider", spider, "not found"
        sys.exit()

    return job

def schedule_spider(project, opts):
    job = get_job(project, opts.spider)
    if job.info["state"] != "running":
        job_id = project.schedule(opts.spider)

def check_errors(project, opts):
    job = get_job(project, opts.spider)

    if job.info["state"] == "finished" and opts.mail:
        delta = (datetime.utcnow() - datetime.strptime(job.info["updated_time"], "%Y-%m-%dT%H:%M:%S.%f"))
        delta_days = delta.days
        delta_hours = delta.seconds / 3600.
        if job.info["errors_count"] > 0 and delta_days == 0 and delta_hours < ERROR_CHECK_PERIOD:
            send_emails(opts, ERROR_URL % (opts.project, job.info["id"]))

def send_emails(opts, error_link):
    if SES_LOGIN:
        ses = boto.connect_ses(*SES_LOGIN)
        ses.send_email(EMAIL_FROM, EMAIL_SUBJECT % opts.spider,
            EMAIL_BODY % (opts.spider, error_link), opts.mail)
    else:
        print EMAIL_BODY % (opts.spider, error_link)

def main():
    opts = parse_opts()
    conn = scrapinghub.Connection(SH_APIKEY)
    project = conn[opts.project]

    if opts.check_errors:
        check_errors(project, opts)

    elif opts.schedule:
        schedule_spider(project, opts)

if __name__ == "__main__":
    main()
