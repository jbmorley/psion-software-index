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

import collections
import logging
import os
import tarfile
import tempfile
import zipfile
import zlib

import pycdlib

import model


def extract_iso(path, destination_path):

    iso = pycdlib.PyCdlib()
    iso.open(path)

    pathname = 'iso_path'
    if iso.has_udf():
        pathname = 'udf_path'
    elif iso.has_joliet():
        pathname = 'joliet_path'

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


def extract_tar(source, destination):
    with tarfile.TarFile(source) as tar:
        tar.extractall(path=destination)


def extract_zip(source, destination):
    with zipfile.ZipFile(source) as zip:
        zip.extractall(path=destination)


CONTAINER_MAPPING = {
    ".iso": extract_iso,
    ".tar": extract_tar,
    ".zip": extract_zip,
}


class Extractor(object):

    def __init__(self, path, method):
        self.path = os.path.abspath(path)
        self.method = method

    def __enter__(self):
        self.pwd = os.getcwd()
        self.temporary_directory = tempfile.TemporaryDirectory()  # TODO: Redundant?
        os.chdir(self.temporary_directory.name)
        try:
            self.method(self.path, self.temporary_directory.name)
            return self.temporary_directory.name
        except:
            os.chdir(self.pwd)
            self.temporary_directory.cleanup()
            raise

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.pwd)
        self.temporary_directory.cleanup()


def walk(path, reference=None, relative_to=None):
    reference = reference if reference is not None else []
    path = os.path.abspath(path)
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for a in [os.path.join(root, f) for f in files]:
                reference_item = model.ReferenceItem(name=os.path.relpath(a, relative_to), url=None)
                for (inner_path, inner_reference) in walk(a, reference=reference, relative_to=relative_to):
                    yield (inner_path, inner_reference)
    else:
        reference_item = model.ReferenceItem(name=os.path.relpath(path, relative_to), url=None)
        _, ext = os.path.splitext(path)
        ext = ext.lower()

        if ext in CONTAINER_MAPPING:
            logging.debug("Extracting '%s'...", path)
            try:
                with Extractor(path, method=CONTAINER_MAPPING[ext]) as contents_path:
                    for (inner_path, inner_reference) in walk(contents_path,
                                                              reference=reference + [reference_item],
                                                              relative_to=contents_path):
                        yield (inner_path, inner_reference)
            except (NotImplementedError, zipfile.BadZipFile, OSError, RuntimeError, tarfile.ReadError, zlib.error) as e:
                logging.warning("Failed to extract file '%s' with error '%s'.", path, e)
        else:
            yield (path, reference + [reference_item])
