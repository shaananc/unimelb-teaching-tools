#!/usr/bin/env python3
"""This module fetches get a breakdown of scores by question number for a quiz and writes it to points.csv

This script is supplemented by config.py, for which a sample is provided.
"""
from rich.console import Console
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    get_assignment_info,
    get_quiz_submission_history,
    get_user_info_api,
    logger,
)


console = Console()


def main():
    logger.info("Fetching Quiz Answers...")
    assignment = get_assignment_info()
    if "errors" in assignment:
        logger.error(assignment["errors"][0]["message"])
        sys.exit(1)

    assignment_id = assignment["id"]
    all_dict = defaultdict(list)
    seen_submission = set()
    for submission in get_quiz_submission_history(assignment_id):
        try:
            if submission["id"] in seen_submission:
                continue
            seen_submission.add(submission["id"])
            if submission["score"]:
                all_dict[submission["grader_id"]].append(submission["score"])

        except KeyboardInterrupt:
            continue
        except Exception as e:
            print(e)

    logger.info("Getting Grader Names")
    graders = {}
    for grader_id in all_dict.keys():
        grader_obj = get_user_info_api(grader_id)
        graders[grader_id] = grader_obj["name"]

    logger.info("Writing to CSV")
    with open("graders.csv", "w") as f:  # You will need 'wb' mode in Python 2.x
        f.write("grader, score\n")
        for grader, scores in all_dict.items():
            for score in scores:
                f.write(f"{graders[grader]},{score}\n")

        f.write("\n\n\n")
        for grader, scores in all_dict.items():
            f.write(f"{graders[grader]},{sum(scores)/len(scores)}\n")

    # df = pd.DataFrame.from_records(all_dict, index="sid")
    # df.to_csv("graders.csv", index=True)


if __name__ == "__main__":
    main()
