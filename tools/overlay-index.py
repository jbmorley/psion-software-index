#!/usr/bin/env python3

import argparse
import collections
import json
import os
import shutil


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

    destination_library_path = os.path.join(output_path, "library.json")
    destination_sources_path = os.path.join(output_path, "sources.json")
    destination_summary_path = os.path.join(output_path, "summary.json")


    screenshots_output_path = os.path.join(output_path, "screenshots")

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

    # Create the screenshots directory if it doesn't exist.
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
