#!/usr/bin/env python3

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
