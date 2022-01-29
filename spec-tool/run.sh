#!/bin/bash

DIRECTORY=`dirname $0`
SPEC_DIR=""
ENTITY_DIR=""

function usage() {
    echo "Usage: $(basename $0) -s <API Spec File/Dir> -e <Entity Java File/Dir>"
}

while getopts s:e: opt; do
  case ${opt} in
    s)
      SPEC_DIR=$OPTARG
      ;;
    e)
      ENTITY_DIR=$OPTARG
      ;;
    \?)
      usage;
      exit 1
      ;;
  esac
done

if [ "$SPEC_DIR" == "" ]; then
    echo "Spec file or dir is missing"
    usage;
elif [ "$ENTITY_DIR" == "" ]; then
    echo "Entity file or dir is missing"
    usage;
else
    java -classpath "$DIRECTORY/vsd-spec-plugin/lib/*" com.nokia.nuage.vsd.plugin.spec.ui.Main -s $SPEC_DIR -j $ENTITY_DIR
fi
