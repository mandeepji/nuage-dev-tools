#!/bin/bash
#set -e
set -o pipefail

DIR="$( cd -P "$( dirname "$0" )" && pwd )"
TMP_DIR="/tmp/vsd_dev_setup"
IMG_OVA_NAME=''
VM_IP=''
NOCVM_IP=$1
MY_IP=`ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1'`
PORT_PREFIX=3

function setenv {
    echo "Script dir="$DIR
    echo "Temporary Dir="$TMP_DIR
    VSD_BUILD_IMAGE_URL='https://intranet.mv.nuagenetworks.net/images/vsd/'${VERSION}'/'${BRANCH}'/'
    VSD_BUILD_IMAGE_DIR=$TMP_DIR'/intranet.mv.nuagenetworks.net/images/vsd/'${VERSION}'/'${BRANCH}'/'
    echo "VSD Build URL="$VSD_BUILD_IMAGE_URL

    if [ ! -d $TMP_DIR ]; then
        mkdir $TMP_DIR
    fi
    rm -rf $TMP_DIR/*
    rm -rf ~/.ssh/known_hosts
}

function downloadOVA {
    echo "Enter ova file location or press enter to download:"
    read OVA_FILE_LOCATION
    if [ "$OVA_FILE_LOCATION" == "" ]; then
        echo "Downloading OVA image file from" $VSD_BUILD_IMAGE_URL "to" $TMP_DIR
        wget --no-check-certificate --directory-prefix=$TMP_DIR --user=$USER --ask-password --accept *.ova -r --no-parent $VSD_BUILD_IMAGE_URL
    else
        mkdir -p $VSD_BUILD_IMAGE_DIR
        cp $OVA_FILE_LOCATION $VSD_BUILD_IMAGE_DIR/
    fi
    return $?
}

function importVM {
IMG_OVA_FILE=`ls -lrt "$VSD_BUILD_IMAGE_DIR"* | awk '{print $9}'`
IMG_OVA_NAME=$(basename -- "$IMG_OVA_FILE")
IMG_OVA_NAME="${IMG_OVA_NAME%.*}"
    echo "OVA File="$IMG_OVA_FILE
    echo "OVA File Name="$IMG_OVA_NAME

    vboxmanage list vms | grep $IMG_OVA_NAME &> /dev/null
    if [ $? == 0 ]; then
	echo "Image "$IMG_OVA_NAME" already present in your virtual box. If you want fresh then delete that first."
	exit 1
    fi

    echo "Importing VSD VM Image" $IMG_OVA_NAME 
    vboxmanage import $IMG_OVA_FILE --vsys 0 --vmname $IMG_OVA_NAME --memory 8192 --cpus 3
    return $?
}

function modifyVM() {
    if [ "$NAT_CONFIG" == "yes" ]; then
      vboxmanage modifyvm $IMG_OVA_NAME --nic1 nat --natpf1 "ssh_rule,tcp,,${PORT_PREFIX}022,,22"
      vboxmanage modifyvm $IMG_OVA_NAME --nic1 nat --natpf1 "vsd_client_rule,tcp,,${PORT_PREFIX}443,,8443"
      vboxmanage modifyvm $IMG_OVA_NAME --nic1 nat --natpf1 "jboss_debug_rule,tcp,,${PORT_PREFIX}787,,8787"
      vboxmanage modifyvm $IMG_OVA_NAME --nic1 nat --natpf1 "med_debug_rule,tcp,,${PORT_PREFIX}005,,5005"
      return $?
    fi
    return 0
}

function startVM() {
    vboxmanage startvm $IMG_OVA_NAME
    return $?
}

function waitForBoot {
    VM_HOSTNAME=`hostname`"-vm.mylocalvm"
    echo "Local VM Hostname="$VM_HOSTNAME
    # FIXME Get IP address of VM
    echo "Login into VM and give me IP address of VM:"
    read VM_IP
    if [[ $VM_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      return 0
    else
      echo "Invalid IP. Rerun this script with '-c <IP>' to configure VM"
      return 1
    fi
}

function changeConfig {
if [[ $VM_HOSTNAME == "localhost.localdomain" ]]; then
    echo "Login into VM and give me hostname of VM:"
    read VM_HOSTNAME
fi
echo 'Changing configuration in IP='$VM_IP' Host='${VM_HOSTNAME}
TEMP_IP=$VM_IP
TEMP_PORT=22
if [ "$NAT_CONFIG" == "yes" ]; then
    TEMP_IP=$MY_IP
    TEMP_PORT=${PORT_PREFIX}022
fi
sshpass -p 'Alcateldc' ssh root@$TEMP_IP -p $TEMP_PORT -q << EOF
grep -q -F 'HOSTNAME=$VM_HOSTNAME' /etc/sysconfig/network || echo "HOSTNAME=$VM_HOSTNAME" >> /etc/sysconfig/network
hostname $VM_HOSTNAME
grep -q -F '$VM_IP $VM_HOSTNAME' /etc/hosts || echo "$VM_IP $VM_HOSTNAME" >> /etc/hosts
service network restart

grep -q -F 'nameserver 135.227.208.143' /etc/resolv.conf || echo "nameserver 135.227.208.143" >> /etc/resolv.conf
grep -q -F 'tos orphan 6 minclock 2 maxclock 3' /etc/ntp.conf || echo "tos orphan 6 minclock 2 maxclock 3" >> /etc/ntp.conf
grep -q -F 'server 152.148.152.38' /etc/ntp.conf || echo "server 152.148.152.38" >> /etc/ntp.conf

service ntpd stop
sleep 5
service ntpd start
sleep 5

MY_IF=\`ifconfig -a | sed -n 1p | awk '{print \$1}' | sed 's/:\$//'\`;ip link set dev \$MY_IF down; ip link set dev \$MY_IF name eth0; ip link set dev eth0 up
EOF
}

function deployrc {
echo 'Creating .vsdrc and deploying'
TEMP_IP=$VM_IP
TEMP_PORT=22
if [ "$NAT_CONFIG" == "yes" ]; then
    TEMP_IP=$MY_IP
    TEMP_PORT=${PORT_PREFIX}022
fi
echo $TEMP_IP  $TEMP_PORT
sshpass -p 'Alcateldc' ssh root@$TEMP_IP -p $TEMP_PORT -q << EOF
echo "cd /opt/vsd" > ~/.vsdrc

echo "" >> ~/.vsdrc
echo "## alias" >> ~/.vsdrc
echo "alias vi='vim'" >> ~/.vsdrc

echo '' >> ~/.vsdrc
echo 'export LC_ALL="en_US.UTF-8"' >> ~/.vsdrc
echo '' >> ~/.vsdrc

echo "## monit alias" >> ~/.vsdrc
echo "alias msummary='monit summary'" >> ~/.vsdrc
echo "alias mjboss-start='monit start jboss'" >> ~/.vsdrc
echo "alias mjboss-stop='monit stop jboss'" >> ~/.vsdrc
echo "alias al='wget https://raw.githubusercontent.com/sunilvp/alias/master/alias.sh  -O /tmp/aliases; chmod +x /tmp/aliases'" >> ~/.vsdrc

echo "if [ -f \\"/tmp/aliases\\" ]; then" >> ~/.vsdrc
echo "    source /tmp/aliases" >> ~/.vsdrc
echo "else" >> ~/.vsdrc
echo "    al" >> ~/.vsdrc
echo "    source /tmp/aliases" >> ~/.vsdrc
echo "fi" >> ~/.vsdrc

echo '' >> ~/.vsdrc
echo '## functions' >> ~/.vsdrc
echo 'function clslog {' >> ~/.vsdrc
echo '  if [ "\$1" == "" ]; then' >> ~/.vsdrc
echo '    truncate -s 0 ./*.log &> /dev/null;' >> ~/.vsdrc
echo '  else' >> ~/.vsdrc
echo '    truncate -s 0 \$1/*.log &> /dev/null;' >> ~/.vsdrc
echo '  fi' >> ~/.vsdrc
echo '}' >> ~/.vsdrc

echo '' >> ~/.vsdrc
echo 'function keygrep {' >> ~/.vsdrc
echo '    keytool -list -v -keystore \$1 -storepass Alcateldc | grep \$2;' >> ~/.vsdrc
echo '}' >> ~/.vsdrc

echo '' >> ~/.vsdrc
echo 'function netconfsetup {' >> ~/.vsdrc
echo '    echo "Generating certificates for netconf manager"' >> ~/.vsdrc
echo '    /opt/vsd/ejbca/deploy/certMgmt.sh -a generate -c netconfmgr -u netconfmgr -o csp -f jks -t client -p netconfmgr' >> ~/.vsdrc
echo '    echo "Cerificates can be copied from /opt/vsd/ejbca/p12/netconfmgr.jks /opt/vsd/jboss/standalone/configuration/vsd.truststore"' >> ~/.vsdrc
echo '    if [ -d "/opt/netconfmanager/conf" ]; then' >> ~/.vsdrc
echo '        cp /opt/vsd/ejbca/p12/netconfmgr.jks /opt/netconfmanager/conf/.' >> ~/.vsdrc
echo '        cp /opt/vsd/jboss/standalone/configuration/vsd.truststore /opt/netconfmanager/conf/.' >> ~/.vsdrc
echo '        MYIP=\`hostname -i\` ' >> ~/.vsdrc
echo '        sed -i "s/jms.host=.*/jms.host="\$MYIP"/" /opt/netconfmanager/conf/netconfmanager.properties' >> ~/.vsdrc
echo '        sed -i "s/vsd.host=.*/vsd.host="\$MYIP"/" /opt/netconfmanager/conf/netconfmanager.properties' >> ~/.vsdrc
echo '    fi' >> ~/.vsdrc
echo '}' >> ~/.vsdrc

echo '' >> ~/.vsdrc
echo 'function enabledebug {' >> ~/.vsdrc
echo '    echo "Enabling debug"' >> ~/.vsdrc
echo '    sed -i "s/DEBUG_MODE=false/DEBUG_MODE=true/" /etc/init.d/mediator.sh' >> ~/.vsdrc
echo '    sed -i "s/DEBUG_MODE=false/DEBUG_MODE=true/" /opt/vsd/mediator/mediator.sh' >> ~/.vsdrc
echo '    sed -i "s/DEBUG_MODE=false/DEBUG_MODE=true/" /opt/vsd/jboss/bin/standalone.sh' >> ~/.vsdrc
echo '}' >> ~/.vsdrc

echo "alias cl='clslog /opt/vsd/jboss/standalone/log/'" >> ~/.vsdrc
echo "alias dvsd='\\cp -rf /opt/vsd/mandy/CloudMgmt-ear-\$VSD_VERSION-SNAPSHOT.ear /opt/vsd/jboss/standalone/deployments/CloudMgmt-ear-\$VSD_BUILD.ear ; \\cp -rf /opt/vsd/mandy/CloudMgmt-api-\$VSD_VERSION-SNAPSHOT.jar /opt/vsd/jboss/modules/system/layers/base/com/alu/cna/cloudmgmt/main/CloudMgmt-api-\$VSD_BUILD.jar; \\cp -rf /opt/vsd/mandy/tplibsrv-ear-\$VSD_VERSION-SNAPSHOT.ear /opt/vsd/jboss/standalone/deployments/tplibsrv-ear-\$VSD_BUILD.ear'" >> ~/.vsdrc

grep -q -F '. ~/.vsdrc' ~/.bashrc || echo "if [ -f ~/.vsdrc ]; then . ~/.vsdrc; fi" >> ~/.bashrc
EOF
}

############
### MAIN ###
############
while getopts b:c:d:fnp:v: opt; do
  case ${opt} in
    b)
      BRANCH=$OPTARG
      ;;
    c)
      ACTION="CONFIG_CHANGE"
      VM_IP=$OPTARG
      if [ "$NAT_CONFIG" != "yes" ]; then
        VM_HOSTNAME=`sshpass -p 'Alcateldc' ssh root@$VM_IP 'hostname'`
      else
        VM_HOSTNAME=`hostname`"-vm.mylocalvm"
      fi
      ;;
    d)
      ACTION="DEPLOY_RC"
      VM_IP=$OPTARG
      ;;
    f)
      ACTION="FULL_SETUP"
      VERSION='0.0'
      BRANCH='latest'
      ;;
    n)
      NAT_CONFIG="yes"
      ;;
    p)
      PORT_PREFIX=$OPTARG
      ;;
    v)
      VERSION=$OPTARG
      ;;
    \?)
      echo "Usage: $(basename $0) [-n -p <port-prefix>] -c <IP address>"
      echo "       $(basename $0) [-n -p <port-prefix>] -f [-v <version>] [-b <branch>]"
      echo "Options:"
      echo "       c) change config. Changes system config in remote machine at <IP address>."
      echo "       f) full VSD VM.   Downloads <branch> or latest for <version> or 0.0 ova,"
      echo "                         create VM, change VM and start install script in local machine."
      echo "       n) NAT IP config. Configures NAT network adapter with port-forwarding instead of bridge adapter."
      echo "       p) Port prefix.   Port prefix for NAT network port-forwarding. See example below:"
      echo "                         Example if port-prefix = 2,3,4 or 5, flowwing port-forwarding will be added,"
      echo "                         |---------------|-------|---------|---------------|-------------|------------|"
      echo "                         |  port-prefix  |   ssh |  https  |  jboss_debug  |  med_debug  |  xmpp_sim  |"
      echo "                         |---------------|-------|---------|---------------|-------------|------------|"
      echo "                         |            2  |  2022 |   2443  |         2787  |       2005  |      2222  |"
      echo "                         |   default  3  |  3022 |   3443  |         3787  |       3005  |      3222  |"
      echo "                         |            4  |  4022 |   4443  |         4787  |       4005  |      4222  |"
      echo "                         |            5  |  5022 |   5443  |         5787  |       5005  |      5222  |"
      echo "                         |            6  |  6022 |   5443  |         6787  |       6005  |      6222  |"
      echo "                         |            7  |  7022 |   5443  |         7787  |       7005  |      7222  |"
      echo "                         |---------------|-------|---------|---------------|-------------|------------|"
      exit 1
      ;;
  esac
done

if [ "$ACTION" == "CONFIG_CHANGE" ]; then
  #echo 'Changing configuration in IP='$VM_IP' Host='${VM_HOSTNAME}
  if changeConfig ; then
    echo "Config changes successful"
  else
    echo "Change config failed"
    exit 1
  fi
  #echo 'Creating .vsdrc and deploying'
  if deployrc ; then
    echo ".vsdrc deployed successful"
  else
    echo ".vsdrc deployment failed"
    exit 1
  fi
elif [ "$ACTION" == "DEPLOY_RC" ]; then
  #echo 'Creating .vsdrc and deploying'
  if deployrc ; then
    echo ".vsdrc deployed successful"
  else
    echo ".vsdrc deployment failed"
    exit 1
  fi
elif [ "$ACTION" == "FULL_SETUP" ]; then
  echo "Setting up full VSD VM of $VERSION"
  if setenv && downloadOVA && importVM && modifyVM && startVM && waitForBoot && changeConfig && deployrc ; then
    echo "Full VSD VM is successful"
    echo "Login to VM ($VM_IP) and run /opt/vsd/install.sh to install vsd."
  else
    echo "Full VSD VM is failed, see above for errors."
  fi
fi

