#!/usr/bin/env python3

import argparse
import array
import collections
import contextlib
import csv
import glob
import hashlib
import json
import os
import subprocess
import tempfile


# These SIS files currently cause issues with the extraction tools we're using so they're being ignored for the time
# being to allow us to make progress with some of the existing libraries.
IGNORED = set([
    "jCompilePsion.sis",
    "jRunPsion.sis",
    "MrMattGames1.sis",
    "SCOMMSW.SIS",
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


class Installer(object):

    def __init__(self, library_path, path, details, sha256):
        self.library_path = library_path
        self.path = path
        self._details = details
        self.sha256 = sha256

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

            with tempfile.TemporaryDirectory() as temporary_directory_path:
                with contextlib.chdir(temporary_directory_path):
                    dumpsis_extract(file_path, temporary_directory_path)
                    contents = glob.glob("**/*.aif", recursive=True)
                    if contents:
                        subprocess.check_call(["lua", "/Users/jbmorley/Projects/opolua/src/dumpaif.lua", contents[0]])
                    print(contents)

            installer = Installer(path, rel_path, info, shasum(file_path))
            installers.append(installer)

    return installers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="+")
    options = parser.parse_args()


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

    with open('output.html', 'w') as fh:
        fh.write("""<!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    .sha, .uid {
                        font-family: monospace;
                    }
                </style>
            </head>
            <body>
            """)

        for uid, installers in sorted([item for item in groups.items()], key=lambda x: x[1][0].name.lower()):
            fh.write(f"<h1>{installers[0].name}</h1>")
            fh.write(f"<div class=\"uid\">{"0x%08x" % uid}</div>")
            fh.write("<table>")

            unique_shas = collections.defaultdict(list)
            for installer in installers:
                unique_shas[installer.sha256].append(installer)

            shas_sorted_by_version = sorted([sha for sha in unique_shas.keys()], key=lambda x: unique_shas[x][0].version)

            for sha in shas_sorted_by_version:
                duplicate_installers = unique_shas[sha]
                installer = duplicate_installers[0]

                all_paths = ", ".join([i.path for i in duplicate_installers])

                fh.write("<tr>")
                fh.write(f"<td>{installer.version}</td>")
                fh.write(f"<td>{installer.language_emoji}</td>")
                fh.write(f"<td class=\"sha\">{installer.sha256}</td>")
                fh.write("<td>")
                fh.write("<ul>")
                for i in duplicate_installers:
                    fh.write(f"<li>{i.path}</li>")
                fh.write("</ul>")
                fh.write("</td>")
                fh.write("</tr>")
            fh.write("</table>")

        fh.write("""</body>
            </html>
            """)

    print(f"{total_count} valid sis files; {len(unique_uids)} unique uids; {len(unique_versions)} unique versions'; {len(unique_shas)} unique files")



if __name__ == "__main__":
    main()
