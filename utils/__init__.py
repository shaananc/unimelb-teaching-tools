import requests
import sys
import json
from cachier import cachier
from datetime import timedelta
import configparser
from pathlib import Path
import os
import logging
from typing import Any, Dict, Iterator, Optional, Union
from rich.logging import RichHandler
import rich.traceback
from requests.models import Response

logger = logging.getLogger(__name__)
FORMAT = "%(message)s"
rich_handler = RichHandler(markup=True)
file_handler = logging.FileHandler(filename="unimelblib.log")
file_handler.formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%d-%b-%y %H:%M:%S"
)

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[rich_handler, file_handler],
)


rich.traceback.install()

logger.info("Reading Configuration File")
config = configparser.ConfigParser()
CONFIG_FILENAME = "config.ini"
CONFIG_GLOBAL_KEY = "GLOBAL"
LOCAL_CONFIG_PATH = Path(Path(os.path.realpath(__file__)).parent / CONFIG_FILENAME)
result = []

if LOCAL_CONFIG_PATH.exists():
    result = config.read(LOCAL_CONFIG_PATH)
elif Path(CONFIG_FILENAME).exists():
    result = config.read(CONFIG_FILENAME)
else:
    raise FileNotFoundError(
        "Could not find the configuration file 'config.ini' in either the current working directory or the script directory"
    )

assert result
logger.info("Configuration File Successfully Read.")


if "log_level" in config[CONFIG_GLOBAL_KEY]:
    level = config[CONFIG_GLOBAL_KEY]["log_level"]
    logger.info(f"Setting log level to {level}") 
    logger.setLevel(level)


# Global variables for API use
global_section = config[CONFIG_GLOBAL_KEY]

canvas_token = config.get(CONFIG_GLOBAL_KEY, "canvas_token", fallback=None)
if not canvas_token:
    logger.warning("No Canvas Token found in config.ini")
canvas_headers = {"Authorization": "Bearer " + str(canvas_token)} if canvas_token else None
canvas_api_url = config.get(CONFIG_GLOBAL_KEY, "canvas_api_url", fallback=None)
if not canvas_api_url:
    logger.warning("No Canvas API URL found in config.ini")

canvas_course_id = config.get(CONFIG_GLOBAL_KEY, "canvas_course_id", fallback=None)
if not canvas_course_id:
    logger.warning("No Canvas Course ID found in config.ini")    
class_url = f'{canvas_api_url}/courses/{canvas_course_id}' if canvas_course_id else None
quiz_id = config.get(CONFIG_GLOBAL_KEY, "quiz_id", fallback=None)
if not quiz_id:
    logger.warning("No Quiz ID found in config.ini")
quiz_url = f'{class_url}/quizzes/{quiz_id}' if quiz_id else None
assignment_url = f'{class_url}/assignments//{quiz_id}'
students_url = f"{class_url}/search_users"
quiz_submissions_url = f"{quiz_url}/submissions"
cache_expiry = int(global_section.get("cache_expiry", fallback="0"))
user_api = f'{canvas_api_url}/users'


def canvas_handled_get_request(url, payload) -> Response:
    r = requests.get(url, headers=canvas_headers, params=payload)
    if r.status_code == 401:
        logger.error(
            requests.exceptions.HTTPError(
                "Received HTTP 401: Unauthorized Access. Likely your token was invalid."
            )
        )
        sys.exit(1)
    return r


@cachier(stale_after=timedelta(days=cache_expiry))
def get_users_ids():
    users = {}
    payload = {
        "include[]": [],
    }
    url = students_url
    while True:
        r = canvas_handled_get_request(url, payload)
        vals = json.loads(r.text)
        users |= {u["id"]: u for u in vals}
        link = r.links.get("next")
        if link:
            url = link["url"]
            if not url:
                break
        else:
            break
    return users


def get_links():
    pass


def get_user_info_api(user_id: int) -> Dict[str, Any]:
    url = f"{user_api}/{user_id}/profile"
    r = requests.get(url, headers=canvas_headers)
    return json.loads(r.text)


def get_user_info(user_id: int) -> Dict[str, Optional[Union[int, str]]]:
    try:
        return get_users_ids()[user_id]
    except KeyError:
        get_users_ids.clear_cache()
        return get_users_ids()[user_id]


def get_quiz_info() -> Dict[str, Any]:
    payload = {
        "include[]": [],
    }
    r = requests.get(quiz_url, headers=canvas_headers, params=payload)
    return json.loads(r.text)


def get_assignment_info() -> Dict[str, Any]:
    payload = {
        "include[]": [],
    }
    r = requests.get(assignment_url, headers=canvas_headers, params=payload)
    return json.loads(r.text)

def get_quiz_submission_history(quiz_assignment_id: int) -> Iterator[Dict[str, Any]]:
    url = f"{class_url}/assignments/{quiz_assignment_id}/submissions"
    payload = {
        "include[]": ["submission_history"],
    }

    while True:
        r = requests.get(url, headers=canvas_headers, params=payload)
        submissions = json.loads(r.text)
        for submission in submissions:
            yield submission
        link = r.links.get("next")
        if link:
            url = link["url"]
            if not url:
                break
        else:
            break


def get_truthy_config_option(option: str, section: str = CONFIG_GLOBAL_KEY) -> str:
    r = config.get(section, option=option, fallback=None)
    if not r:
        raise ValueError(f"Needed configuration value '{option}' not set")
    return r


def submit_quiz_payload(submission_id, payload) -> None:
    logger.info(payload)
    r = requests.put(
        f"{quiz_submissions_url}/{submission_id}",
        headers=canvas_headers,
        json=payload,
    )
    if r.ok:
        logger.info("Successfully submitted grade")
    else:
        r.raise_for_status()


def get_course_users():
    """Alternate API call to get course users"""
    url = f"{class_url}/users"
    payload = {"sort": "username", "include[]": []}

    while True:
        r = canvas_handled_get_request(url, payload)
        submissions = json.loads(r.text)
        for submission in submissions:
            yield submission
        link = r.links.get("next")
        if link:
            url = link["url"]
            if not url:
                break
        else:
            break


def get_quiz_answers(submission_id: int):
    """Gets the official answers for a quiz"""
    quiz_submissions_questions_url = (
        f"{canvas_api_url}/quiz_submissions/{submission_id}/questions"
    )
    payload = {
        "include[]": [],
    }
    r = canvas_handled_get_request(quiz_submissions_questions_url, payload)
    questions = json.loads(r.text)
    return sorted(questions["quiz_submission_questions"], key=lambda x: x["position"])


@cachier(stale_after=timedelta(days=cache_expiry))
def get_section_info():
    """Gets a list of sections and students enrolled in them"""
    url = class_url + "/sections"
    payload = {
        "include[]": ["students", "total_students", "enrollments"],
    }
    sections = []
    while True:
        r = canvas_handled_get_request(url, payload)
        sections += json.loads(r.text)
        link = r.links.get("next")
        if link:
            url = link["url"]
            if not url:
                break
        else:
            break

    logger.info(sections)
    return sections
