#!/bin/bash

# Change directory to the current script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

# Check if maven is installed
if ! command -v mvn &> /dev/null; then
    echo -e "$(tput bold)$(tput setaf 1)Maven is not installed, please install maven!$(tput sgr0)"
    exit 1
fi

docker build -t img-ocr-validator .

