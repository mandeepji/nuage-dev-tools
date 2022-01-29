#!/bin/bash
#set -e
set -o pipefail

for pkg in sshpass virtualbox python-setuptools socat qemu-utils
do
  installed=`apt-cache search ${pkg} | wc -l`
  if [ $installed == 0 ]; then 
    echo $pkg' notinstalled'
    sudo apt-get install $pkg
  else
    echo $pkg' already installed'
  fi
done

sudo easy_install pip
sudo pip install ncclient
