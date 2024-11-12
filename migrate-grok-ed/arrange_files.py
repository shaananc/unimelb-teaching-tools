
import os
import json
import shutil
import pathlib
from pathlib import Path

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




def main():

    # this is a one-time script to arrange the files in a more logical way
    
    # get the directory the executing file is in
    cwd = Path(os.path.dirname(os.path.realpath(__file__)))
    # get the path to the output/grok_exercises directory
    output_base = cwd / "output" / "grok_exercises"
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
        if "unimelb-comp10001-2024-s2" not in slug:
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