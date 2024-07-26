#!/usr/bin/env python3

import argparse
import array
import base64
import collections
import contextlib
import csv
import glob
import hashlib
import os
import re
import shutil
import tempfile
import urllib.parse
import uuid
import zipfile

import jinja2
import yaml

import opolua


ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")
BUILD_DIRECTORY = os.path.join(ROOT_DIRECTORY, "build")

OPOLUA_DIRECTORY = os.path.join(ROOT_DIRECTORY, "opolua")
DUMPAIF_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpaif.lua")
DUMPSIS_PATH = os.path.join(OPOLUA_DIRECTORY, "src", "dumpsis.lua")


# These SIS files currently cause issues with the extraction tools we're using so they're being ignored for the time
# being to allow us to make progress with some of the existing libraries.
IGNORED = set([
    "netutils.sis",
    "nEzumi 2.sis",
    "RevoSDK.zip",
])

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
    "library/msgsuite",
    "library/pcba",
    "library/psiwin",
    "library/revogames",
    "library/s3comms",
    "library/s3games",
    "library/s3graphics",
    "library/s3mapping",
    "library/s3misc",
    "library/s3money",
    "library/s3prog",
    "library/s3units",
    "library/s3util",
    "library/s3vault",
    "library/s7games",
    "library/siena",
]


LANGUAGE_ORDER = ["en_GB", "en_US", "en_AU", "fr_FR", "de_DE", "it_IT", "nl_NL", "bg_BG", ""]


class DummyMetadataProvider(object):

    def summary_for(self, path):
        return None


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
        directory = os.path.dirname(path).lower()
        while directory != "/":
            if directory in self.descriptions:
                return self.descriptions[directory]
            directory = os.path.dirname(directory)
        return None


def decode(s, encodings=('ascii', 'utf8', 'latin1', 'cp1252')):
    for encoding in encodings:
        try:
            return s.decode(encoding)
        except UnicodeDecodeError:
            pass
    raise UnicodeDecodeError("Unknown encoding")


def find_sibling(path, name):
    directory_path = os.path.dirname(path)
    files = os.listdir(directory_path)
    for f in files:
        if f.lower() == name.lower():
            return os.path.join(directory_path, f)


def readme_for(path):
    readme_path = find_sibling(path, "readme.txt")
    if readme_path:
        with open(readme_path, "rb") as fh:
            return decode(fh.read())


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

    def __init__(self, reference, details, sha256, icons, summary, readme):
        self.reference = reference
        self._details = details
        self.sha256 = sha256
        self.icons = icons
        self.summary = summary
        self.readme = readme
        self.uuid = str(uuid.uuid4())  # TODO: Is this ever used? <------ remove me
        self.uid = "0x%08x" % self._details["uid"]
        self.version = self._details["version"]
        self.full_path = str(reference)
        self.language_emoji = "".join([LANGUAGE_EMOJI[language] for language in self._details["name"].keys()])

    @property
    def name(self):
        return select_name(self._details["name"])

    @property
    def icon(self):
        return select_icon(self.icons)

    @property
    def install_url(self):
        return "x-reconnect://install/?" + urllib.parse.urlencode({"path": "file://" + self.full_path}, quote_via=urllib.parse.quote)


class App(object):

    def __init__(self, reference, identifier, sha256, name, icons, summary, readme):
        self.reference = reference
        self.identifier = identifier
        self.sha256 = sha256
        self.name = name
        self.icons = icons
        self.summary = summary
        self.readme = readme
        self.version = "Unknown Version"
        self.language_emoji = "Unknown Language"
        self.full_path = str(reference)
        self.uid = self.identifier

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


def select_name(names):
    for language in LANGUAGE_ORDER:
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


def import_installer(library, reference, path):
    info = opolua.dumpsis(path)
    icons = []
    with tempfile.TemporaryDirectory() as temporary_directory_path:
        with contextlib.chdir(temporary_directory_path):
            opolua.dumpsis_extract(path, temporary_directory_path)
            contents = glob.glob("**/*.aif", recursive=True)
            if contents:
                aif_path = contents[0]
                icons = opolua.get_icons(aif_path)
    summary = library.summary_for(path)
    readme = readme_for(path)
    return Installer(reference, info, shasum(path), icons, summary, readme)


class Reference(object):

    def __init__(self, parent, path):
        self.parent = parent
        self.path = path

    def __str__(self):
        return os.path.join(self.parent.path, self.path)


def import_apps(library, reference=None, path=None, indent=0):
    reference = reference if reference else [library]
    path = path if path else library.path
    apps = []

    print(" " * indent + f"Importing library '{path}'...")
    for root, dirs, files in os.walk(path):
        file_paths = [os.path.join(root, f) for f in files]
        for file_path in file_paths:
            basename = os.path.basename(file_path)
            name, ext = os.path.splitext(basename)
            ext = ext.lower()
            rel_path = os.path.relpath(file_path, path)

            if basename in IGNORED or "System/Install" in file_path:
                continue

            elif ext == ".app":

                print(" " * indent + f"Importing app '{file_path}'...")
                aif_path = find_sibling(file_path, name + ".aif")
                uid = str(uuid.uuid4())
                icons = []
                name = os.path.basename(rel_path)
                if aif_path:
                    info = opolua.dumpaif(aif_path)
                    uid = ("0x%08x" % info["uid3"]).lower()
                    name = select_name(info["captions"])
                    icons = opolua.get_icons(aif_path)
                summary = library.summary_for(file_path)
                readme = readme_for(file_path)
                installer = App(reference + [rel_path], uid, shasum(file_path), name, icons, summary, readme)
                apps.append(installer)

            elif ext == ".sis":

                print(" " * indent + f"Importing installer '{file_path}'...")
                try:
                    # reference = Reference(parent=library, path=rel_path)
                    apps.append(import_installer(library=library,
                                                 reference=reference + [rel_path],
                                                 path=file_path))
                except opolua.InvalidInstaller as e:
                    print(e)

            elif ext == ".zip":

                print(" " * indent + f"Importing zip '{file_path}'...")
                try:
                    with Zip(file_path) as contents_path:
                        apps.extend(import_apps(library, reference + [rel_path], contents_path, indent=indent+2))
                except NotImplementedError as e:
                    print(" " * indent + f"Unsupported zip file '{file_path}', {e}.")
                except zipfile.BadZipFile as e:
                    print(" " * indent + f"Corrupt zip file '{file_path}', {e}.")

    return apps


class Zip(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.temporary_directory = tempfile.TemporaryDirectory()

    def __enter__(self):
        self.pwd = os.getcwd()
        self.temporary_directory = tempfile.TemporaryDirectory()
        os.chdir(self.temporary_directory.name)
        try:
            with zipfile.ZipFile(self.path) as zip:
                zip.extractall()
            return self.temporary_directory.name
        except:
            os.chdir(self.pwd)
            self.temporary_directory.cleanup()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)
        self.temporary_directory.cleanup()


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
    for source in definition["sources"]:
        metadata_provider = DummyMetadataProvider()
        if "metadata_provider" in source:
            metadata_provider_class = source["metadata_provider"]
            metadata_provider = globals()[metadata_provider_class](path=source["path"])
        library = Library(path=source["path"],
                          name=source["name"],
                          metadata_provider=metadata_provider)
        libraries.append(library)
        installers += import_apps(library)

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
    for uid, installers in sorted([item for item in groups.items()], key=lambda x: x[1][0].name.lower()):
        applications.append(Application(uid, installers))

    if os.path.exists(BUILD_DIRECTORY):
        shutil.rmtree(BUILD_DIRECTORY)

    os.mkdir(BUILD_DIRECTORY)

    shutil.copyfile(os.path.join(ROOT_DIRECTORY, "css", "main.css"),
                    os.path.join(BUILD_DIRECTORY, "main.css"))

    with open(os.path.join(BUILD_DIRECTORY, "index.html"), "w") as fh:
        fh.write(template.render(options=definition["options"],
                                 libraries=libraries,
                                 summary=summary,
                                 applications=applications))


if __name__ == "__main__":
    main()
