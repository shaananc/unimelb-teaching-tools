import requests
import sys
import json
from cachier import cachier
from datetime import timedelta
import configparser
from pathlib import Path
import os

config = configparser.ConfigParser()
CONFIG_FILENAME = "config.ini"
CONFIG_GLOBAL_KEY = "GLOBAL"
if Path(CONFIG_FILENAME).exists():
    config.read(CONFIG_FILENAME)
elif Path(os.path.realpath(__file__)).exists():
    config.read(Path(os.path.realpath(__file__)) / CONFIG_FILENAME)
else:
    raise FileNotFoundError(
        "Could not find the configuration file 'config.ini' in either the current working directory or the script directory"
    )

# Global variables for API use
global_section = config[CONFIG_GLOBAL_KEY]
headers = {"Authorization": "Bearer " + global_section["canvas_token"]}
canvas_api_url = global_section["canvas_api_url"]
class_url = f'{canvas_api_url}/courses/{global_section["canvas_course_id"]}'
quiz_url = f'{class_url}/quizzes/{global_section["quiz_id"]}'
students_url = f"{class_url}/search_users"
quiz_submissions_url = f"{quiz_url}/submissions"
cache_expiry = int(global_section.get("cache_expiry", fallback="0"))


def canvas_handled_get_request(url, payload):
    r = requests.get(url, headers=headers, params=payload)
    if r.status_code == 401:
        print(
            requests.exceptions.HTTPError(
                "Received HTTP 401: Unauthorized Access. Likely your token was invalid."
            )
        )
        sys.exit(1)
    return r


# uncomment to cache the list of users, cache is stored at ~/.cachier
@cachier(stale_after=timedelta(days=cache_expiry))
def get_users():
    users = {}
    payload = {
        "include[]": [],
    }
    url = students_url
    while True:
        r = canvas_handled_get_request(url, payload)
        vals = json.loads(r.text)
        users |= {u["id"]: u for u in vals}
        if r.links.get("next"):
            url = r.links.get("next")["url"]
        else:
            break
    return users


def get_user_info(user_id: int):
    return get_users()[user_id]


def get_quiz_info():
    payload = {
        "include[]": [],
    }
    r = requests.get(quiz_url, headers=headers, params=payload)
    return json.loads(r.text)


def get_quiz_submission_history(quiz_assignment_id: int):
    url = f"{class_url}/assignments/{quiz_assignment_id}/submissions"
    payload = {
        "include[]": ["submission_history"],
    }

    while True:
        r = requests.get(url, headers=headers, params=payload)
        submissions = json.loads(r.text)
        for submission in submissions:
            yield submission
        if r.links.get("next"):
            url = r.links.get("next")["url"]
        else:
            break


def get_truthy_config_option(option, section=CONFIG_GLOBAL_KEY):
    r = config.get(section, option=option)
    if not r:
        raise ValueError(f"Needed configuration value '{option}' not set")
    return r


def submit_quiz_payload(submission_id, payload):
    r = requests.put(
        f"{quiz_submissions_url}/{submission_id}",
        headers=headers,
        json=payload,
    )
    if r.ok:
        print("Successfully submitted")
    else:
        r.raise_for_status()


def get_quiz_answers(submission_id: int):
    """Gets the official answers for a quiz"""
    quiz_submissions_questions_url = (
        f"{canvas_api_url}/quiz_submissions/{submission_id}/questions"
    )
    payload = {
        "include[]": [],
    }
    r = requests.get(quiz_submissions_questions_url, headers=headers, params=payload)
    questions = json.loads(r.text)
    return sorted(questions["quiz_submission_questions"], key=lambda x: x["position"])
