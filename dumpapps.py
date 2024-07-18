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
import shutil
import subprocess
import tempfile

import jinja2
import yaml


ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")
BUILD_DIRECTORY = os.path.join(ROOT_DIRECTORY, "build")


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


LIBRARY_INDEXES = [
    "library/epocgames",
    "library/epocgraphics",
    "library/epocmap",
    "library/epocmisc",
    "library/epocmoney",
    "library/epocprog",
    "library/epocutil",
    "library/epocvault",
    "library/geofox",
    "library/s7games",
]


class LibraryMetadataProvider(object):

    def __init__(self, path):
        self.path = path
        self.descriptions = {}
        for index_path in LIBRARY_INDEXES:
            with open(os.path.join(path, index_path) + ".htm") as fh:
                for line in fh.readlines():
                    match = re.match(r"^(\S+)\s+(\d{2}/\d{2}/\d{2})\s+(.+)$", line)
                    if not match:
                        continue
                    application_path = os.path.join(path, index_path, match.group(1)).lower()
                    self.descriptions[application_path] = match.group(3)
                    if not os.path.exists(application_path):
                        print("WARN: Misisng application path", application_path)

    def summary_for(self, path):
        directory = os.path.dirname(os.path.join(self.path, path)).lower()
        if directory in self.descriptions:
            return self.descriptions[directory]
        return None


def decode(s, encodings=('ascii', 'utf8', 'latin1', 'cp1252')):
    for encoding in encodings:
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("Unknown encoding")


def readme_for(path):
    directory_path = os.path.dirname(path)
    files = os.listdir(directory_path)
    for f in files:
        if f.lower() == "readme.txt":
            with open(os.path.join(directory_path, f), "rb") as fh:
                return decode(fh.read())


class DummyMetadataProvider(object):

    def summary_for(self, path):
        return None


class Image(object):

    def __init__(self, width, height, bpp, data):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.data = data


class Library(object):

    def __init__(self, path, name, metadata_provider):
        self.path = path
        self.name = name
        self.metadata_provider = metadata_provider

    def summary_for(self, path):
        return self.metadata_provider.summary_for(path)


class Summary(object):

    def __init__(self, installer_count, uid_count, version_count, sha_count):
        self.installer_count = installer_count
        self.uid_count = uid_count
        self.version_count = version_count
        self.sha_count = sha_count


class Version(object):

    def __init__(self, installers):
        self.installers = installers
        self.variants = group_collections(installers, lambda x: x.sha256)

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

    @property
    def summary(self):
        return self.installers[0].summary

    @property
    def readme(self):
        for installer in self.installers:
            if installer.readme is not None:
                return installer.readme

    @property
    def icon(self):
        return select_icon([installer.icon for installer in self.installers
                            if installer.icon])


class Installer(object):

    def __init__(self, library, path, details, sha256, icons):
        self.library = library
        self.path = path
        self._details = details
        self.sha256 = sha256
        self.icons = icons
        self.readme = readme_for(os.path.join(library.path, path))

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

    @property
    def full_path(self):
        return os.path.join(self.library.path, self.path)

    @property
    def summary(self):
        return self.library.summary_for(self.path)

    @property
    def icon(self):
        return select_icon(self.icons)


class Collection(object):

    def __init__(self, identifier, installers):
        self.identifier = identifier
        self.installers = installers


def select_icon(icons):
    square_icons = [icon for icon in icons if icon.width == icon.height]
    icons = list(reversed(sorted(icons, key=lambda x: (x.bpp, x.width))))
    if len(icons) < 1:
        return None
    return icons[0]


def group_collections(installers, group_by):
    groups = collections.defaultdict(list)
    for installer in installers:
        groups[group_by(installer)].append(installer)
    return [Collection(identifier, installers) for identifier, installers in groups.items()]


def dumpsis(path):
    result = subprocess.run(["lua", "/Users/jbmorley/Projects/opolua/src/dumpsis.lua", "--json", path], capture_output=True)

    # Sadly we ignore foreign characters right now and using CP1252 by default.
    stdout = result.stdout.decode('utf-8')
    stderr = result.stderr.decode('utf-8')

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


def import_library(library):
    installers = []

    print(f"Importing library '{library.path}'...")
    for root, dirs, files in os.walk(library.path):
        file_paths = [os.path.join(root, f) for f in files]
        for file_path in file_paths:
            basename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            if ext != ".sis" or basename in IGNORED:
                continue
            rel_path = os.path.relpath(file_path, library.path)
            print(f"Importing '{rel_path}'...")
            info = dumpsis(file_path)
            if info is None:
                continue

            icons = []
            with tempfile.TemporaryDirectory() as temporary_directory_path:
                with contextlib.chdir(temporary_directory_path):
                    dumpsis_extract(file_path, temporary_directory_path)
                    contents = glob.glob("**/*.aif", recursive=True)
                    if contents:
                        aif_path = contents[0]
                        icons = get_icons(aif_path)
            installer = Installer(library, rel_path, info, shasum(file_path), icons)

            installers.append(installer)

    return installers


def get_icons(aif_path):
    aif_path = os.path.abspath(aif_path)
    with tempfile.TemporaryDirectory() as directory_path:
        aif_basename = os.path.basename(aif_path)
        temporary_aif_path = os.path.join(directory_path, aif_basename)
        shutil.copyfile(aif_path, temporary_aif_path)
        subprocess.check_output(["lua", "/Users/jbmorley/Projects/opolua/src/dumpaif.lua", "-e", temporary_aif_path])
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("definition")
    options = parser.parse_args()

    with open(options.definition) as fh:
        definition = yaml.safe_load(fh)

    loader = jinja2.FileSystemLoader(TEMPLATES_DIRECTORY)
    environment = jinja2.Environment(loader=loader)
    template = environment.get_template("index.html")

    libraries = []
    installers = []
    for source in definition:
        metadata_provider = DummyMetadataProvider()
        if "metadata_provider" in source:
            metadata_provider_class = source["metadata_provider"]
            metadata_provider = globals()[metadata_provider_class](path=source["path"])
        library = Library(path=source["path"],
                          name=source["name"],
                          metadata_provider=metadata_provider)
        libraries.append(library)
        installers += import_library(library)

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

    if os.path.exists(BUILD_DIRECTORY):
        shutil.rmtree(BUILD_DIRECTORY)

    os.mkdir(BUILD_DIRECTORY)

    shutil.copyfile(os.path.join(ROOT_DIRECTORY, "css", "main.css"),
                    os.path.join(BUILD_DIRECTORY, "main.css"))

    with open(os.path.join(BUILD_DIRECTORY, "index.html"), "w") as fh:
        fh.write(template.render(libraries=libraries,
                                 summary=summary,
                                 applications=applications))


if __name__ == "__main__":
    main()
