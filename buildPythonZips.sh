#!/bin/bash
BRANCH="test"
if [ "$1" == "master" ]; then
    BRANCH="prod"
fi
echo "Zipping packages for $BRANCH"

cd python;

if [ $? == 0 ]; then
    echo "Completed OK"
    # for each zip file, upload it to s3 to the correct bucket
fi