#!/usr/bin/env python3
"""This module is an autograder for Canvas Quizzes that interfaces with the Canvas API.
It uses Docker as a sandbox, running check50 to process assignments.

Using it requires config.ini to be modified with an apporpriate Canvas API token and the path to the CS50 style checks to be run. 
Use rubric.py to configure each individual question. The question IDs are sourced from the Canvas API.
"""
import json
from operator import itemgetter
from rubric import rubric
import html2text
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel
from rich.console import RenderGroup
from rich.progress import Progress
from rich.highlighter import ReprHighlighter
import sys
import os

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (  # pylint:disable=wrong-import-position
    get_quiz_submission_history,
    get_quiz_info,
    get_user_info,
    get_users,
    submit_quiz_payload,
    get_truthy_config_option,
    logger,
)

import subprocess
from pathlib import Path
import shutil

console = Console()
highlighter = ReprHighlighter()

MODULE_CONFIG_SECTION = "GRADER"


def run_checks(student_dir: Path):
    """Calls into the CS50 check50 library with appropriate setup to actually run the automated tests"""

    path_to_checks = get_truthy_config_option("path_to_checks", MODULE_CONFIG_SECTION)
    path_to_dist = get_truthy_config_option("path_to_dist", MODULE_CONFIG_SECTION)

    command = [
        "docker",
        "run",
        f"--volume={Path(path_to_checks).absolute()}:/opt/check_files",
        f"--volume={Path(student_dir).absolute()}:/src",
        f"--volume={Path(path_to_dist).absolute()}:/dist",
        "--rm",
        "-ti",
        "shaananc/check50",
        "check50",
        "-o",
        "json",
        "--dev",
        "/opt/check_files",
    ]

    p = subprocess.run(command, capture_output=True, check=False)
    results = p.stdout.decode("ascii")
    return json.loads(results)


def run_automated_tests(most_recent_answers):
    """Runs automated tests over a student submission"""
    student_dir = Path("./tmp/autograding/")
    for answer in most_recent_answers:
        question_id = answer["question_id"]
        if (
            "skip" not in rubric[question_id]
            and answer["correct"] != True
            and answer["correct"] != False
            and ("tests" in rubric[question_id])
        ):

            Path(student_dir).mkdir(parents=True, exist_ok=True)
            with open(student_dir.joinpath(f"./{question_id}.c"), "a") as f:
                f.write("\n")
                f.write(html2text.html2text(answer["text"]))

    with Progress(expand=True) as progress:
        task1 = progress.add_task(
            "[red]Running automated tests...", start=False, transient=True
        )
        results = run_checks(student_dir)
        progress.start_task(task1)
        progress.update(task1, total=100, completed=100)

    shutil.rmtree(student_dir)

    return results


def generate_test_output_panel(test):
    panel_items = []
    if test["passed"] == False and "expected" in test["cause"]:
        panel_items.append("[magenta]Automated Tests Failed.[/magenta]\n")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Actual")
        table.add_column("Expected")
        table.add_row(
            f'[red]{test["cause"]["actual"]}[/red]',
            f'[green]{test["cause"]["expected"]}[/green]',
        )
        panel_items.append(table)
    else:
        panel_items.append("[magenta]Automated Compilation Failed.[/magenta]\n")

    return panel_items


def interactive_grade(
    student_answer, tests, results, rubric_description, full_score, internal_title, idx
):
    panel_items = []
    score_pts = 0
    score_comment = ""
    if tests:
        for test_name, pts in tests.items():
            if test_name in results:
                test = results[test_name]
                if test["passed"]:
                    panel_items.append(
                        f"[green]{test_name} Passed: {pts} points![/green]\n"
                    )
                    score_pts += pts
                else:
                    panel_items += generate_test_output_panel(test)

        score_comment = ""

        student_code = Syntax(
            html2text.html2text(student_answer["text"]),
            "c",
            theme="monokai",
            line_numbers=True,
        )
        panel_items.append(student_code)

        if score_pts != full_score:
            if rubric_description:
                panel_items.append(f"[green]Rubric: {rubric_description}[/green]\n")

            console.print(Panel(RenderGroup(*panel_items), title=internal_title))

            score_in = input("{}: ?/{}  ".format(f"Question {idx+1}", full_score))
            score_split = score_in.split(" ")
            score_pts = min(round(float(score_split[0]), 1), full_score)
            score_comment = " ".join(score_split[1:])
        else:

            console.print(Panel(RenderGroup(*panel_items), title=internal_title))
            console.print(f"Question {idx+1}: {full_score}/{full_score}")

    return (
        score_pts,
        score_comment,
    )


def canvas_grade(student_answer, internal_title, full_score, idx):
    panel_items = []
    score_pts = 0
    was_graded = True
    if student_answer["correct"]:
        panel_items.append("[green]Answer was correct![/green]\n")
        console.print(Panel(RenderGroup(*panel_items), title=internal_title))
        console.print(f"Question {idx+1}: {full_score}/{full_score}\n")
        score_pts = full_score
    elif student_answer["correct"] == False:
        panel_items.append("[magenta]Answer was incorrect.[/magenta]\n")
        console.print(Panel(RenderGroup(*panel_items), title=internal_title))
        console.print(f"Question {idx+1}: {score_pts}/{full_score}\n")
    elif not student_answer["text"]:
        panel_items.append("[magenta]No student answer submitted![/magenta]\n")
        console.print(Panel(RenderGroup(*panel_items), title=internal_title))
        console.print(f"Question {idx+1}: {score_pts}/{full_score}\n")
    else:
        was_graded = False

    return score_pts, was_graded


def grade_question(results, student_answer, idx: int) -> tuple[float, str]:
    """Grades a single question, in the context of a submission"""
    question_id = student_answer["question_id"]

    internal_title, full_score, rubric_description, tests = itemgetter(
        "name", "total_points", "rubric_description", "tests"
    )(rubric[question_id])

    # If student_answer["correct"] is True or False, the question was graded by Canvas itself, likely as a multiple-choice
    score_pts, was_canvas_graded = canvas_grade(
        student_answer, internal_title, full_score, idx
    )
    comment = ""
    # if not autograded by canvas, run the full grader
    if not was_canvas_graded:
        score_pts, _ = interactive_grade(
            student_answer,
            tests,
            results,
            rubric_description,
            full_score,
            internal_title,
            idx,
        )
        comment += input("Question Comments:\n") + "\n\n"

    grade = min(round(score_pts, 1), full_score)
    comment += "{}: {}/{}".format(f"Question {idx+1}", score_pts, full_score)

    return grade, comment


def get_question_score(idx, student_answer, autograder_results):
    question_id = student_answer["question_id"]
    if "skip" in rubric[question_id]:
        return {}

    if not rubric[question_id]["total_points"]:
        q_grade = 0
        q_comment = ""
        return {"score": q_grade, "comment": q_comment}

    q_grade, q_comment = grade_question(autograder_results, student_answer, idx)
    return {"score": q_grade, "comment": q_comment}


def grade_submission(submission):
    """Grades an individual user's submission"""
    console.clear()
    user = get_user_info(submission["user_id"])["name"].encode("utf-8").decode("ascii")

    logger.info(f"Grading User {user}")
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

    results = run_automated_tests(most_recent_answers)

    question_grades = {}
    # Loop until the user confirms that they are happy with the submission
    while True:
        comment = "Scores by Question:\n"
        grade = 0.0

        for idx, student_answer in enumerate(most_recent_answers):
            question_grade_dict = get_question_score(idx, student_answer, results)
            question_grades[student_answer["question_id"]] = question_grade_dict

        console.print(Panel(highlighter(comment)))
        console.print(f"Grade: {grade}")
        confirm = input("Correct? [y/N/cancel].")

        if "Y" in confirm or "y" in confirm:
            payload = {
                "quiz_submissions": [
                    {
                        "attempt": submission_history[0]["attempt"],
                        "questions": question_grades,
                    }
                ]
            }

            submit_quiz_payload(submission_history[0]["id"], payload)

        elif confirm == "" or confirm[0] == "N" or confirm[0] == "n":
            continue
        else:
            return


def main():
    logger.info("Downloading User Data...")
    get_users()
    logger.info("Fetching Quiz Answers...")
    quiz = get_quiz_info()
    quiz_assignment_id = quiz["assignment_id"]
    for submission in get_quiz_submission_history(quiz_assignment_id):
        try:
            grade_submission(submission)
        except KeyboardInterrupt:
            continue
        except Exception as e:
            raise (e)
            console.print(e)
            continue


if __name__ == "__main__":
    main()
