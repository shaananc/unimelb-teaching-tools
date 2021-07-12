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


# Global variables for API use
global_section = config[CONFIG_GLOBAL_KEY]
headers = {"Authorization": "Bearer " + global_section["canvas_token"]}
canvas_api_url = global_section["canvas_api_url"]
class_url = f'{canvas_api_url}/courses/{global_section["canvas_course_id"]}'
quiz_url = f'{class_url}/quizzes/{global_section["quiz_id"]}'
students_url = f"{class_url}/search_users"
quiz_submissions_url = f"{quiz_url}/submissions"
cache_expiry = int(global_section.get("cache_expiry", fallback="0"))


def canvas_handled_get_request(url, payload) -> Response:
    r = requests.get(url, headers=headers, params=payload)
    if r.status_code == 401:
        logger.error(
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
            url = r.links.get("next")
            if url:
                url = url["url"]
            else:
                break
        else:
            break
    return users


def get_user_info(user_id: int) -> Dict[str, Optional[Union[int, str]]]:
    try:
        return get_users()[user_id]
    except KeyError:
        get_users.clear_cache()
        return get_users()[user_id]


def get_quiz_info() -> Dict[str, Any]:
    payload = {
        "include[]": [],
    }
    r = requests.get(quiz_url, headers=headers, params=payload)
    return json.loads(r.text)


def get_quiz_submission_history(quiz_assignment_id: int) -> Iterator[Dict[str, Any]]:
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
            url = r.links.get("next")
            if url:
                url = url["url"]
            else:
                break
        else:
            break


def get_truthy_config_option(option: str, section: str = CONFIG_GLOBAL_KEY) -> str:
    r = config.get(section, option=option)
    if not r:
        raise ValueError(f"Needed configuration value '{option}' not set")
    return r


def submit_quiz_payload(submission_id, payload) -> None:
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
