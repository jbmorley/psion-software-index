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
import os
import urllib.parse
import yaml

ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(ROOT_DIRECTORY, "assets.txt")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("definition")
    options = parser.parse_args()

    with open(options.definition) as fh:
        definition = yaml.safe_load(fh)

    assets = []
    for source in definition["sources"]:
        if "url" not in source or not source["url"].startswith("https://archive.org/details/"):
            continue
        url = urllib.parse.urlparse(source["url"])
        assets.append(os.path.split(url.path)[-1])

    assets.sort()

    with open(ASSETS_PATH, "w") as fh:
        for asset in assets:
            fh.write(asset)
            fh.write("\n")


if __name__ == "__main__":
    main()
