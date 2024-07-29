#!/usr/bin/env python3

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

import argparse
import array
import base64
import collections
import contextlib
import csv
import glob
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
import uuid
import zipfile

import pycdlib
import yaml

import opolua


TOOLS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ROOT_DIRECTORY = os.path.dirname(TOOLS_DIRECTORY)
TEMPLATES_DIRECTORY = os.path.join(ROOT_DIRECTORY, "templates")

SITE_DIRECTORY = os.path.join(ROOT_DIRECTORY, "site")
DATA_DIRECTORY = os.path.join(SITE_DIRECTORY, "_data")
SUMMARY_PATH = os.path.join(DATA_DIRECTORY, "summary.json")
SOURCES_PATH = os.path.join(DATA_DIRECTORY, "sources.json")
LIBRARY_PATH = os.path.join(DATA_DIRECTORY, "library.json")

verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")


# These SIS files currently cause issues with the extraction tools we're using so they're being ignored for the time
# being to allow us to make progress with some of the existing libraries.
IGNORED = set([
    "netutils.sis",
    "NETUTILS.SIS",
    "NetUtils.sis",
    "nEzumi 2.sis",
    "RevoSDK.zip",
    "SCOMMSW.SIS",
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


class Chdir(object):

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.pwd = os.getcwd()
        os.chdir(self.path)
        return self.path

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)


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
                        logging.warning("WARN: Misisng application path", application_path)

    def summary_for(self, path):
        directory = os.path.dirname(path).lower()
        while directory != "/":
            if directory in self.descriptions:
                return self.descriptions[directory]
            directory = os.path.dirname(directory)
        return None


# TODO: Rename to source!
class Library(object):

    def __init__(self, path, name, url, metadata_provider):
        self.path = path
        self.name = name
        self.url = url
        self.metadata_provider = metadata_provider

    def summary_for(self, path):
        return self.metadata_provider.summary_for(path)

    def as_dict(self):
        return {
            'path': self.path,
            'name': self.name,
            'url': self.url,
        }


class Summary(object):

    def __init__(self, installer_count, uid_count, version_count, sha_count):
        self.installer_count = installer_count
        self.uid_count = uid_count
        self.version_count = version_count
        self.sha_count = sha_count

    def as_dict(self):
        return {
            'installerCount': self.installer_count,
            'uidCount': self.uid_count,
            'versionCount': self.version_count,
            'shaCount': self.sha_count,
        }


# TODO: Consider replacing with Collection
class Version(object):

    def __init__(self, installers):
        self.installers = installers
        self.variants = group_collections(installers, lambda x: x.sha256)

    @property
    def version(self):
        return self.installers[0].version

    def as_dict(self):
        return {
            'version': self.version,
            'variants': [variant.as_dict() for variant in self.variants],
        }


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

    def as_dict(self):
        dict = {
            'uid': self.uid,
            'name': self.name,
            'summary': self.summary,
            'versions': [version.as_dict() for version in self.versions],
        }
        summary = self.summary
        if summary:
            dict['summary'] = summary
        readme = self.readme  # TODO: Rename to description
        if readme:
            dict['readme'] = readme
        icon = self.icon
        if icon:
            dict['iconData'] = icon.data
        return dict


# TODO: This feels messy. Maybe the reference really should be a class?
def reference_as_dicts(reference):
    return [item.as_dict() for item in reference]


# TODO: Add additional information into the reference item (e.g., type, identifier)
#       A reference should be able to find the referenced item without any further information.
class ReferenceItem(object):

    def __init__(self, path):
        self.path = path

    def as_dict(self):
        return {
            'path': self.path,
            'name': self.path,
        }


class Release(object):

    # TODO: Rename UID to identifier everywhere.
    def __init__(self, reference, identifier, sha256, name, version, icons, summary, readme):
        self.reference = reference
        self.uid = identifier
        self.sha256 = sha256
        self.name = name
        self.version = version
        self.icons = icons
        self.summary = summary
        self.readme = readme
        self.icon = select_icon(self.icons)

    def as_dict(self):
        dict = {
            'reference': reference_as_dicts(self.reference),
            'sha256': self.sha256,
            'uid': self.uid,
            'name': self.name,
            'version': self.version,
        }
        icon = self.icon
        if icon:
            dict['iconData'] = self.icon.data
        return dict


class Collection(object):

    def __init__(self, identifier, installers):
        self.identifier = identifier
        self.installers = installers  # TODO: Rename to items?

    def as_dict(self):
        return {
            'identifier': self.identifier,
            'installers': [installer.as_dict() for installer in self.installers],
        }


class Reference(object):

    def __init__(self, parent, path):
        self.parent = parent
        self.path = path

    def __str__(self):
        return os.path.join(self.parent.path, self.path)


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
    logging.effort("Failed to select a name from candidates '%s'.", names)
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
        with Chdir(temporary_directory_path):
            opolua.dumpsis_extract(path, temporary_directory_path)
            contents = glob.glob("**/*.aif", recursive=True)
            if contents:
                aif_path = contents[0]
                icons = opolua.get_icons(aif_path)
    summary = library.summary_for(path)
    readme = readme_for(path)
    return Release(reference=reference,
                   identifier="0x%08x" % info["uid"],
                   sha256=shasum(path),
                   name=select_name(info["name"]),
                   version=info["version"],
                   icons=icons,
                   summary=summary,
                   readme=readme)


def import_apps(library, reference=None, path=None, indent=0):
    reference = reference if reference else [library]
    path = path if path else library.path
    apps = []

    logging.info(" " * indent + f"Importing library '{path}'...")
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

                logging.info(" " * indent + f"Importing app '{file_path}'...")
                aif_path = find_sibling(file_path, name + ".aif")
                uid = str(uuid.uuid4())
                icons = []
                name = os.path.basename(rel_path)
                if aif_path:
                    info = opolua.dumpaif(aif_path)
                    uid = ("0x%08x" % info["uid3"]).lower()
                    name = select_name(info["captions"])
                    icons = opolua.get_icons(aif_path)
                else:
                    try:
                        info = opolua.dumpaif(file_path)
                        icons = opolua.get_icons(file_path)
                        name = select_name(info["captions"])
                    except opolua.InvalidAIF:
                        pass
                    except BaseException as e:
                        logging.warning("Failed to parse APP as AIF with message '%s'", e)
                summary = library.summary_for(file_path)
                readme = readme_for(file_path)
                release = Release(reference=reference + [ReferenceItem(rel_path)],
                                  identifier=uid,
                                  sha256=shasum(file_path),
                                  name=name,
                                  version="Unknown",
                                  icons=icons,
                                  summary=summary,
                                  readme=readme)
                apps.append(release)

            elif ext == ".sis":

                logging.info(" " * indent + f"Importing installer '{file_path}'...")
                try:
                    apps.append(import_installer(library=library,
                                                 reference=reference + [ReferenceItem(rel_path)],
                                                 path=file_path))
                except opolua.InvalidInstaller as e:
                    logging.error("Failed to import installer with message '%s", e)

            elif ext == ".zip":

                logging.info(" " * indent + f"Importing zip '{file_path}'...")
                try:
                    with Zip(file_path) as contents_path:
                        apps.extend(import_apps(library, reference + [ReferenceItem(rel_path)], contents_path, indent=indent+2))
                except NotImplementedError as e:
                    logging.info(" " * indent + f"Unsupported zip file '{file_path}', {e}.")
                except zipfile.BadZipFile as e:
                    logging.info(" " * indent + f"Corrupt zip file '{file_path}', {e}.")

            elif ext == ".iso":

                logging.info(" " * indent + f"Importing ISO '{file_path}'...")
                with Iso(file_path) as contents_path:
                    apps.extend(import_apps(library, reference + [ReferenceItem(rel_path)], contents_path, indent=indent+2))

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


def extract_iso(path, destination_path):

    iso = pycdlib.PyCdlib()
    iso.open(path)

    pathname = 'iso_path'
    start_path = '/'
    root_entry = iso.get_record(**{pathname: start_path})

    dirs = collections.deque([root_entry])
    while dirs:
        dir_record = dirs.popleft()
        ident_to_here = iso.full_path_from_dirrecord(dir_record,
                                                     rockridge=pathname == 'rr_path')
        relname = ident_to_here[len(start_path):]
        if relname and relname[0] == '/':
            relname = relname[1:]
        if dir_record.is_dir():
            if relname != '':
                os.makedirs(os.path.join(destination_path, relname))
            child_lister = iso.list_children(**{pathname: ident_to_here})

            for child in child_lister:
                if child is None or child.is_dot() or child.is_dotdot():
                    continue
                dirs.append(child)
        else:
            if dir_record.is_symlink():
                fullpath = os.path.join(destination_path, relname)
                local_dir = os.path.dirname(fullpath)
                local_link_name = os.path.basename(fullpath)
                old_dir = os.getcwd()
                os.chdir(local_dir)
                os.symlink(dir_record.rock_ridge.symlink_path(), local_link_name)
                os.chdir(old_dir)
            else:
                iso.get_file_from_iso(os.path.join(destination_path, relname), **{pathname: ident_to_here})


class Iso(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.temporary_directory = tempfile.TemporaryDirectory()

    def __enter__(self):
        logging.info(f"Opening ISO file '{self.path}'...")
        self.pwd = os.getcwd()
        self.temporary_directory = tempfile.TemporaryDirectory()
        os.chdir(self.temporary_directory.name)
        extract_iso(self.path, self.temporary_directory.name)
        return self.temporary_directory.name

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)
        self.temporary_directory.cleanup()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("definition")
    parser.add_argument('--verbose', '-v', action='store_true', default=False, help="Show verbose output.")
    options = parser.parse_args()

    with open(options.definition) as fh:
        definition = yaml.safe_load(fh)

    libraries = []
    installers = []
    for source in definition["sources"]:
        metadata_provider = DummyMetadataProvider()
        if "metadata_provider" in source:
            metadata_provider_class = source["metadata_provider"]
            metadata_provider = globals()[metadata_provider_class](path=source["path"])
        library = Library(path=source["path"],
                          name=source["name"],
                          url=source["url"] if "url" in source else None,
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

    os.makedirs(DATA_DIRECTORY, exist_ok=True)

    logging.info("Writing summary...")
    with open(SUMMARY_PATH, "w") as fh:
        json.dump(summary.as_dict(), fh)

    logging.info("Writing sources...")
    with open(SOURCES_PATH, "w") as fh:
        json.dump([library.as_dict() for library in libraries], fh)

    logging.info("Writing the library...")
    with open(LIBRARY_PATH, "w", encoding="utf-8") as fh:
        json.dump([application.as_dict() for application in applications], fh)


if __name__ == "__main__":
    main()
