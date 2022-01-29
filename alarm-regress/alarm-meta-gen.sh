#!/bin/bash

#####################################################################
# If this script run with alarm-spec location (first arg)
#    then generates alarm-spec-meta file
# Else it generates alarm message dump from mysql-db in xmpp format
#####################################################################

spec_meta_file='./alarm-spec-meta'
alarm_message_dump_file='./alarm-messages-dump.xml'

getValue()
{
value=`cat $1 | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/\042'$2'\042/){print $(i+1)}}}' | tr -d '"' | sed -n p`
echo $value
}
if [[ "$1" == *alarm-specifications* ]]
then
    spec_files="$1/*.spec"
    echo "Generating alarm-spec-meta from alarm-specs"
    echo "" > $spec_meta_file
    for spec_file in $spec_files
    do
        type=`getValue $spec_file "alarmed-object-type"`
        code=`getValue $spec_file "code"`
        title=`getValue $spec_file "title"`
        severity=`getValue $spec_file "severity"`
        auto_clear=`getValue $spec_file "auto-clear"`
        from=`getValue $spec_file "supported-from"`
        if [ -z "$from" ]; then
          from="0.0.0"
        fi 
        echo '#'$type'##'$code#$from#$severity#$auto_clear#$title >> $spec_meta_file
    done
else
    echo "Generating alarm-message-dumps"
    rm $alarm_message_dump_file
    touch $alarm_message_dump_file
    echo "<messages>" > $alarm_message_dump_file
    while IFS= read -r line
    do
      IFS=# read var1 type table code version <<< $line
      ids=($(mysql vsddb -e "select id from $table"))
      if [[ ${#ids[@]} > 1 ]]
      then
          for id in "${ids[@]}"
          do
              if [[ $id != "id" ]]
              then
                  echo "Dumping message for code=$code type=$type id=$id"
                  echo -n "    <nuage xmlns='alu:nuage:message'>" >> $alarm_message_dump_file
                  echo -n "<cloudmgmt xmlns='http://www.nuagenetworks.net/2013/controller/Request' version='6.0.2' nodeType='VSC'>" >> $alarm_message_dump_file
                  echo -n "<message xmlns='http://www.nuagenetworks.net/2013/controller/Message' type='ERROR'>" >> $alarm_message_dump_file
                  echo -n "<error>" >> $alarm_message_dump_file
                  echo -n "<entity-key>$type#$id</entity-key>" >> $alarm_message_dump_file
                  echo -n "<alarm-code>$code</alarm-code>" >> $alarm_message_dump_file
                  echo -n "</error>" >> $alarm_message_dump_file
                  echo -n "</message>" >> $alarm_message_dump_file
                  echo -n "</cloudmgmt>" >> $alarm_message_dump_file
                  echo -n "</nuage>" >> $alarm_message_dump_file
                  echo "" >> $alarm_message_dump_file
              fi
          done
      fi
    done < "$spec_meta_file"
    echo "</messages>" >> $alarm_message_dump_file
fi
