#!/bin/bash

set -e
set -o pipefail
set -x
set -u

ROOT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ASSETS_DIRECTORY="$ROOT_DIRECTORY/assets"

source "$ROOT_DIRECTORY/environment.sh"

# Download the assets.
mkdir -p "$ASSETS_DIRECTORY"
cd "$ASSETS_DIRECTORY"
ia download 3-libjune-05

# Build the index.
cd "$ROOT_DIRECTORY"
pipenv run python3 dumpapps.py library.yaml
