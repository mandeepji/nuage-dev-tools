#!/usr/bin/env python3

import subprocess, sys, time, json, os, re, argparse, logging
import signal, requests, urllib3, base64

vsd_ip          = 'localhost'
vsd_port        = 8443
api_version     = 'v6'
logfile         = 'log/bulk-alarm.log'

#####  Overall process for alarm regression  #############
## 1. For each alarm definition in spec files            #
##    1.1. Build alarm xml file                          #
##    1.2. Push Alarm via XMPP Client                    #
##    1.3. Wait for alarm to be created in VSD           #
##########################################################

auth_key        = 'Basic Y3Nwcm9vdDpjc3Byb290'
csp_enterprise  = ''
alarm_name      = ''
alarm_code      = 0
alarm_mo        = ''

entity_cache = {}

xmpp_client_home = '/opt/vsd/tools'
xmpp_client_cmd  = xmpp_client_home + '/xmpp_client.py -i 127.0.0.1 -u simulator -p Alcateldc -d sendmsg '

alarm_spec_meta = './alarm-spec-meta'

log = './log'

# schema
schema_code = 'code'
schema_name = 'title'
schema_object_type = 'alarmed-object-type'
schema_severity = 'severity'
schema_auto_clear = 'auto-clear'
schema_description = 'description'

parents = {
        'nsgateway'           : 'enterprise',
        'vsc'                 : 'vsp',
        'ikegatewayconnection': '',
        'ssidconnection'      : '',
        'vlan'                : 'nsport',
        'vport'               : 'subnet',
        'service'             : 'gateway',
        'nsport'              : 'nsgateway',
        }

def setup():
    logging.info('Setting up environment')
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    subprocess.run(['rm', '-rf', log + '/xml_inputs'])
    rest_auth_setup()

def rest_get_call(rest_uri):
    rest_url = "https://" + vsd_ip + ":" + str(vsd_port) + "/nuage/api/" + api_version + "/" + rest_uri
    logging.debug("REST GET URL %s" % rest_url)
    logging.debug("Fetching REST data using URL (%s)" % (rest_url))
    rest_headers = {
            'X-Nuage-Organization' : 'csp', 
            'Content-Type' : 'application/json', 
            'Authorization' : auth_key
            }
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

def rest_auth_setup():
    global auth_key, csp_enterprise
    response = rest_get_call("me")
    csp_enterprise = response[0]["enterpriseID"]
    keystr = 'csproot:' + response[0]["APIKey"]
    encoded = base64.b64encode(keystr.encode())
    auth_key = "XREST " + encoded.decode("utf-8")

def create_input_file(action, alarm_log, entity_type, entity_id, alarm_name, severity, description):
    input_file_name = alarm_log + '/' + entity_type + '_' + entity_id + '-input-' + action + '.xml'
    input_file = open(input_file_name, "w+")
    parameters = re.findall('\{([^}]+)', description.replace("-", "_"))
    param_content = ""
    if len(parameters) > 0:
        param_result = [None]*(len(parameters)+len(parameters))
        param_result[::2] = parameters
        param_result[1::2] = parameters
        param_content = ("<parameters>" + "".join(['\n              <parameter name="%s">dummy_%s</parameter>']*len(parameters)) + "\n           </parameters>") % tuple(param_result)
    input_content = '''<nuage xmlns='alu:nuage:message'>
    <cloudmgmt xmlns="http://www.nuagenetworks.net/2013/controller/Request" version="20.10.1" nodeType="VSC">
        <message xmlns="http://www.nuagenetworks.net/2013/controller/Message" type="ERROR">
            <error action="%s">
               <entity-key>%s#%s</entity-key>
               <alarm-code>%s</alarm-code>
               <reason>Alarm Regression Test</reason>
               <severity>%s</severity>
               %s
            </error>
        </message>
    </cloudmgmt>
</nuage>''' % (action, entity_type, entity_id, alarm_name, severity, param_content)

    input_file.write(input_content)
    input_file.close()
    return input_file_name

def send_xmpp(xmpp_file):
    logging.debug("Sending XMPP Message to Raise/Clear Alarm. Input file: %s" % xmpp_file)
    FNULL = open(os.devnull, 'w')
    subprocess.call(xmpp_client_cmd + " " + xmpp_file, shell=True, stdout=FNULL, stderr=subprocess.STDOUT)

def read_defs():
    logging.debug('Reading alarm spec meta %s' % alarm_spec_meta)
    alarm_defs = []
    with open(alarm_spec_meta) as fp:
        for line in fp:
            values = line.split("#")
            #bfdsession#BFD_SESSION#50002#0.0.0#MAJOR#true#BFD Session Down
            alarm_def = {schema_name: values[7].replace(' ', '_').upper(), schema_object_type: values[1], schema_code: int(values[3]), schema_severity: values[5], schema_auto_clear: values[6], schema_description: "dummy description"}
            alarm_defs.append(alarm_def)
    return alarm_defs
 
def get_entity_urls(entity_type):
    uri = entity_type + 's'
    uris = []
    parent_path = parents.get(entity_type, None)
    logging.debug("Parent path for entity %s = %s" % (entity_type, parent_path))
    if parent_path:
        #sep = parent_path.rfin
        parent_urls = get_entity_urls(parent_path)
        for parent_url in parent_urls:
            response = rest_get_call(parent_url)
            if response == None:
                continue
            for parent_entity in response:
                url = parent_path + 's/' + parent_entity.get("ID") + '/' + entity_type + 's'
                uris.append(url)
    else:
        uris.append(uri)
    return uris

def get_entities(url):
    entities_data = []
    response = rest_get_call(url)
    if response:
        entities_data.extend(response)
    return entities_data

def test(filename, url, entity_type, entity_id, alarm_def, action):
    send_xmpp(filename)
    time.sleep(0.5)

    uri = entity_type + "s/" + entity_id + "/alarms"
    logging.info("{:6} {:55} {:8}".format(alarm_def[schema_code], alarm_def[schema_name], action.upper()))
    print("{:6} {:55} {:8}".format(alarm_def[schema_code], alarm_def[schema_name], action.upper()))

def run_test(alarm_def):
    logging.debug("Running test for alarm-code(%s), alarm-name(%s) for entities(%s)" % (alarm_def[schema_code], alarm_def[schema_name], alarm_def[schema_object_type]))

    entity_type = alarm_def[schema_object_type]
    entities_data = None
    urls = get_entity_urls(entity_type)
    for url in urls:
        entities_data = get_entities(url)
        if entities_data:
            entity_cache[entity_type] = entities_data
        for entity_data in entities_data:
            if entity_type == "enterprise":
                if entity_data["name"] == "Shared Infrastructure":
                    continue
            dir_path = os.getcwd()
            alarm_log = dir_path + "/%s/xmpp_inputs/%d_%s" % (log, alarm_def[schema_code], alarm_def[schema_name].replace(" ", "_").replace("-", "_"))
            subprocess.run(['mkdir', "-p", alarm_log])

            raise_file_name = create_input_file("set",   alarm_log, entity_type, entity_data["ID"], alarm_def[schema_name].replace(" ", "_").replace("-", "_").upper(), alarm_def[schema_severity], alarm_def[schema_description])

            test(raise_file_name, url, entity_type, entity_data["ID"], alarm_def, 'set')

def main(argv):
    
    setup()

    global xmpp_process
    global offset
    offset = 0

    if not os.path.isfile(alarm_spec_meta):
       logging.error('Alarm spec meta ({}) does not exist'.format(alarm_spec_meta))
       print('Alarm spec meta ({}) does not exist'.format(alarm_spec_meta))
       sys.exit()

    alarm_defs = read_defs()

    logging.info('-' * 100)
    logging.info("{:^6} {:55} {:8} {:12}".format("CODE", "TITLE", "ACTION", "REST"))
    logging.info('-' * 100)
    print('-' * 100)
    print("{:^6} {:55} {:8} {:12}".format("CODE", "TITLE", "ACTION", "REST"))
    print('-' * 100)
    for alarm_def in alarm_defs:
        if alarm_name != '':
            if alarm_def[schema_name] == alarm_name:
                run_test(alarm_def)
        elif alarm_code != 0:
            if int(alarm_def[schema_code]) == alarm_code:
                run_test(alarm_def)
        elif alarm_mo != '':
            if alarm_mo in alarm_def[schema_object_type]:
                run_test(alarm_def)
        else:
            run_test(alarm_def)
    logging.info('-' * 100)
    print('-' * 100)
    time.sleep(10)

def signal_handler(sig, frame):
    logging.info('you pressed Ctrl+C!')
    print('you pressed Ctrl+C!')
    sys.exit(0)

def list_alarms():
    alarm_defs = read_defs()

    logging.info('-' * 250)
    logging.info("{:^6} {:55} {:8} {:10} {:20} {}".format("CODE", "TITLE", "SEVERITY", "AUTO-CLEAR", "OBJECT", "DESCRIPTION"))
    logging.info('-' * 250)
    print('-' * 250)
    print("{:^6} {:55} {:8} {:10} {:20} {}".format("CODE", "TITLE", "SEVERITY", "AUTO-CLEAR", "OBJECT", "DESCRIPTION"))
    print('-' * 250)
    for alarm_def in alarm_defs:
        logging.info("{:6} {:55} {:8} {:10} {:20} {}".format(alarm_def[schema_code], alarm_def[schema_name], alarm_def[schema_severity], "YES" if alarm_def[schema_auto_clear] == 'true' else "NO", alarm_def[schema_object_type], alarm_def[schema_description]))
        print("{:6} {:55} {:8} {:10} {:20} {}".format(alarm_def[schema_code], alarm_def[schema_name], alarm_def[schema_severity], "YES" if alarm_def[schema_auto_clear] == 'true' else "NO", alarm_def[schema_object_type], alarm_def[schema_description]))

def usage():
    print("Usage   : %s [Option]" % sys.argv[0])
    print("          Option --list : list all alarm definitions")
    print("                 --log {level} : run with this log level")
    print("                 --name {alarm-name} : run for specific alarm name")
    print("                 --code {alarm-code} : run for specific alarm code")
    print("                 --mo {mo-name} : run for specific managed object")
    print("Example : %s --name MAC_LOOP_ERROR" % sys.argv[0])
    sys.exit()

if __name__ == '__main__':
    
    parser=argparse.ArgumentParser()
    parser.add_argument('--list',   help='List all alarm definitions', action='store_true')
    parser.add_argument('--log',  help='Log level')
    parser.add_argument('--name',   help='Specific alarm name')
    parser.add_argument('--code',   help='Specific alarm code', type=int, default=0)
    parser.add_argument('--entity', help='Specific alarm entity')
    args=parser.parse_args()
   
    subprocess.run(['mkdir', '-p', log])

    if args.log:
        numeric_level = getattr(logging, args.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % args.log)
        logging.basicConfig(filename=logfile,filemode='w',level=numeric_level)
    else:
        logging.basicConfig(filename=logfile,filemode='w',level=logging.INFO)
    if args.list:
        list_alarms()
        sys.exit()
    if args.name:
       alarm_name = args.name
    elif args.code:
        alarm_code = args.code
    elif args.entity:
        alarm_mo = args.entity

    signal.signal(signal.SIGINT, signal_handler)
    main(sys.argv[1:])
    sys.exit()
