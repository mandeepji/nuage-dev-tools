#!/usr/bin/env python

from ncclient import manager
from lxml import etree
import os, sys, getopt, traceback, json

username = 'netconf'
password = 'tigris'

def usage():
    print 'Usage:   ', os.path.basename(__file__), '-h|host <IP Address> [Options]'
    print 'Options: -h|--host      : IP address of netconf device'
    print '         -u|--username  : netconf username [default=', username, ']'
    print '         -p|--password  : netconf password [default=', password, ']'
    print '         -f|--filter    : xml file having netconf filter'
    print '         -v|--values    : json as key-value. values will be used to replace keys in filter xml file'
    print '         -n|--namespace : xml namespace'
    sys.exit()

def main(argv):
    hostname = ''
    global username
    global password
    port = 830
    namespace= "{urn:nokia.com:sros:ns:yang:sr:conf}"
    tree = ''
    xmlfilter = ''
    values = ''

    try:
        opts, args = getopt.getopt(argv,"h:u:p:f:n:v:", ["host=","username=","password=","filter=","namespace=","values="])
    except getopt.GetoptError:
        usage()

    for opt, arg in opts:
        if opt in ("-h", "--host"):
            hostname = arg
        elif opt in ("-u", "--username"):
            username = arg
        elif opt in ("-p", "--password"):
            password = arg
        elif opt in ("-n", "--namespace"):
            namespace = arg
        elif opt in ("-v", "--values"):
            values = json.loads(arg)
        elif opt in ("-f", "--filter"):
            tree = etree.parse(arg)
            rootXml = tree.getroot();
            xmlfilter = etree.tostring(tree.getroot(), encoding='utf8', method='xml')
        else:
            usage()

    if values <> '':
        for key,value in values.items():
            xmlfilter = xmlfilter.replace(key, value)

    if '$' in xmlfilter:
        print 'Please use -v to provide all values in filter.'
        print 'Following lines uses variables:'
        for line in xmlfilter.splitlines():
            if '$' in line:
                print '>>>>', line
        sys.exit()

    try:
        with manager.connect(host=hostname,
                                 port=830,
                                 username=username,
                                 password=password,
                                 hostkey_verify=False,
                                 ) as sr_manager:
            mfilter = xmlfilter
            sr_config = sr_manager.get(('subtree', mfilter))
            print sr_config
    except:
        print 'Exception while execution'
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60

if __name__ == '__main__':
    main(sys.argv[1:])
