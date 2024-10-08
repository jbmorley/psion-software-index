#!/bin/bash

# Copyright (c) 2024 Jason Morley
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

SCRIPTS_DIRECTORY="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

ROOT_DIRECTORY="$SCRIPTS_DIRECTORY/.."
TOOLS_DIRECTORY="$ROOT_DIRECTORY/tools"

export PYTHONUSERBASE="$ROOT_DIRECTORY/.local/python"
mkdir -p "$PYTHONUSERBASE"
export PATH="$PYTHONUSERBASE/bin":$PATH

export PIPENV_VENV_IN_PROJECT=1

export GEM_HOME="${ROOT_DIRECTORY}/.local/ruby"
mkdir -p "$GEM_HOME"
export PATH="${GEM_HOME}/bin":$PATH

export BIN_DIRECTORY="$ROOT_DIRECTORY/.local/bin"
export PATH=$BIN_DIRECTORY:$PATH

export PATH=$TOOLS_DIRECTORY:$PATH
