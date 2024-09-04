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

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile

TOOLS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ROOT_DIRECTORY = os.path.dirname(TOOLS_DIRECTORY)
OPOLUA_DIRECTORY = os.path.join(ROOT_DIRECTORY, "dependencies", "opolua")
DUMPAIF_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpaif.lua")
DUMPSIS_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpsis.lua")
RECOGNIZE_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "recognize.lua")

UNSUPPORTED_MESSAGE = "Only ER5 SIS files are supported"
NOT_AN_AI_MESSAGE = "Not an AIF file"


class InvalidInstaller(Exception):
    pass


class InvalidAIF(Exception):
    pass


class Image(object):

    def __init__(self, width, height, bpp, data):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.data = data


def run_json_command(command, path):
    result = subprocess.run(["lua", command, "--json", path], capture_output=True)
    stdout = result.stdout.decode('utf-8')
    stderr = result.stderr.decode('utf-8')

    if UNSUPPORTED_MESSAGE in stdout + stderr:
        raise InvalidInstaller(stdout + stderr)
    elif NOT_AN_AI_MESSAGE in stdout + stderr:
        raise InvalidAIF(stdout + stderr)

    # Check the return code.
    # It might be nicer to mark
    try:
        result.check_returncode()
    except:
        print("stderr")
        print(stderr)
        print("stdout")
        print(stdout)
        exit("Failed to read SIS file")

    return json.loads(stdout)


def dumpsis(path):
    return run_json_command(DUMPSIS_PATH, path)


def dumpaif(path):
    return run_json_command(DUMPAIF_PATH, path)


def dumpsis_extract(source, destination):
    result = subprocess.run(["lua", DUMPSIS_PATH, source, destination], capture_output=True)

    # Sadly we ignore foreign characters right now and using CP1252 by default.
    stdout = result.stdout.decode('utf-8')
    stderr = result.stderr.decode('utf-8')

    if "Illegal byte sequence" in stdout + stderr:
        return None

    # Check the return code.
    # It might be nicer to mark
    try:
        result.check_returncode()
    except:
        print("stderr")
        print(stderr)
        print("stdout")
        print(stdout)
        exit("Failed to read SIS file")


def get_icons(aif_path):
    aif_path = os.path.abspath(aif_path)
    with tempfile.TemporaryDirectory() as directory_path:
        aif_basename = os.path.basename(aif_path)
        temporary_aif_path = os.path.join(directory_path, aif_basename)
        shutil.copyfile(aif_path, temporary_aif_path)
        subprocess.check_output(["lua", DUMPAIF_PATH, "-e", temporary_aif_path])
        aif_basename = os.path.basename(temporary_aif_path)
        aif_dirname = os.path.dirname(temporary_aif_path)
        icon_candidates = os.listdir(aif_dirname)
        icons = []
        for candidate in icon_candidates:
            match = re.match("^" + aif_basename + r"_(\d)_(\d+)x(\d+)_(\d)bpp.bmp$", candidate)
            if match:
                index = match.group(1)
                width = int(match.group(2))
                height = int(match.group(3))
                bpp = int(match.group(4))
                asset_path = os.path.join(aif_dirname, candidate)
                with open(asset_path, 'rb') as fh:
                    data = "data:image/bmp;base64," + base64.b64encode(fh.read()).decode('utf-8')
                    icons.append(Image(width, height, bpp, data))
        return icons


def recognize(path):
    logging.debug("Recognizing '%s'...", path)
    try:
        details = run_json_command(RECOGNIZE_PATH, path)
        if "era" in details:
            era = details["era"]
            details["era"] = "epoc32" if era == "er5" else era
        return details
    except:
        return {"type": "unknown"}
