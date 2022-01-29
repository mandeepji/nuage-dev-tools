# DB-Upgrade Development Utility Tools
  
## prerequisites

This tool will require follwoing:

1. iptables disabled in machine having mysql

2. Mysql DB user cnauser/cnapass created and granted permission
```
CREATE USER cnauser@$DEV_MC_IP IDENTIFIED BY 'cnapass';
GRANT ALL PRIVILEGES ON * . * TO cnauser@DEV_MC_IP;
```

3. DB-Solo installed on development machine
https://github.mv.usa.alcatel.com/CNA/CNA-Server/wiki/DB-Upgrade#db-solo-licenses

## db-upgrade-tool

### Run DB-upgrade (this script builds dbdiff and upgrade mysql)
NOTE: This script expects the DB is in old version and data has been populated
```
db-upgrade-tool/run-db-upgrade.sh -s <CNA-Server-Path> -i <mysql IP> -f <from_version> -t <to_version>
Example: ./run-db-upgrade.sh -s /home/mrekhi/work/workspace/CNA-Server -i 10.31.101.36 -f 5.3.3 -t 5.4.1
```

### Utility script to set remote mysql IP (like VSD running in NOC) in CNA-Server project to develop and test VSD upgrade.

```
db-upgrade-tool/set-mysql-ip.sh -s <CNA-Server-Path> -i <mysql IP>
```

