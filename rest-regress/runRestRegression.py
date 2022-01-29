#!/usr/bin/env python3

import subprocess, atexit, sys, time, json, argparse, logging
import signal, requests, urllib3, configparser, base64
from collections import Counter

config = configparser.RawConfigParser()
config.read('restregress.properties')

vsd_ip         = config.get('DEFAULT', 'vsd_ip')
vsd_port       = config.get('DEFAULT', 'vsd_port')
api_version    = config.get('DEFAULT', 'api_version')
logfile        = config.get('DEFAULT', 'logfile')

auth_key       = 'Basic Y3Nwcm9vdDpjc3Byb290'
csp_enterprise = ''
ITERATIONS     = 1
ENTITY_TYPE    = ''
PARENT_TYPE    = ''
PARENT_ID      = ''
FILTER         = ''
TEMPLATE       = ''

# logs
log = './log'

def setup():
    logging.info('Setting up regression environment')
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    rest_auth_setup()

def rest_get_call(rest_uri, page, fltr):
    rest_url = "https://" + vsd_ip + ":" + vsd_port + "/nuage/api/" + api_version + "/" + rest_uri
    logging.debug("REST GET URL %s" % rest_url)
    logging.debug("Fetching REST data using URL (%s)" % (rest_url))
    rest_headers = {
            'X-Nuage-Organization' : 'csp', 
            'Content-Type' : 'application/json', 
            'Authorization' : auth_key,
            }
    if fltr != '':
        rest_headers["x-nuage-filter"] = fltr
        rest_headers["x-nuage-filtertype"] = 'predicate'
        rest_headers["x-nuage-page"] = str(page)
        rest_headers["x-nuage-pagesize"] = str(500)
    try:
        rest_response = requests.get(rest_url, headers=rest_headers, verify=False)
        if rest_response.status_code == 200:
            logging.debug("REST Response %s" % rest_response.text)
            if len(rest_response.text) > 0:
                return rest_response.json()
            else:
                return None
        else:
            if debug:
                logging.debug("REST Failed %s" % rest_response.text)
            return None
    except:
        logging.debug("REST Exception %s" % rest_response.text)
        return None

def rest_post_call(rest_uri, data):
    rest_url = "https://" + vsd_ip + ":" + vsd_port + "/nuage/api/" + api_version + "/" + rest_uri
    logging.debug("REST POST URL %s" % rest_url)
    logging.debug("Posting REST data using URL (%s) with data=%s" % (rest_url, data))
    rest_headers = {
            'X-Nuage-Organization' : 'csp', 
            'Content-Type' : 'application/json', 
            'Authorization' : auth_key
            }
    try:
        rest_response = requests.post(rest_url, headers=rest_headers, json=data, verify=False)
        if rest_response.status_code == 200:
            logging.debug("REST Response %s" % rest_response.json())
            return rest_response.json()
        else:
            logging.debug("REST Response %s" % rest_response.json())
            return None
    except:
        logging.debug("REST Exception %s" % rest_response.json())
        return None

def rest_auth_setup():
    global auth_key, csp_enterprise
    response = rest_get_call("me", 1, '')
    csp_enterprise = response[0]["enterpriseID"]
    keystr = 'csproot:' + response[0]["APIKey"]
    encoded = base64.b64encode(keystr.encode())
    auth_key = "XREST " + encoded.decode("utf-8")

def run_test(i, entity_type, parent_type, parent_id, fltr, template):
    data = json.loads(template.replace("$i", str(i)))
    if parent_id != '':
        uri=parent_type + "s" + "/" + parent_id + "/" + entity_type + "s"
        logging.debug("Running object creation under specific parent for iteration(%s) for entities(%s) with uri=%s. Data=%s" % (i, entity_type, uri, data))
        rest_post_call(uri, data)
    else:
        if parent_type != '':
            x = 0
            while True:
                x = x + 1
                response = rest_get_call(parent_type + "s", x, fltr)
                if response:
                    for nsg in response:
                        #TODO fetch all ids for parent_type and call for all
                        nsgId = nsg["ID"]
                        uri=parent_type + "s" + "/" + nsgId + "/" + entity_type + "s"
                        logging.debug("Running object creation under all parent for iteration(%s) for entities(%s) with uri=%s. Data=%s" % (i, entity_type, uri, data))
                        rest_post_call(uri, data)
                else:
                    break
        else:
            uri=entity_type + "s"
            logging.debug("Running object creation under csp for iteration(%s) for entities(%s) with uri=%s. Data=%s" % (i, entity_type, uri, data))
            rest_post_call(uri, data)

def main(argv):
    
    setup()

    global offset
    offset = 0

    print('-' * 100)
    for i in range(0, ITERATIONS):
        run_test(i, ENTITY_TYPE, PARENT_TYPE, PARENT_ID, FILTER, TEMPLATE)
    logging.info('-' * 100)
    print('-' * 100)
    time.sleep(10)

def signal_handler(sig, frame):
    logging.info('you pressed Ctrl+C!')
    print('you pressed Ctrl+C!')
    sys.exit(0)

def cleanup():
    logging.info('Stopping all process')
    logging.info('cleaned up')

if __name__ == '__main__':
    
    parser=argparse.ArgumentParser()
    parser.add_argument('-l', '--log',      help='Log level')
    parser.add_argument('-e', '--entity',   help='Run regression for specific entity')
    parser.add_argument('-n', '--number',   help='Run regression for specific number of times')
    parser.add_argument('--ptype',          help='Parent entity type')
    parser.add_argument('--pid',            help='Parent id')
    parser.add_argument('-f', '--fltr',     help='Filter to find parent id')
    parser.add_argument('-t', '--template', help='Template for rest calls')
    args=parser.parse_args()
   
    subprocess.run(['mkdir', '-p', log])

    if args.log:
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)
        logging.basicConfig(filename=logfile,filemode='w',level=numeric_level)
    else:
        logging.basicConfig(filename=logfile,filemode='w',level=logging.INFO)
    if args.number:
       ITERATIONS = int(args.number)
    if args.entity:
       ENTITY_TYPE = args.entity
    if args.ptype:
       PARENT_TYPE = args.ptype
    if args.pid:
       PARENT_ID = args.pid
    if args.template:
       TEMPLATE = args.template
    if args.fltr:
       FILTER = args.fltr

    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    main(sys.argv[1:])
    sys.exit()
