#!/bin/bash

set -e
set -o pipefail
set -x
set -u

ROOT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ENVIRONMENT_PATH="$ROOT_DIRECTORY/environment.sh"

if [ -d "$ROOT_DIRECTORY/.local" ] ; then
    rm -r "$ROOT_DIRECTORY/.local"
fi
source "$ENVIRONMENT_PATH"

# Install the Python dependencies
PIPENV_PIPFILE="$ROOT_DIRECTORY/Pipfile" pipenv install

# Install Internet Archive tools
mkdir -p "$TOOLS_DIRECTORY"
curl -L https://archive.org/download/ia-pex/ia -o "$TOOLS_DIRECTORY/ia"
chmod +x "$TOOLS_DIRECTORY/ia"
