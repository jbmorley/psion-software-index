#!/usr/bin/env python3

import argparse
import logging
import os
import sys

import yaml

import common


TOOLS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
ROOT_DIRECTORY = os.path.dirname(TOOLS_DIRECTORY)
ASSETS_DIRECTORY = os.path.join(ROOT_DIRECTORY, "_new_assets")


verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("library")
    options = parser.parse_args()

    library = common.Library(options.library)
    library.sync()

    for source in library.sources:
        print(source.title)
        print(source.description)
        print(source.url)
        print("")


if __name__ == "__main__":
    main()
