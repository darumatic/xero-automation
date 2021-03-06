#!/bin/bash -e

USAGE="Usage: xero_report.sh --PROJECT_ID=projectId --START_DATE=startTime --END_DATE=startTime --XERO_CONSUMER_KEY=key --XERO_PRIVATE_KEY_FILE=key.pem  --XERO_PRIVATE_KEY=key"
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
PWD=$(pwd)

for i in "$@"
do
case $i in
    --PROJECT_ID=*)
    PROJECT_ID="${i#*=}"
    shift
    ;;
    --START_DATE=*)
    START_DATE="${i#*=}"
    ;;
    --END_DATE=*)
    END_DATE="${i#*=}"
    shift
    ;;
     --DURATION_WEEKS=*)
    DURATION_WEEKS="${i#*=}"
    shift
    ;;
    --XERO_CONSUMER_KEY=*)
    XERO_CONSUMER_KEY="${i#*=}"
    shift
    ;;
    --XERO_PRIVATE_KEY_FILE=*)
    XERO_PRIVATE_KEY_FILE="${i#*=}"
    shift
    ;;
    --XERO_PRIVATE_KEY=*)
    XERO_PRIVATE_KEY="${i#*=}"
    shift
    ;;
    --OUTPUT=*)
    OUTPUT="${i#*=}"
    shift
    ;;
esac
done

if [ -z ${XERO_CONSUMER_KEY+x} ]  || [ -z ${XERO_PRIVATE_KEY_FILE+x} ] && [ -z ${XERO_PRIVATE_KEY+x} ] || [ -z ${PROJECT_ID+x} ]; then
    echo $USAGE
    exit 1
fi

if [ -z ${XERO_PRIVATE_KEY+x} ]; then
    XERO_PRIVATE_KEY=$(cat $XERO_PRIVATE_KEY_FILE)
fi

if [ -z ${START_DATE+x} ]; then
    START_DATE='None'
fi

if [ -z ${END_DATE+x} ]; then
    END_DATE='None'
fi

if [ -z ${DURATION_WEEKS+x} ]; then
    DURATION_WEEKS=2
fi

if [ -z ${OUTPUT+x} ]; then
    OUTPUT=$PWD
fi

if [ -z ${CI_BUILD_REF_NAME+x} ]; then
    git_branch=$(git rev-parse --abbrev-ref HEAD)
else
    git_branch=$CI_BUILD_REF_NAME
fi

echo $OUTPUT

python $BASE_DIR/xero_report.py -p $PROJECT_ID -s $START_DATE -e $END_DATE -u $XERO_CONSUMER_KEY -d $DURATION_WEEKS -o $OUTPUT --key="${XERO_PRIVATE_KEY}"
$BASE_DIR/git_persist.sh $git_branch


