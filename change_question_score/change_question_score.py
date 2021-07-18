#!/usr/bin/env python3
"""
This script allows you to change the score for students for a particular question.
Currently it is configured to set all questions with a maximum score of 0 to 0 in each students' submission

Why do this? In my exams I typically include an ungraded question in which students can express themselves.
Tutors will not grade this question, leaving the quizes partially graded and not ready for release.
By running this script, I set the points awarded for that question to zero, enabling grade posting.

This script is supplemented by config.ini and rubric.py, for which samples are provided.
"""
from rich import print
from rich.console import Console

import sys
import os

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    submit_quiz_payload,
    get_quiz_info,
    get_users_ids,
    get_user_info,
    get_quiz_submission_history,
    logger,
)
from rubric import rubric

console = Console()


def process_submission(submission):
    """Sets the score on an individual user's submission"""
    user = get_user_info(submission["user_id"])["name"].encode("utf-8").decode("ascii")

    logger.info(f"[bold cyan]Processing User {user}[/bold cyan]")

    submission_history = sorted(
        submission["submission_history"], key=lambda x: x["attempt"]
    )
    if "submission_data" not in submission_history[0]:
        return

    most_recent_answers = submission_history[0]["submission_data"]

    question_grades = {}

    for student_answer in most_recent_answers:
        question_id = student_answer["question_id"]
        if question_id not in rubric:
            raise KeyError(f"Rubric is missing entry for Question {question_id}")
        # this controls which question to set to zero, change this condition as needed
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
    logger.info(question_grades)

    submit_quiz_payload(submission_history[0]["id"], payload)


def main():
    logger.info("Downloading User Data...")
    get_users_ids()
    logger.info("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            process_submission(submission)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            raise (e)
            continue


if __name__ == "__main__":
    main()
