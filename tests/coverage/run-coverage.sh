#!/usr/bin/env sh

TEST_SCRIPT="$1.py"
TEST_DIRECTORY=".."
HTML_DIRECTORY="coverage/html/$1"

cd $TEST_DIRECTORY
mkdir -p $HTML_DIRECTORY
coverage run $TEST_SCRIPT

if [ $? == 0 ]; then
    coverage html --directory $HTML_DIRECTORY
    coverage report
fi
