#!/bin/bash

DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
VSD_DIR=""
MYSQL_IP=""
FROM_VERSION=""
TO_VERSION=""
MODE="standard"
MY_IP=`ip addr | grep 'state UP' -A2 | tail -n1 | awk '{print $2}' | cut -f1  -d'/'`

function usage() {
    echo "Usage: $(basename $0) -s <CNA-Server-Path> -i <mysql IP> -f <from version> -t <to version> -m <standard|in_service>"
    echo "Example : $(basename $0) -s /home/mrekhi/work/workspace/CNA-Server -i 135.227.65.198 -f 5.3.2 -t 5.3.3 -m in_service"
}

while getopts s:i:f:t:m: opt; do
  case ${opt} in
    s)
      VSD_DIR=$OPTARG
      ;;
    i)
      MYSQL_IP=$OPTARG
      ;;
    f)
      FROM_VERSION=$OPTARG
      ;;
    t)
      TO_VERSION=$OPTARG
      ;;
    m)
      MODE=$OPTARG
      ;;
    \?)
      usage;
      exit 1
      ;;
  esac
done

if [ "$VSD_DIR" == "" ]; then
    echo "CNA-Server-Path is missing"
    usage;
elif [ "$MYSQL_IP" == "" ]; then
    echo "Mysql IP address is missing"
    usage;
elif [ "$FROM_VERSION" == "" ]; then
    echo "From version is missing"
    usage;
elif [ "$TO_VERSION" == "" ]; then
    echo "To version is missing"
    usage;
elif [ "$MODE" == "standard" ]; then
    echo "CREATE USER cnauser@$MY_IP IDENTIFIED BY 'cnapass';"
    echo "GRANT ALL PRIVILEGES ON * . * TO cnauser@$MY_IP WITH GRANT OPTION;"
    echo "Login to mysql and run above two commands, then press enter to continue..."
    read

    echo "Running standard upgrade test"
    echo "Changing mysql IP to " $MYSQL_IP
    $DIRECTORY/set-mysql-ip.sh -s $VSD_DIR -i $MYSQL_IP

    # TODO workaround
    sed -i "s+CREATE TABLE/CREATE TABLE IF NOT EXISTS+CREATE TABLE/CREATE TABLE+" $VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/db-diff/dbdiff.sh

    cd $VSD_DIR/workspace/CloudMgmt; mvn clean install -Ddbdiff=True -Dbranch.version=$TO_VERSION

    # By default it loads default data which can be overritten using -d CloudMgmt-db/dbdumps/${FROM_VERSION}-data.sql
    cd $VSD_DIR/workspace/CloudMgmt; CloudMgmt-db/upgrade-test.sh -f $FROM_VERSION -t $TO_VERSION 
    echo "Reverting mysql IP changes"
    $DIRECTORY/set-mysql-ip.sh -s $VSD_DIR -i 'localhost'

elif [ "$MODE" == "in_service" ]; then
    echo "CREATE USER dbadmin@$MY_IP IDENTIFIED BY 'Adm1np@ss';"
    echo "GRANT ALL PRIVILEGES ON * . * TO dbadmin@$MY_IP WITH GRANT OPTION;"
    echo "Login to mysql and run above two commands, then press enter to continue..."
    read

    echo "Running in_service upgrade test"
    echo "Changing mysql IP to " $MYSQL_IP
    $DIRECTORY/set-mysql-ip.sh -s $VSD_DIR -i $MYSQL_IP

    # TODO workaround
    sed -i "s+CREATE TABLE/CREATE TABLE IF NOT EXISTS+CREATE TABLE/CREATE TABLE+" $VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/db-diff/dbdiff.sh
    read

    cd $VSD_DIR/workspace/CloudMgmt; mvn clean install -Ddbdiff=True -Dbranch.version=$TO_VERSION

	echo "Restoring vsddb with dbdump as dbDiff deleted during build"
    MYSQL_CMD="mysql -h$MYSQL_IP -udbadmin -pAdm1np@ss"
    INIT_DB_SCHE_IMPORT_FILE=$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/dbdumps/$FROM_VERSION.sql
    INIT_DB_DATA_IMPORT_FILE=$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/dbdumps/$FROM_VERSION-data.sql
	$MYSQL_CMD -e "drop database if exists vsddb;"
	$MYSQL_CMD -e "create database vsddb;"
	echo "import db $INIT_DB_DATA_IMPORT_FILE"
	$MYSQL_CMD vsddb < $INIT_DB_SCHE_IMPORT_FILE
	$MYSQL_CMD vsddb < $INIT_DB_DATA_IMPORT_FILE

    TMP_EXPAND_DIR=$DIRECTORY'/tmp-vsd-expand'
    TMP_LOG_FILE=$TMP_EXPAND_DIR'/opt/vsd/db/vsddb-upgrade.log'
    SCALE_DIR='/home/mrekhi/work/workspace/CNA-Scale'
    echo "Cleaning up temp dir" $TMP_EXPAND_DIR
    rm -rf $TMP_EXPAND_DIR
    mkdir -p $TMP_EXPAND_DIR/opt/vsd/bin
    mkdir -p $TMP_EXPAND_DIR/opt/vsd/scripts
    mkdir -p $TMP_EXPAND_DIR/opt/vsd/sysmon
    mkdir -p $TMP_EXPAND_DIR/opt/vsd/password
    mkdir -p $TMP_EXPAND_DIR/opt/vsd/db

    echo "Copying expand schema setup..."
    cp $SCALE_DIR/online_schema_migration/scripts/vsd-online-schema-migration-expand $TMP_EXPAND_DIR/opt/vsd/bin/.
    cp $SCALE_DIR/scripts/* $TMP_EXPAND_DIR/opt/vsd/scripts/.
    cp $SCALE_DIR/password/* $TMP_EXPAND_DIR/opt/vsd/password/.
    cp $SCALE_DIR/sysmon/src/constants.py $TMP_EXPAND_DIR/opt/vsd/sysmon/.
    cp -r $SCALE_DIR/online_schema_migration $TMP_EXPAND_DIR/opt/vsd/db/.

    echo "Changing mysql IP to " $MYSQL_IP
    $DIRECTORY/set-mysql-ip.sh -s $VSD_DIR -i $MYSQL_IP

    cp -r $VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/* $TMP_EXPAND_DIR/opt/vsd/db/.

    # edit log file location
    sed -i "s+/opt/vsd/db/vsddb-upgrade.log+$TMP_LOG_FILE+" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/migration_constants.py

    #TODO move below in set-mysql-ip file if path has been given
    sed -i "s/show grants for '{}'@'localhost'/show grants for '{}'@$MYSQL_IP/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/vsd_online_schema_migration_expand.py
    sed -i "s/grant all privileges on *.* to 'dbadmin'@'localhost'/grant all privileges on *.* to 'dbadmin'@'$MYSQL_IP'/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/migration_constants.py
    sed -i "s/mysql --user={} --password={}/mysql --host=$MYSQL_IP --user={} --password={}/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/vsd_online_schema_migration_base.py
    sed -i "s/mysql --user={} --password={}/mysql --host=$MYSQL_IP --user={} --password={}/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/vsd_online_schema_migration_expand.py
    sed -i "s/mysql --user={} --password={}/mysql --host=$MYSQL_IP --user={} --password={}/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/vsd_online_schema_migration_reduce.py
    sed -i "s/mysql --user={} --password={}/mysql --host=$MYSQL_IP --user={} --password={}/" $TMP_EXPAND_DIR/opt/vsd/db/online_schema_migration/scripts/migration_util.py

    echo "Reverting mysql IP changes in workspaces (not needed as already copied to local dir)"
    $DIRECTORY/set-mysql-ip.sh -s $VSD_DIR -i 'localhost'

    # finally run the expand script
    $TMP_EXPAND_DIR/opt/vsd/bin/vsd-online-schema-migration-expand
fi


