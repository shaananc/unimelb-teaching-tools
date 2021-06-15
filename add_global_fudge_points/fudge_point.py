#!/usr/bin/env python3
"""
This script is used to add fudge points to all student submissions, allowing for linear scaling of grades.
Note students who received a zero originally do not receive a grade bump, which this script presumes requires a good faith effort.

This script is supplemented by config.ini, for which a sample is provided in which the user can configure the number of fudge points to add or subtract.
"""
from rich.console import Console
from rich.panel import Panel
import sys
import os

sys.path.insert(0, os.path.abspath(".."))

from utils import (  # pylint:disable=wrong-import-position
    get_user_info,
    get_users,
    get_quiz_info,
    get_truthy_config_option,
    get_quiz_submission_history,
    submit_quiz_payload,
)

MODULE_CONFIG_SECTION = "FUDGEPOINTS"

initial_fudge_points = int(
    get_truthy_config_option("initial_fudge_points", MODULE_CONFIG_SECTION)
)
max_points = int(get_truthy_config_option("max_points", MODULE_CONFIG_SECTION))
respect_cap = bool(get_truthy_config_option("respect_cap", MODULE_CONFIG_SECTION))

console = Console()


def interactive_grader(submission):
    """Grades an individual user's submission"""
    user = get_user_info(submission["user_id"])["name"].encode("utf-8").decode("ascii")

    console.print(
        Panel(f"[bold cyan]Updating {user}[/bold cyan]", expand=False),
        justify="center",
    )

    submission_history = sorted(
        submission["submission_history"], key=lambda x: x["attempt"]
    )
    if "submission_data" not in submission_history[0]:
        return

    most_recent_answers = submission_history[0]["submission_data"]

    total = sum([i["points"] for i in most_recent_answers])
    fudge_points = initial_fudge_points
    if fudge_points > 0 and total in (0, max_points) or total == 0:
        console.print("No fudging required.")
        return

    if total + fudge_points > max_points and respect_cap:
        fudge_points = max_points - total

    console.print(f"{total} --> {total+fudge_points}")

    payload = {
        "quiz_submissions": [
            {
                "attempt": submission_history[0]["attempt"],
                "fudge_points": fudge_points,
            }
        ]
    }

    submit_quiz_payload(submission_history[0]["id"], payload)


def main():
    console.print("Downloading User Data...")
    get_users()
    console.print("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            interactive_grader(submission)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            # raise (e)
            print(e)
            continue


if __name__ == "__main__":
    main()
