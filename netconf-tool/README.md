# Netconf Development Utility Tools
  
## prerequisites

There are few open-source external tools used to run this tool. These tools are:

1. python ncclient (pip install ncclient)

## netconf-tool

### usage 1:

Contains scripts for connectiong netconf devices (as client) to fetch details based on filters.

```
Usage:
netconf-tool/client/netconf-get-request.py -h|host <Device IP Address> [Options]
Options: -h|--host      : IP address of netconf device
         -u|--username  : netconf username [default= netconf ]
         -p|--password  : netconf password [default= tigris ]
         -f|--filter    : xml file having netconf filter (samples are in filters dir)
         -v|--values    : json as key-value. values will be used to replace keys in filter xml file
         -n|--namespace : xml namespace
```

### usage 2:

Contains postman REST request scripts to initial setup netconf manager config in VSD.
```
Step 1: Import collection netconf-tool/vsd-netconf-setup-collection.json into postman.
Step 2: Create an environment variable name=URL_API current-value=https://<VSD_IP_ADDRESS>:8443/nuage/api/v5_0
Step 3: Run collection 'VSD-Netconf-Setup'

```

