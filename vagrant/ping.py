import urllib, urllib2, base64
import socket
import json
import os
import sys
import commands
import traceback

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

item = {}
item['ip_address'] = commands.getoutput("/sbin/ifconfig").split("\n")[10].split()[1][5:]
item['port'] = 6800

# check if spiders are loaded
try:
    status = json.loads(urllib2.urlopen("http://127.0.0.1:6800/listprojects.json").read())
    if 'status' not in status:
        print 'listprojects.json status not OK'
        print status
        exit()
    elif status['status'] != 'ok' or len(status['projects']) == 0:
        os.system("cd /bright/scraper/brightcorp && scrapy deploy")
        print 'brightcorp project deployed'

    str_ping_data = encoded_dict(item)
    data = urllib.urlencode(str_ping_data)
    request = urllib2.Request("http://" + sys.argv[1] + "/api/v1/node/ping", data)
    base64string = base64.encodestring('%s:%s' % (sys.argv[2], sys.argv[3])).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    x = urllib2.urlopen(request)
    print x.read()
except:
    traceback.print_exc(file=sys.stdout)
    pass