#!/bin/bash

set -e
set -o pipefail
set -x
set -u

ROOT_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ASSETS_DIRECTORY="$ROOT_DIRECTORY/assets"
ASSETS_LIST_PATH="$ROOT_DIRECTORY/assets.txt"

source "$ROOT_DIRECTORY/environment.sh"

# Generate the asset list from the definition.
cd "$ROOT_DIRECTORY"
pipenv run python3 generate-asset-list.py library.yaml

# Download the assets.
mkdir -p "$ASSETS_DIRECTORY"
cd "$ASSETS_DIRECTORY"
ia download --itemlist "$ASSETS_LIST_PATH"

# Build the index.
cd "$ROOT_DIRECTORY"
pipenv run python3 dumpapps.py library.yaml
