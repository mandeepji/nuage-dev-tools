#!/usr/bin/env python3

import subprocess, atexit, sys, signal, socket, os, time, re

VMNAME       = ''
VM_IMAGE     = ''
VM_QCOW      = ''
VM_LOCK_FILE = ''
SIM_IP       = ''

MY_IF=os.popen("ifconfig -a | sed -n 1p | awk '{print $1}' | sed 's/:$//'").read().rstrip("\n\r")

def enableFeatures():
    print("Enabling features")
    commands = '''
        configure
            interface mgmt 0
                ip address dhcp
            exit

            username admin password 0 Alcateldc!

            feature telnet
            feature nxapi
            feature bash-shell
            feature scp-server
            cfs eth distribute
            nv overlay evpn
            feature ospf
            feature bgp
            feature isis
            feature fabric forwarding
            feature netconf
            feature interface-vlan
            feature vn-segment-vlan-based
            feature lacp
            feature vpc
            feature lldp
            feature bfd
            feature nv overlay
            fabric forwarding anycast-gateway-mac aacc.44ff.6356
            hardware access-list tcam region racl 1024
            hardware access-list tcam region arp-ether 256
            nxapi use-vrf management

            interface nve1
                host-reachability protocol bgp
            exit

            router bgp 1022
            exit
        exit

        show interface mgmt 0
        '''

    for cmd in commands.splitlines():
        socat_process.stdin.write(bytes(cmd + '\n', 'utf-8'))
        socat_process.stdin.flush()

def showInterface():
    print("Executing show interface command")
    commands = '''
        show interface mgmt 0
        '''

    for cmd in commands.splitlines():
        socat_process.stdin.write(bytes(cmd + '\n', 'utf-8'))
        socat_process.stdin.flush()

def bootConfig():
    global socat_process, SIM_IP
    time.sleep(30)
    cmd = ['socat', 'stdio', 'unix-connect:%s' % VM_LOCK_FILE]
    socat_process = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE)
    while True:
        line = socat_process.stdout.readline().decode("utf-8").rstrip("\n\r")
        print("socat>%s" % line)
        if line.startswith('Abort Power On Auto Provisioning'):
            socat_process.stdin.write(bytes('skip\n', 'utf-8'))
            socat_process.stdin.flush()
        elif line.startswith(' login:'):
            print("SimSetup: auto-login")
            socat_process.stdin.write(bytes('admin\n', 'utf-8'))
            socat_process.stdin.flush()
        elif line.startswith('Password:'):
            print("SimSetup: auto-login-password")
            socat_process.stdin.write(bytes('\n', 'utf-8'))
            socat_process.stdin.flush()
            time.sleep(5)
            enableFeatures()
        elif line.find('Internet Address is ') != -1:
            m = re.search('  Internet Address is (.*?)/.*', line)
            if m:
                SIM_IP = m.group(1)
            print("Sim %s" % SIM_IP)
            break

def startVM():
    subprocess.run(['vboxmanage', 'startvm', VMNAME])

def createSim():
    global VM_LOCK_FILE
    print("Creating Sim name=%s" % VMNAME)
    subprocess.run(['vboxmanage', 'createvm', '--name', VMNAME, '--ostype', 'Linux_64', '--register'])

    VM_LOCK_FILE='/tmp/cisco_sim_' + VMNAME

    print("Configuring Sim")
    subprocess.run(['vboxmanage', 'storagectl', VMNAME, '--name', "SATA Controller", '--add', 'sata', '--controller', 'IntelAHCI'])
    subprocess.run(['vboxmanage', 'storageattach', VMNAME, '--storagectl', "SATA Controller", '--port', '0', '--device', '0', '--type', 'hdd', '--medium', VM_IMAGE])

    subprocess.run(['vboxmanage', 'modifyvm', VMNAME, '--boot1', 'disk', '--boot2', 'dvd', '--boot3', 'none', '--boot4', 'none'])
    subprocess.run(['vboxmanage', 'modifyvm', VMNAME, '--memory', '8192', '--firmware', 'efi', '--cpus', '2', '--vtxvpid', 'on', '--vram', '24'])
    subprocess.run(['vboxmanage', 'modifyvm', VMNAME, '--nic1', 'bridged', '--bridgeadapter1', MY_IF, '--macaddress1', 'auto'])
    subprocess.run(['vboxmanage', 'modifyvm', VMNAME, '--uart1', '0x3f8', '4', '--uartmode1', 'server', VM_LOCK_FILE])
    subprocess.run(['vboxmanage', 'modifyvm', VMNAME, '--audio', 'none', '--usb', 'on', '--usbehci', 'off', '--usbxhci', 'off'])

def getConfig():
    global socat_process, SIM_IP
    VM_LOCK_FILE='/tmp/cisco_sim_' + VMNAME
    print("Getting sim config from %s" % VM_LOCK_FILE)
    cmd = ['socat', 'stdio', 'unix-connect:%s' % VM_LOCK_FILE]
    socat_process = subprocess.Popen(cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE)

    time.sleep(5)
    socat_process.stdin.write(bytes('\n\n', 'utf-8'))
    socat_process.stdin.flush()

    showInterface()

    while True:
        line = socat_process.stdout.readline().decode("utf-8").rstrip("\n\r")
        print("socat>%s" % line)
        if line.endswith('login:'):
            print("SimSetup: auto-login")
            socat_process.stdin.write(bytes('admin\n', 'utf-8'))
            socat_process.stdin.flush()
        elif line.startswith('Password:'):
            print("SimSetup: auto-login-password")
            socat_process.stdin.write(bytes('Alcateldc!\n', 'utf-8'))
            socat_process.stdin.flush()
        elif line.startswith('switch'):
            showInterface()
        elif line.find('Internet Address is ') != -1:
            m = re.search('  Internet Address is (.*?)/.*', line)
            if m:
                SIM_IP = m.group(1)
            print("Sim %s" % SIM_IP)
            break

    sys.exit()

def usage():
    print("Usage   : %s [Option]" % sys.argv[0])
    print("          Option -help : Show this help message")
    print("                 -name {vm-name} -disk {vpdk-path} : create and start new vm with boot from specified disk")
    print("                 -name {vm-name} -qcow {qcow-path} : create and start new vm with boot from specified disk, which is convered from qcow")
    print("Example : %s -name 'N9K7.3' -d ~/cisco-images/n9k7.3.vmdk" % sys.argv[0])
    sys.exit()

def main(argv):
    global VM_IMAGE

    if VMNAME == '':
        print("Missing name")
        usage()
    elif VM_IMAGE == '' and VM_QCOW == '':
        print("Either qcow or vmdk should be provided")
        usage()
    elif VM_IMAGE == '' and VM_QCOW != '':
        VM_IMAGE=VM_QCOW + '_' + VMNAME + '.vmdk'
        subprocess.run(['qemu-img', 'convert', '-f', 'qcow2', VM_QCOW, '-O', 'vmdk', VM_IMAGE])

    createSim()
    startVM()
    bootConfig()
    print("Cisco Simulator VM Name=%s, IP=%s created successfully" % (VMNAME, SIM_IP))

def signal_handler(sig, frame):
    print('you pressed Ctrl+C!')
    sys.exit(0)

def cleanup():
    print('Stopping all process')
    if socat_process:
        socat_process.terminate()
    print ('cleaned up')

############
### MAIN ###
############
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if "-help" == sys.argv[1]:
            usage()
        elif len(sys.argv) > 2:
            if "-name" == sys.argv[1]:
                VMNAME = sys.argv[2]
            elif "-get" == sys.argv[1]:
                VMNAME = sys.argv[2]
                getConfig()
            if len(sys.argv) > 3:
                if "-disk" == sys.argv[3]:
                    VM_IMAGE = sys.argv[4]
                elif "-qcow" == sys.argv[3]:
                    VM_QCOW = sys.argv[4]
            else:
                usage()
        else:
            usage()
    else:
        usage()

    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    main(sys.argv[1:])
    sys.exit()

