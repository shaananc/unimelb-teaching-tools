import os

"""
This script arranges JSON files in a more logical way by moving them into subdirectories based on a specific key in the JSON data.
The script performs the following steps:
1. Sets up logging with colorized output using the `rich` library.
2. Defines a `DRY_RUN` flag to indicate whether the script should perform actual file operations or just log the intended actions.
3. Defines the `main` function which:
    - Determines the current working directory of the script.
    - Sets the base output directory to "output/grok_exercises".
    - Iterates through all JSON files in the base output directory.
    - Reads each JSON file and extracts the "title" and "slug" keys.
    - Checks if the "slug" contains a specific substring ("unimelb-comp10001-2024-s2").
    - If the substring is not found, logs the file path to "remainders.txt" and skips further processing for that file.
    - Constructs a subdirectory path based on the "title" key.
    - Logs the intended file move operation.
    - If not in dry run mode, creates the subdirectory (if it doesn't exist) and moves the file to the subdirectory.
    - Logs the total number of files moved.
Usage:
- Set the `DRY_RUN` flag to `True` to perform a dry run without making any actual changes.
- Set the `DRY_RUN` flag to `False` to perform the actual file move operations.
"""
import json
import shutil
import pathlib
from pathlib import Path
from configparser import ConfigParser

import os

# use rich to colorize all the logging
from rich.logging import RichHandler

# add logging
import logging

FORMAT = "%(message)s"
logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)],
)
logger = logging.getLogger(__name__)

DRY_RUN = False
DRY_RUN_STR = "[DRY RUN] " if DRY_RUN else ""
config = ConfigParser()
config.read("config/config_comp10001.ini")
grok_slug = config.get("GROK", "grok_course_slug")
log_dir =  Path("output")/ grok_slug / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(filename=log_dir / "arrange_files.log")
file_handler.formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%d-%b-%y %H:%M:%S"
)
logger.addHandler( file_handler)


def main():

    # this is a one-time script to arrange the files in a more logical way

    # get the directory the executing file is in
    cwd = Path(os.path.dirname(os.path.realpath(__file__)))
    # get the path to the output/grok_exercises directory
    output_base = cwd / "output" / grok_slug / "grok_exercises"
    moved_files = 0
    # iterate through all the json files in output/grok_exercises and move them to a subdirectory based on the json key "title"
    logger.info(output_base)
    for file in output_base.glob("*.json"):
        logger.debug(f"Processing file: {file}")

        # get the full path to the file
        file_path = os.path.join(output_base, file)
        # open the file and read the json
        with open(file_path, "r") as f:
            data = json.load(f)

        # check we have the right slug
        title = data["title"]
        slug = data["slug"]
        logging.debug(f"Obtained Slug and Title: {slug}, {title}")
        if grok_slug not in slug:
            open("remainders.txt", "a").write(file_path + "\n")
            continue

        # get the title from the json

        # if title.startswith("Ex"):
        #     # get only the exercise number
        #     title = title.split(":")[0]
        # else:
        #     open("remainders.txt", "a").write(file_path + "\n")
        #     continue

        # get the path to the subdirectory based on the title
        sub_dir = os.path.join(output_base, title)
        # just print for a dry run
        logger.info(f"{DRY_RUN_STR} Moving {file_path} to {sub_dir}")
        moved_files += 1
        if not DRY_RUN:
            # create the subdirectory if it doesn't exist
            pathlib.Path(sub_dir).mkdir(parents=True, exist_ok=True)
            # move the file to the subdirectory
            shutil.move(file_path, sub_dir)

    logger.info(f"Moved {moved_files} files")


main()
