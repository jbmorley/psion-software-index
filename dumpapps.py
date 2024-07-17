#!/usr/bin/env python3

import argparse
import array
import base64
import collections
import contextlib
import csv
import glob
import hashlib
import json
import os
import re
import subprocess
import tempfile

import jinja2

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")


# These SIS files currently cause issues with the extraction tools we're using so they're being ignored for the time
# being to allow us to make progress with some of the existing libraries.
IGNORED = set([
    "ebc.sis",
    "jCompilePsion.sis",
    "jRunPsion.sis",
    "MrMattGames1.sis",
    "SCOMMSW.SIS",
    "enotem.SIS",  # Unknown compression scheme 3
    "eplaym.SIS",  # Unknown compression scheme 3
    "ER5.SIS",
    "MSGSUITE.SIS",
    "netutils.sis",
    "Hol5.SIS",
])

UNSUPPORTED_MESSAGE = "Only ER5 SIS files are supported"

LANGUAGE_EMOJI = {
    "en_GB": "🇬🇧",
    "de_DE": "🇩🇪",
    "en_US": "🇺🇸",
    "en_AU": "🇦🇺",
    "fr_FR": "🇫🇷",
    "it_IT": "🇮🇹",
    "nl_NL": "🇳🇱",
    "es_ES": "🇪🇸",
    "cs_CZ": "🇨🇿",
    "bg_BG": "🇧🇬",
    "hu_HU": "🇭🇺",
    "pl_PL": "🇵🇱",
    "ru_RU": "🇷🇺",
    "no_NO": "🇳🇴",
    "sv_SE": "🇸🇪",
    "da_DK": "🇩🇰",
    "en_NZ": "🇳🇿",
    "de_CH": "🇨🇭",
    "fi_FI": "🇫🇮",
    "fr_BE": "🇧🇪",
    "nl_BE": "🇧🇪",
    "fr_CH": "🇨🇭",
    "pt_PT": "🇵🇹",
}


class Summary(object):

    def __init__(self, installer_count, uid_count, version_count, sha_count):
        self.installer_count = installer_count
        self.uid_count = uid_count
        self.version_count = version_count
        self.sha_count = sha_count


class Version(object):

    def __init__(self, installers):
        self.installers = installers

    @property
    def version(self):
        return self.installers[0].version


class Application(object):

    def __init__(self, uid, installers):
        self.uid = uid
        self.installers = installers
        versions = collections.defaultdict(list)
        for installer in installers:
            versions[installer.version].append(installer)
        self.versions = sorted([Version(installers=installers) for installers in versions.values()], key=lambda x: x.version)

    @property
    def name(self):
        return self.installers[0].name


class Installer(object):

    def __init__(self, library_path, path, details, sha256, icon_data):
        self.library_path = library_path
        self.path = path
        self._details = details
        self.sha256 = sha256
        self.icon_data = icon_data

    @property
    def uid(self):
        return self._details["uid"]

    @property
    def version(self):
        return self._details["version"]

    @property
    def name(self):
        return select_name(self._details["name"], ["en_GB", "en_US", "en_AU", "fr_FR", "de_DE", "it_IT", "nl_NL"])

    @property
    def language_emoji(self):
        return "".join([LANGUAGE_EMOJI[language] for language in self._details["name"].keys()])


def dumpsis(path):
    result = subprocess.run(["lua", "/Users/jbmorley/Projects/opolua/src/dumpsis.lua", "--json", path], capture_output=True)

    # Sadly we ignore foreign characters right now and using CP1252 by default.
    stdout = result.stdout.decode('cp1252', 'ignore')
    stderr = result.stderr.decode('cp1252', 'ignore')

    if UNSUPPORTED_MESSAGE in stdout + stderr:
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

    return json.loads(stdout)


def dumpsis_extract(source, destination):
    result = subprocess.run(["lua", "/Users/jbmorley/Projects/opolua/src/dumpsis.lua", source, destination], capture_output=True)

    # Sadly we ignore foreign characters right now and using CP1252 by default.
    stdout = result.stdout.decode('cp1252', 'ignore')
    stderr = result.stderr.decode('cp1252', 'ignore')

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


def select_name(names, languages):
    for language in languages:
        if language in names:
            return names[language]
    print(names)
    exit("Unable to find language")


def shasum(path):
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def import_library(path):
    installers = []

    print(f"Importing library '{path}'...")
    for root, dirs, files in os.walk(path):
        file_paths = [os.path.join(root, f) for f in files]
        for file_path in file_paths:
            basename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            if ext != ".sis" or basename in IGNORED:
                continue
            rel_path = os.path.relpath(file_path, path)
            print(f"Importing '{rel_path}'...")
            info = dumpsis(file_path)
            if info is None:
                continue

            icon_data = None
            with tempfile.TemporaryDirectory() as temporary_directory_path:
                with contextlib.chdir(temporary_directory_path):
                    dumpsis_extract(file_path, temporary_directory_path)
                    contents = glob.glob("**/*.aif", recursive=True)
                    if contents:
                        aif_path = contents[0]
                        subprocess.check_call(["lua", "/Users/jbmorley/Projects/opolua/src/dumpaif.lua", "-e", aif_path])
                        aif_basename = os.path.basename(aif_path)
                        aif_dirname = os.path.dirname(aif_path)
                        icon_candidates = os.listdir(aif_dirname)
                        print(icon_candidates)
                        for candidate in icon_candidates:
                            match = re.match("^" + aif_basename + r"_(\d)_(\d+)x(\d+)_(\d)bpp.bmp$", candidate)
                            if match:
                                index = match.group(1)
                                width = int(match.group(2))
                                height = int(match.group(3))
                                bpp = int(match.group(4))
                                asset_path = os.path.join(aif_dirname, candidate)
                                if width != 48 or height != 48:
                                    continue
                                print(asset_path, index, width, height, bpp)
                                with open(asset_path, 'rb') as fh:
                                    icon_data = "data:image/bmp;base64," + base64.b64encode(fh.read()).decode('utf-8')
                                break

            installer = Installer(path, rel_path, info, shasum(file_path), icon_data)
            installers.append(installer)

    return installers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="+")
    options = parser.parse_args()


    loader = jinja2.FileSystemLoader(TEMPLATES_DIRECTORY)
    environment = jinja2.Environment(loader=loader)
    template = environment.get_template("index.html")

    paths = [os.path.abspath(path) for path in options.path]
    installers = []
    for path in paths:
        installers += import_library(path)

    unique_uids = set()
    unique_versions = set()
    unique_shas = set()
    total_count = 0
    details = collections.defaultdict(list)
    groups = collections.defaultdict(list)

    for installer in installers:
        unique_uids.add(installer.uid)
        unique_versions.add((installer.uid, installer.version))
        unique_shas.add(installer.sha256)
        total_count = total_count + 1
        details[(installer.uid, installer.sha256, installer.version)].append(installer)
        groups[(installer.uid)].append(installer)

    summary = Summary(installer_count=total_count,
                      uid_count=len(unique_uids),
                      version_count=len(unique_versions),
                      sha_count=len(unique_shas))

    applications = []
    for uid, installers in sorted([item for item in groups.items()],                                        key=lambda x: x[1][0].name.lower()):
        applications.append(Application(uid, installers))

    with open("index.html", "w") as fh:
        fh.write(template.render(summary=summary, applications=applications))


if __name__ == "__main__":
    main()
