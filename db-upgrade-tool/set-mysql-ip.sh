#!/bin/bash

DIRECTORY=`dirname $0`
VSD_DIR=""
MYSQL_IP=""

while getopts s:i: opt; do
  case ${opt} in
    s)
      VSD_DIR=$OPTARG
      ;;
    i)
      MYSQL_IP=$OPTARG
      ;;
    \?)
      usage;
      exit 1
      ;;
  esac
done

declare -A FILE_OBJ1=(
    [file]="${VSD_DIR}/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/conf/nuageFlyway.properties.template"
    [str1]="^flyway.url=jdbc:mysql:\/\/localhost:3306"
    [str2]="flyway.url=jdbc:mysql:\/\/${MYSQL_IP}:3306"
)
declare -A FILE_OBJ2=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/1-vsddb-status.sh"
    [str1]="^MYSQLHOST="
    [str2]="MYSQLHOST=${MYSQL_IP}"
)
declare -A FILE_OBJ3=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/vsddb-upgrade.sh"
    [str1]="^MYSQLHOST="
    [str2]="MYSQLHOST=${MYSQL_IP}"
)
declare -A FILE_OBJ4=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/pom.xml"
    [str1]="<database-hostname>localhost<\/database-hostname>"
    [str2]="<database-hostname>${MYSQL_IP}<\/database-hostname>"
)
declare -A FILE_OBJ5=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/saas/db_util.py"
    [str1]="host = \"localhost\""
    [str2]="host = \"${MYSQL_IP}\""
)
declare -A FILE_OBJ6=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/commandline/flyway-commandline-2.0/constraints_migration.py"
    [str1]="host = \"localhost\""
    [str2]="host = \"${MYSQL_IP}\""
)
declare -A FILE_OBJ7=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/upgrade-test.sh"
    [str1]="MYSQL_CMD=\"mysql -u\$USER_NAME -p\$PASSWORD\""
    [str2]="MYSQL_CMD=\"mysql -h ${MYSQL_IP} -u\$USER_NAME -p\$PASSWORD\""
)
declare -A FILE_OBJ8=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/upgrade-test.sh"
    [str1]="mysql -u\$USER_NAME -p\$PASSWORD -s -b -e \"select 1 from mysql.user\" > \/dev\/null 2>\&1"
    [str2]="mysql -h ${MYSQL_IP} -u\$USER_NAME -p\$PASSWORD -s -b -e \"select 1 from mysql.user\" > \/dev\/null 2>\&1"
)
declare -A FILE_OBJ9=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/db-diff/dbdiff.sh"
    [str1]="HOST=\"localhost\";"
    [str2]="HOST=\"${MYSQL_IP}\";"
)
declare -A FILE_OBJ10=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/db-diff/dbdiff.sh"
    [str1]="mysqldump --skip-dump-date --no-data --log-error=\$dbdumperrorlog \${MYSQLUSER\/-u\/-u } \$MYSQLPASS \"$SRCDB\" >> \"\$dbdumpfile\""
    [str2]="mysqldump -h ${MYSQL_IP} --skip-dump-date --no-data --log-error=\$dbdumperrorlog \${MYSQLUSER\/-u\/-u } $MYSQLPASS \"$SRCDB\" >> \"$dbdumpfile\""
)
declare -A FILE_OBJ11=(
    [file]="$VSD_DIR/workspace/CloudMgmt/CloudMgmt-db/db-diff/dbdiff.sh"
    [str1]="SERVER=\"no\";"
    [str2]="SERVER=\"yes\";"
)

#str1 = $BASEDIR/db-diff/dbdiff.sh -from $INIT_VERSION
#str2 = $BASEDIR/db-diff/dbdiff.sh -from $INIT_VERSION -dbserver 10.31.101.36


function usage() {
    echo "Usage: $(basename $0) -s <CNA-Server-Path> -i <mysql IP>"
    echo "Example : $(basename $0) -s /home/mrekhi/work/workspace/CNA-Server -i 135.227.65.198"
}

if [ "$VSD_DIR" == "" ]; then
    echo "CNA-Server-Path is missing"
    usage;
elif [ "$MYSQL_IP" == "" ]; then
    echo "Mysql IP address is missing"
    usage;
else
    declare -n FILE_OBJ
    for FILE_OBJ in ${!FILE_OBJ@}; do
        FILE=${FILE_OBJ[file]}
        STR1=${FILE_OBJ[str1]}
        STR2=${FILE_OBJ[str2]}
        #echo Updating file $FILE with $STR1
        if [ 'localhost' == $MYSQL_IP ]
        then
            cd $VSD_DIR; git checkout -- $FILE
        else
            sed -i "s/$STR1/$STR2/" $FILE
        fi
    done
fi


