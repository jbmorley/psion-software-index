import base64
import json
import os
import re
import shutil
import subprocess
import tempfile

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
OPOLUA_DIRECTORY = os.path.join(ROOT_DIRECTORY, "opolua")
DUMPAIF_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpaif.lua")
DUMPSIS_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpsis.lua")

UNSUPPORTED_MESSAGE = "Only ER5 SIS files are supported"


class InvalidInstaller(Exception):
    pass


class Image(object):

    def __init__(self, width, height, bpp, data):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.data = data


def dumpsis(path):
    result = subprocess.run(["lua", DUMPSIS_PATH, "--json", path], capture_output=True)

    # Sadly we ignore foreign characters right now and using CP1252 by default.
    stdout = result.stdout.decode('utf-8')
    stderr = result.stderr.decode('utf-8')

    if UNSUPPORTED_MESSAGE in stdout + stderr:
        raise InvalidInstaller(stderr)

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


def get_uid(aif_path):
    output = subprocess.check_output(["lua", DUMPAIF_PATH, aif_path]).decode('utf-8', 'ignore')
    return output.split()[1]
