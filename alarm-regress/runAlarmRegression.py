#!/usr/bin/env python3

import subprocess, atexit, sys, time, json, os, re, argparse, logging
import pexpect, signal, requests, urllib3, select, configparser, base64
from collections import Counter

config = configparser.RawConfigParser()
config.read('alarmregress.properties')

vsd_ip          = config.get('DEFAULT', 'vsd_ip')
vsd_port        = config.get('DEFAULT', 'vsd_port')
api_version     = config.get('DEFAULT', 'api_version')
vsd_hostname    = config.get('DEFAULT', 'vsd_hostname')
jms_client_home = config.get('DEFAULT', 'jms_client_home')
alarm_spec_home = config.get('DEFAULT', 'alarm_spec_home')
cloudmgmt_sim   = config.get('DEFAULT', 'cloudmgmt_sim')
logfile         = config.get('DEFAULT', 'logfile')

#####  Overall process for alarm regression  #############################
## 1. Start JMS Client and start watching JMSEvents on topic/CNAAlarms   #
## 2. For each alarm definition in spec files (set/clear)                #
##    1.1. Build alarm xml file                                          #
##    1.2. Push Alarm via XMPP Client                                    #
##    1.3. Wait for alarm to be created in VSD                           #
##    1.4. Validate Alarm via REST call entity/alarms                    #
##    1.5. Validate Alarm via JMS Logs                                   #
##########################################################################

# default flags. can be overridden by command line parameters
keep = False
skip = False

auth_key        = 'Basic Y3Nwcm9vdDpjc3Byb290'
csp_enterprise  = ''
ALARM_NAME      = ''
ALARM_CODE      = 0
ALARM_MO        = ''
counter         = Counter()
counter_names   = ["REST SET PASS", "REST SET FAIL", "REST CLEAR PASS", "REST CLEAR FAIL", "JMS SET PASS", "JMS SET FAIL", "JMS CLEAR PASS", "JMS CLEAR FAIL"]

entity_cache = {}

#jms_alarm_topic = 'topic/CNAAlarms'
jms_client_cmd  = jms_client_home + '/runjmsclient.sh'

xmpp_client_home = cloudmgmt_sim + '/src/main/scripts'
xmpp_client_cmd  = xmpp_client_home + '/runcnaXmppSim.bash -x ' + vsd_hostname + ' -c ' + vsd_ip + ' -xh ' + vsd_ip

alarm_spec_dir   = alarm_spec_home + '/'

# logs
log = './log'
jms_log_dir = jms_client_home + '/log'
jms_log_file = jms_log_dir + '/jmsclient.log'
xmpp_tor = xmpp_client_home + '/tor'
xmpp_log = xmpp_client_home + '/cna-mediator.log'

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
        'vlan'                : 'vport',
        'vport'               : 'subnet',
        'service'             : 'gateway',
        'nsport'              : 'nsgateway',
        }

def setup():
    logging.info('Setting up regression environment')
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # Cleaning regression, jms, xmpp client logs
    logging.debug("Cleaning regression, jms, xmpp client logs")
    logging.debug("jms_log_dir=%s, xmpp_tor=%s, xmpp_log=%s, log=%s" % (jms_log_dir, xmpp_tor, xmpp_log, log))
    subprocess.run(['rm', '-rf', jms_log_dir])
    subprocess.run(['rm', '-rf', xmpp_tor])
    subprocess.run(['rm', '-rf', xmpp_log])

    rest_auth_setup()
    if not skip:
        jms_auth_setup()

def rest_get_call(rest_uri):
    rest_url = "https://" + vsd_ip + ":" + vsd_port + "/nuage/api/" + api_version + "/" + rest_uri
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
    response = rest_get_call("me")
    csp_enterprise = response[0]["enterpriseID"]
    keystr = 'csproot:' + response[0]["APIKey"]
    encoded = base64.b64encode(keystr.encode())
    auth_key = "XREST " + encoded.decode("utf-8")

def jms_auth_setup():
    uri = 'enterprises/' + csp_enterprise + '/users'
    response = rest_get_call(uri)
    jms_user_name = 'AlarmRegressUser'
    exist = False
    for user in response:
        if jms_user_name == user["userName"]:
            exist = True
    if not exist:
        logging.info("Creating jms user (%s)" % jms_user_name)
        data = { "firstName": jms_user_name, "lastName": jms_user_name, "password": jms_user_name, "userName": jms_user_name, "email": "AlarmRegressUser@csp.com" }
        rest_post_call(uri, data)
    else:
        logging.info("%s user exist." % jms_user_name)

    jms_properties_file = open(jms_client_home + '/jmsclient.properties', "r")
    file_content = ''
    for line in jms_properties_file:
        if "jms_username =" in line:
            line = "jms_username =" + jms_user_name + '@csp\n'
        elif "jms_password =" in line:
            line = "jms_password =" + jms_user_name + '\n'
        file_content = file_content + line
    jms_properties_file = open(jms_client_home + '/jmsclient.properties', "w+")
    jms_properties_file.write(file_content)
    jms_properties_file.close()

def is_instanceof_alarm(alarm_def, alarm):
    if alarm["title"] == alarm_def[schema_name] and alarm["errorCondition"] == alarm_def[schema_code]: 
        return True
    else:
        return False

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
    input_content = '''<cloudmgmt xmlns="http://www.nuagenetworks.net/2013/controller/Request" version="6.0.1" nodeType="VSC">
    <message xmlns="http://www.nuagenetworks.net/2013/controller/Message" type="ERROR">
        <error action="%s">
           <entity-key>%s#%s</entity-key>
           <alarm-code>%s</alarm-code>
           <reason>Alarm Regression Test</reason>
           <severity>%s</severity>
           %s
        </error>
    </message>
</cloudmgmt>''' % (action, entity_type, entity_id, alarm_name, severity, param_content)

#<alarm-code>%s</alarm-code>
    input_file.write(input_content)
    input_file.close()
    return input_file_name

def send_xmpp(xmpp_file):
    logging.debug("Sending XMPP Message to Raise/Clear Alarm. Input file: %s" % xmpp_file)
    xmpp_process.expect('100. Exit :-')
    xmpp_process.sendline('29')
    xmpp_process.expect('Enter file name:')
    xmpp_process.sendline(xmpp_file)

def validate_rest(uri, alarm_def, action):
    logging.debug("Validating REST Response for %s" % action)
    response = rest_get_call(uri)
    if response == None:
        return "No Response"
    if(is_instanceof_alarm(alarm_def, response[0])):
        return "PASS"
    return "FAIL"
    
def read_jms_logs():
    logs = ''
    global jms_logs_f
    global offset
    jms_logs_f.seek(offset)
    for line in jms_logs_f:
        logs = logs + line
        offset += len(line)
    return logs

def read_defs():
    logging.debug('Reading alarm spec files in %s' % alarm_spec_dir)
    alarm_defs = []
    for filename in os.listdir(alarm_spec_dir):
        if "spec" in filename:
            alarm_spec_file = os.path.join(alarm_spec_dir, filename)
            with open(alarm_spec_file) as alarm_def_file:
                alarm_defs.append(json.load(alarm_def_file))

    alarm_defs.sort(key=lambda x: x[schema_code])
    return alarm_defs

def validate_jms(alarm_def, action):
    if not skip:
        logging.debug("Validating JMS Event for %s" % action)
        jlogs = read_jms_logs()
        if jlogs != '':
            for jms_msg_line in jlogs.splitlines():
                if "message body:" in jms_msg_line:
                    message_body = json.loads(re.search('message body: (.*)', jms_msg_line).group(1))
                    if(is_instanceof_alarm(alarm_def, message_body["entities"][0])):
                        return "PASS"
    else:
        return "NA"
    return "FAIL"

def get_entity_urls(entity_type):
    uri = entity_type + 's'
    uris = []
    parent_path = parents.get(entity_type, None)
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
    rest_result = validate_rest(uri, alarm_def, action)
    if action == 'clear':
        if rest_result == "No Response" or rest_result == None:
            rest_result = "PASS"
            
    jms_result = validate_jms(alarm_def, action)

    counter['REST %s %s' % (action.upper(), rest_result)] += 1
    counter['JMS %s %s' % (action.upper(), jms_result)] += 1

    logging.info("{:6} {:55} {:8} {:12} {:12}".format(alarm_def[schema_code], alarm_def[schema_name], action.upper(), rest_result, jms_result))
    print("{:6} {:55} {:8} {:12} {:12}".format(alarm_def[schema_code], alarm_def[schema_name], action.upper(), rest_result, jms_result))

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
            if entity_data["name"] == "Shared Infrastructure":
                continue
            dir_path = os.getcwd()
            alarm_log = dir_path + "/%s/xmpp_inputs/%d_%s" % (log, alarm_def[schema_code], alarm_def[schema_name].replace(" ", "_").replace("-", "_"))
            subprocess.run(['mkdir', "-p", alarm_log])

            raise_file_name = create_input_file("set",   alarm_log, entity_type, entity_data["ID"], alarm_def[schema_name].replace(" ", "_").replace("-", "_").upper(), alarm_def[schema_severity], alarm_def[schema_description])
            clear_file_name = create_input_file("clear", alarm_log, entity_type, entity_data["ID"], alarm_def[schema_name].replace(" ", "_").replace("-", "_").upper(), alarm_def[schema_severity], alarm_def[schema_description])

            #######################
            #### TEST for SET  ####
            #######################
            test(raise_file_name, url, entity_type, entity_data["ID"], alarm_def, 'set')

            #########################
            #### TEST for CLEAR  ####
            #########################
            if not keep:
                test(clear_file_name, url, entity_type, entity_data["ID"], alarm_def, 'clear')

def main(argv):
    
    setup()

    global jms_process, jms_logs_f, xmpp_process
    global offset
    offset = 0

    if not skip:
        logging.info('Starting JMS Client')
        jms_process = subprocess.Popen([jms_client_cmd, vsd_ip])
        time.sleep(5)
        jms_logs_f = open(jms_log_file, "r")
        jlogs = read_jms_logs()
        if "Started connection" in jlogs:
            logging.info("JMS Client started and connected")
        else:
            logging.info("JMS Client failed to start/connect")
            return
        
    logging.info('Starting XMPP Client')
    xmpp_process = pexpect.spawnu(xmpp_client_cmd, cwd=xmpp_client_home)

    alarm_defs = read_defs()

    logging.info('-' * 100)
    logging.info("{:^6} {:55} {:8} {:12} {:12}".format("CODE", "TITLE", "ACTION", "REST", "JMS"))
    logging.info('-' * 100)
    print('-' * 100)
    print("{:^6} {:55} {:8} {:12} {:12}".format("CODE", "TITLE", "ACTION", "REST", "JMS"))
    print('-' * 100)
    for alarm_def in alarm_defs:
        if ALARM_NAME != '':
            if alarm_def[schema_name] == ALARM_NAME:
                run_test(alarm_def)
        elif ALARM_CODE != 0:
            if int(alarm_def[schema_code]) == ALARM_CODE:
                run_test(alarm_def)
        elif ALARM_MO != '':
            if ALARM_MO in alarm_def[schema_object_type]:
                run_test(alarm_def)
        else:
            run_test(alarm_def)
    logging.info('-' * 100)
    print('-' * 100)

    logging.info('RESULT:')
    print('RESULT')
    logging.info('-' * 8)
    print('-' * 8)
    for c in counter_names:
        logging.info('%-17s  %s' % (c, counter[c]))
        print('%-17s  %s' % (c, counter[c]))

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
        logging.info("{:6} {:55} {:8} {:10} {:20} {}".format(alarm_def[schema_code], alarm_def[schema_name], alarm_def[schema_severity], "YES" if alarm_def[schema_auto_clear] else "NO", alarm_def[schema_object_type], alarm_def[schema_description]))
        print("{:6} {:55} {:8} {:10} {:20} {}".format(alarm_def[schema_code], alarm_def[schema_name], alarm_def[schema_severity], "YES" if alarm_def[schema_auto_clear] else "NO", alarm_def[schema_object_type], alarm_def[schema_description]))

def cleanup():
    logging.info('Stopping all process')
    if jms_process:
        jms_process.terminate()
    if xmpp_process:
        xmpp_process.close()
    logging.info('cleaned up')

def usage():
    print("Usage   : %s [Option]" % sys.argv[0])
    print("          Option -list : list all alarm definitions")
    print("                 -name {alarm-name} : run regression for specific alarm name")
    print("                 -code {alarm-code} : run regression for specific alarm code")
    print("                 -mo {mo-name} : run regression for specific managed object")
    print("Example : %s -name MAC_LOOP_ERROR" % sys.argv[0])
    sys.exit()

if __name__ == '__main__':
    
    parser=argparse.ArgumentParser()
    parser.add_argument('-l', '--list',   help='List all alarm definitions', action='store_true')
    parser.add_argument('--log',  help='Log level')
    parser.add_argument('-k', '--keep',   help='Keeps alarm. Will not clear after raising alarm.', action='store_true')
    parser.add_argument('-s', '--skip',   help='Skips validation via jms.', action='store_false')
    parser.add_argument('-n', '--name',   help='Run regression for specific alarm name')
    parser.add_argument('-c', '--code',   help='Run regression for specific alarm code', type=int, default=0)
    parser.add_argument('-e', '--entity', help='Run regression for specific alarm entity')
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
    if args.keep is not None:
        keep = args.keep
    if args.skip is not None:
        skip = args.skip
    if args.name:
       ALARM_NAME = args.name
    elif args.code:
        ALARM_CODE = args.code
    elif args.entity:
        ALARM_MO = args.entity

    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    main(sys.argv[1:])
    sys.exit()
