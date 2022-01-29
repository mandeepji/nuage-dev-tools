# VSD VM Setup Development Utility Tools
  
## prerequisites

There are few open-source external tools used to run this tool. These tools are:

virtualbox

sshpass

## 1. vsd-setup-tool

Contains scripts to setup vsd server

```
Usage: vsd-dev-setup.sh [-n -p <port-prefix>] -c <IP address>
       vsd-dev-setup.sh [-n -p <port-prefix>] -f [-v <version>] [-b <branch>]
Options:
       c) change config. Changes system config in remote machine at <IP address>.
       f) full VSD VM.   Downloads <branch> or latest for <version> or 0.0 ova,
                         create VM, change VM and start install script in local machine.
       n) NAT IP config. Configures NAT network adapter with port-forwarding instead of bridge adapter.
       p) Port prefix.   Port prefix for NAT network port-forwarding. See example below:
                         Example if port-prefix = 2,3,4 or 5, flowwing port-forwarding will be added,
                         |---------------|-------|---------|---------------|-------------|------------|
                         |  port-prefix  |   ssh |  https  |  jboss_debug  |  med_debug  |  xmpp_sim  |
                         |---------------|-------|---------|---------------|-------------|------------|
                         |            2  |  2022 |   2443  |         2787  |       2005  |      2222  |
                         |   default  3  |  3022 |   3443  |         3787  |       3005  |      3222  |
                         |            4  |  4022 |   4443  |         4787  |       4005  |      4222  |
                         |            5  |  5022 |   5443  |         5787  |       5005  |      5222  |
                         |            6  |  6022 |   5443  |         6787  |       6005  |      6222  |
                         |            7  |  7022 |   5443  |         7787  |       7005  |      7222  |
                         |---------------|-------|---------|---------------|-------------|------------|
```

### usage 1:

Changes system config in remote machine at given IP address.

```
vsd-setup-tool/vsd-dev-setup.sh [-n -p <port-prefix>] -c <IP address>
```

**Note:** If executed with '-n' option, then uses port-forwarding to login for configuration. Additionally -p <prefix> can be given while creating multiple instances. See usage above.

### usage 2:

Full setup. Downloads <branch> (or latest) from <version> (or 0.0) ova, create VM, change VM and start install script in local machine.

```
vsd-setup-tool/vsd-dev-setup.sh [-n] -f [-v <version>] [-b <branch>]
```

**Note:** If executed with '-n' option, then adds port-forwarding configuration and uses port-forwarding to login for configuration.
