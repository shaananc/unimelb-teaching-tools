#!/usr/bin/env python3
"""This module fetches get a breakdown of scores by question number for a quiz and writes it to points.csv

This script is supplemented by config.py, for which a sample is provided.
"""
from rich.console import Console
import pandas as pd
import sys
import os

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    get_user_info,
    get_quiz_info,
    get_quiz_submission_history,
    logger,
)

console = Console()


def process_submission(submission):
    """Grades an individual user's submission"""
    user = get_user_info(submission["user_id"])

    logger.info((f"[bold cyan]Fetching {user['short_name']}[/bold cyan]"))

    submission_history = sorted(
        submission["submission_history"], key=lambda x: x["attempt"]
    )
    if "submission_data" not in submission_history[0]:
        raise Exception("No data provided")

    most_recent_answers = submission_history[0]["submission_data"]

    points = [p["points"] for p in most_recent_answers]
    points_dict = dict(zip(([f"q{i}" for i in range(0, len(points))]), points))
    points_dict["name"] = user["name"].encode("utf-8").decode("ascii")
    points_dict["sid"] = user["sis_user_id"]
    points_dict["login"] = user["login_id"]
    points_dict["email"] = user["email"]
    points_dict["total"] = sum(points)

    return points_dict


def main():
    logger.info("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    all_dict = []
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            all_dict.append(process_submission(submission))
        except KeyboardInterrupt:
            continue
        except Exception as e:
            print(e)

    logger.info("Writing to CSV")
    df = pd.DataFrame.from_records(all_dict, index="sid")
    df.to_csv("points.csv", index=True)


if __name__ == "__main__":
    main()
