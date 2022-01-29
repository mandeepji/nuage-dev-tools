#!/bin/bash
#set -e

###############################################################################
## Usage: git_spotbugs.sh [<base branch>]                                    ##
##   Script to generate spotbugs report for local modified/added files       ##
##   <base branch>: Report will be gerated for PR (committed changes in PR)  ##
##                                                                           ##
##  Output can be viewed/navigated in spotbugs-gui                           ##
##       https://spotbugs.readthedocs.io/en/stable/installing.html           ##
###############################################################################

SB_OUT_FILE=./target/spotbugsXml.xml
OUTPUT_FILE=/tmp/git-spotbugs-output.xml
SEARCH_STR='/src/main/java/'
dir=${PWD##*/}

# spotbug build will generate report at ./target/spotbugsXml.xml
mvn spotbugs:spotbugs -Dspotbugs.maxHeap=3000

# list of git modified files
if [ $# -eq 0 ]
then
    git_files=`git diff --name-only HEAD`
else
    git_current_branch=`git rev-parse --abbrev-ref HEAD`
    git_files=`git diff --name-only $1..$git_current_branch`
fi

git_modules=()
if [[ $dir == "CloudMgmt" ]]; then
    git_modules=()
    for file in ${git_files}
    do
        module=${file%$SEARCH_STR*}
        module=${module##*/}
        git_modules+=( "$module" )
    done
fi

# $1=git_file, $2=$module, $3=prj_dir $4=input_file
get_bug_instances () {
    source_path=${1#*$SEARCH_STR}
    out=$(xmllint --xpath '//BugInstance[Class/SourceLine[@sourcepath="'${source_path}'"]]' ./$module/$SB_OUT_FILE)
    project='<Project><SrcDir>'$3'</SrcDir><WrkDir>'$3'</WrkDir></Project><ShortMessage>'
    echo ${out//'<ShortMessage>'/$project}
}

# generate output xml
echo '<BugCollection sequence="0" release="" analysisTimestamp="'$(date +%s)'" version="3.1.7" timestamp="'$(date +%s)'">' > $OUTPUT_FILE

if [[ $dir == "CloudMgmt" ]]; then
    for module in ${git_modules[@]}
    do
        echo "Processing module:"$module
        for file in ${git_files}
        do
            if [[ $file == *"${module}${SEARCH_STR}"* ]]; then
                echo $(get_bug_instances $file $module ${PWD}/${module}${SEARCH_STR}) >> $OUTPUT_FILE
            fi
        done
    done
else
    for file in ${git_files}
    do
        if [[ $file == *"${dir}${SEARCH_STR}"* ]]; then
            echo $(get_bug_instances $file '.' ${PWD}${SEARCH_STR}) >> $OUTPUT_FILE
        fi
    done
fi

echo '</BugCollection>' >> $OUTPUT_FILE
echo 'Spotbugs diff file is generated at '$OUTPUT_FILE

