#!/usr/bin/env python3

import argparse
import collections
import json
import logging
import os
import shutil
import sys


verbose = '--verbose' in sys.argv[1:] or '-v' in sys.argv[1:]
logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="[%(levelname)s] %(message)s")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("index")
    parser.add_argument("overlay")
    parser.add_argument("output")
    options = parser.parse_args()

    index_path = os.path.abspath(options.index)
    overlay_path = os.path.abspath(options.overlay)
    output_path = os.path.abspath(options.output)

    source_library_path = os.path.join(index_path, "library.json")
    source_sources_path = os.path.join(index_path, "sources.json")
    source_summary_path = os.path.join(index_path, "summary.json")

    data_output_path = os.path.join(output_path, "_data")
    screenshots_output_path = os.path.join(output_path, "screenshots")

    destination_library_path = os.path.join(data_output_path, "library.json")
    destination_sources_path = os.path.join(data_output_path, "sources.json")
    destination_summary_path = os.path.join(data_output_path, "summary.json")


    # Import screenshots from the overlay.
    overlay = collections.defaultdict(list)
    for identifier in os.listdir(overlay_path):
        if identifier.startswith("."):
            continue
        screenshots_path = os.path.join(overlay_path, identifier)
        overlay[identifier] = [os.path.join(screenshots_path, screenshot)
                               for screenshot in os.listdir(screenshots_path)]

    # Load the index.
    with open(source_library_path) as fh:
        index = json.load(fh)

    # Clean up the existing screenshots path.
    if os.path.exists(screenshots_output_path):
        shutil.rmtree(screenshots_output_path)

    # Create the output directories if they don't exist.
    os.makedirs(data_output_path)
    os.makedirs(screenshots_output_path)

    # Merge the screenshots into the overlay.
    for application in index:
        identifier = application['uid']
        if identifier not in overlay:
            continue
        screenshots = overlay[identifier]
        os.makedirs(os.path.join(screenshots_output_path, identifier))
        relative_paths = []
        for screenshot in screenshots:
            relative_path = os.path.join("screenshots", identifier, os.path.basename(screenshot))
            destination_path = os.path.join(output_path, relative_path)
            logging.info("Copying '%s' to '%s'...", screenshot, destination_path)
            shutil.copyfile(screenshot, destination_path)
            relative_paths.append(relative_path)
        application['screenshots'] = relative_paths

    # Write the index.
    shutil.copyfile(source_sources_path, destination_sources_path)
    shutil.copyfile(source_summary_path, destination_summary_path)
    with open(destination_library_path, "w") as fh:
        json.dump(index, fh)


if __name__ == "__main__":
    main()
