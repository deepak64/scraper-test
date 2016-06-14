import urllib, urllib2, base64
import socket
import json
import os
import sys
import time
import httplib
import traceback


#config
delay = 10
item = {}

cidr=urllib2.urlopen('http://169.254.169.254/latest/meta-data/public-ipv4').read()

item['ip_address'] = cidr#socket.gethostname()
item['port'] = 6800

with open ("/etc/cluster", "r") as cluster:
    environment_def  = cluster.read().replace('\n', '')
if environment_def.startswith('prod'):
    endpoint = "internal-private-forager-403834374.us-west-1.elb.amazonaws.com"
else:
    endpoint = "stage.bright.com"


def encoded_dict(in_dict):
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict


str_ping_data = encoded_dict(item)
data = urllib.urlencode(str_ping_data)



def get_status():
    """get status of a scraper"""
    try: 
        response = urllib2.urlopen("http://127.0.0.1:6800/listprojects.json")
        return json.loads(response.read())
    except urllib2.HTTPError, e:
        print 'HTTPError : ' + str(e.code)
    except urllib2.URLError, e:
        print 'URLError : ' + str(e.reason)
    except httplib.HTTPException, e:
        print 'HTTPException'
    except Exception:
        traceback.print_exc(file=sys.stdout)
    return None


def set_status():
    """update status"""
    request = urllib2.Request("http://{}/api/v1/node/ping".format(endpoint), data)
    base64string = base64.encodestring('%s:%s' % ("feedwizard", "7de42fc83c")).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    try:
        status = urllib2.urlopen(request)
        return status.read()
    except urllib2.HTTPError, e:
        print 'HTTPError : ' + str(e.code)
    except urllib2.URLError, e:
        print 'URLError : ' + str(e.reason)
    except httplib.HTTPException, e:
        print 'HTTPException'
    except Exception:
        traceback.print_exc(file=sys.stdout)
    return None




 
# check if spiders are loaded
while True:
    try:

        status = get_status()
        if 'status' not in status:
            exit()
        elif status['status'] != 'ok' or len(status['projects']) == 0:
            """if os.path.isdir("/domain/scraper/brightcorp"):
                print "there is an existing repo"
            else:
                print "no repo yet"
                #NOTE: all deploy are down by the standard deployement system 
                #os.system("cd /domain && git clone git@github.com:brightjobs/scraper")
                #print "repo downloaded"
            # do a scrapy deploy
            #NOTE: all deploy are down by the standard deployement system
            #os.system("cd /domain/scraper/brightcorp && scrapy deploy")
            """
            pass
        print set_status()
    except:
        traceback.print_exc(file=sys.stdout)
        pass
    time.sleep(delay)

