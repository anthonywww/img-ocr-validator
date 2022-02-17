#!/bin/bash

ARGS="${ARGS}"

if [ "$#" -gt 0 ]; then
	ARGS="$@"
fi

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo -e "$(tput bold)$(tput setaf 1)Python is not installed, please install python3!$(tput sgr0)"
    exit 1
fi

python3 src/imgocrvalidator.py ${ARGS}

