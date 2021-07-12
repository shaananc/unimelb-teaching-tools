#!/usr/bin/env python3
"""This script downloads student quiz responses into individual files within ./{quiz_id}/
The subfolder 'by_user' contains one folder for each student login, within which each question is stored in its own file.
The subfolder 'by_question' contains one folder for each question, within which each user's answer is stored in its own file.

This script is supplemented by config.ini, for which a sample is provided.
"""
import html2text
from pathlib import Path
from rich.console import Console
from rich.traceback import install
import sys
import os

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    get_user_info,
    get_users,
    get_quiz_info,
    get_quiz_submission_history,
    get_truthy_config_option,
    logger,
)


MODULE_CONFIG_SECTION = "DOWNLOADER"

install()
console = Console()
quiz_id = get_truthy_config_option("quiz_id")
file_ext = get_truthy_config_option("file_ext", MODULE_CONFIG_SECTION)


def process_submission(submission):
    user = (
        get_user_info(submission["user_id"])["login_id"].encode("utf-8").decode("ascii")
    )

    logger.info("Adding User {}".format(user))

    submission_history = sorted(
        submission["submission_history"], key=lambda x: x["attempt"]
    )
    most_recent_answers = submission_history[0]["submission_data"]

    for idx, answer in enumerate(most_recent_answers):
        question_id = answer["question_id"]

        # check that the answer is not blank, and store it appropriately
        if answer["text"]:
            q_path = f"./{quiz_id}/by_question/question-{idx+1}/{user}"
            Path(q_path).mkdir(parents=True, exist_ok=True)
            with open(q_path + f"/{user}{file_ext}", "w") as f:
                f.write(html2text.html2text(answer["text"]))

            user_path = f"./{quiz_id}/by_user/{user}"
            Path(user_path).mkdir(parents=True, exist_ok=True)
            with open(user_path + f"/{question_id}{file_ext}", "a") as f:
                f.write("\n")
                f.write(html2text.html2text(answer["text"]))


def main():
    logger.info("Downloading User Data...")
    get_users()
    logger.info("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            process_submission(submission)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            logger.error(e)
            continue


if __name__ == "__main__":
    main()
