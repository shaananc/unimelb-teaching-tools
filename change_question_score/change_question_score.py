#!/usr/bin/env python3
"""
This script allows you to change the score for students for a particular question.

Why do this? In my exams I typically include an ungraded question in which students can express themselves.
Tutors will not grade this question, leaving the quizes partially graded and not ready for release.
By running this script, I set the points awarded for that question to zero, enabling grade posting.

This script is supplemented by config.ini and rubric.py, for which samples are provided.
"""
from rubric import rubric
from rich import print
from rich.console import Console
from rich.panel import Panel

import sys
import os

sys.path.insert(0, os.path.abspath(".."))
from utils import (  # pylint:disable=wrong-import-position
    submit_quiz_payload,
    get_quiz_info,
    get_users,
    get_user_info,
    get_quiz_submission_history,
)

console = Console()


def process_submission(submission):
    """Sets the score on an individual user's submission"""
    console.clear()
    user = get_user_info(submission["user_id"])["name"].encode("utf-8").decode("ascii")

    console.print(
        Panel(f"[bold cyan]Grading User {user}[/bold cyan]", expand=False),
        justify="center",
    )

    submission_history = sorted(
        submission["submission_history"], key=lambda x: x["attempt"]
    )
    if "submission_data" not in submission_history[0]:
        return

    most_recent_answers = submission_history[0]["submission_data"]

    question_grades = {}

    for student_answer in most_recent_answers:
        question_id = student_answer["question_id"]
        if not rubric[question_id]["total_points"]:
            q_grade = 0
            q_comment = ""
            question_grades[question_id] = {"score": q_grade, "comment": q_comment}

    payload = {
        "quiz_submissions": [
            {
                "attempt": submission_history[0]["attempt"],
                "questions": question_grades,
            }
        ]
    }
    console.print(question_grades)

    submit_quiz_payload(submission_history[0]["id"], payload)


def main():
    console.print("Downloading User Data...")
    get_users()
    console.print("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            process_submission(submission)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            # raise (e)
            print(e)
            continue


if __name__ == "__main__":
    main()
