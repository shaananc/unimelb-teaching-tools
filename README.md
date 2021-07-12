# Unimelb CS Teaching Scripts
This repository contains collection of scripts for use with University of Melbourne teaching infrastructure.

The original set are based off work for Foundations of Algorithms by Shaanan Cohney. They make heavy use of code written for CS50, Harvard's introduction to Computer Science.

Of particular interest to individuals teaching programming is the autograding repo, which contains an image for sandboxing and testing student code submissions. It is a light wrapper around `check50` with examples.

Many of the scripts interact with either Canvas or Grok Learning, which is a structured platform for teaching programming.

The scripts generally require the user to configure either a cookie or an API key to allow access to the platforms.

The scripts also occasionally make use of undocumented APIs that were reverse engineered by Shaanan Cohney, but which may break as a result.

Scripts are largely written in Python 3.9 but may work with earlier versions.


| Folder      | Description |
| ----------- | ----------- |
| add_global_fudge_points      | Adds fudge points to a Canvas student quiz       |
| autograding      | Docker image, shell script, and python scripts, that enable automatic grading of C code (or other languages)       |
| change_question_score      | Demo of how to adjust the score students receive for a particular Canvas quiz question, for example to fix an error       |
| code_to_pdf      | Light wrapper around render50 to produce PDFs from student code       |
| download_quiz_questions      | Downloads student quiz questions locally for further analysis/autograding       |
| get_scores_grok      | Use an undocumented Grok API to fetch the full details of which tests a student has passed (beyond what the web interface allows for export)       |
| grade_coding_quiz      | Fancy terminal interface for grading Canvas quizzes, easy adaptable, faster than Speedgrader for my uses       |
| questions_to_csv      | Retrieves question-by-question points breakdown from Canvas quiz and stores it in a CSV       |




