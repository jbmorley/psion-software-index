#!/bin/bash

ROOT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

export PYTHONUSERBASE="$ROOT_DIRECTORY/.local/python"
mkdir -p "$PYTHONUSERBASE"
export PATH="$PYTHONUSERBASE/bin":$PATH

export TOOLS_DIRECTORY="$ROOT_DIRECTORY/.local/bin"

export PATH=$PATH:$TOOLS_DIRECTORY
