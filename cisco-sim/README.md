# Cisco Sim Setup Development Utility Tools
  
## prerequisites

There are few open-source external tools used to run this tool. These tools are:

1. virtualbox

2. qemu-utils (only for -qcow option)

3. socat


## Usage:

```
Usage: cisco-sim-setup.py -name <Name of VM> -disk <vmdk (Virtual Machine Disk Image)>
       cisco-sim-setup.py -name <Name of VM> -qcow <qcow2 (qemu qcow2 Image)>
```

Note: This script is tried only on Ubuntu 18.04LTS but should work on other distributions as well.

