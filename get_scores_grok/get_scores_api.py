#!/usr/bin/env python3
"""This script uses an undocument Grok API to fetch the maximum number of tests passed by students on a problem that has multiple tests.

This script is supplemented by config.py, for which a sample is provided. 
The user can either supply the session token by extracting it from a Grok session manually, otherwise, if empty, the script will launch a Firefox instance for the user to login, and it will then automatically extract the cookie.
"""

from json import JSONDecodeError
import requests
from rich import print
from cachier import cachier
import datetime
import logging
import os
import concurrent.futures
import time
import selenium.webdriver as webdriver
import selenium.webdriver.support.ui as ui
import contextlib
from requests_futures.sessions import FuturesSession
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from rich.logging import RichHandler
import sys

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (
    get_truthy_config_option,
    logger,
    cache_expiry,
)  # pylint:disable=wrong-import-position

MODULE_CONFIG_SECTION = "GROK"
OUTPUT_FILENAME = "scores.csv"
course_slug = get_truthy_config_option("grok_course_slug", MODULE_CONFIG_SECTION)
problem_suffix = get_truthy_config_option("grok_problem_suffix", MODULE_CONFIG_SECTION)


# TODO: https://stackoverflow.com/questions/24435656/python-requests-futures-slow-not-threading-properly/24440743

base_url = "https://groklearning.com/api/"
user_url = f"{base_url}/tutor-dashboard/{course_slug}/sorted-students/?order_by=full_name&ascending=true"


logger = logging.getLogger(__name__)
FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)


def get_session_token():
    with contextlib.closing(webdriver.Firefox()) as driver:
        driver.get("https://groklearning.com/login/")
        wait = ui.WebDriverWait(driver, 180)  # timeout after 180 seconds
        wait.until(
            lambda driver: driver.find_elements_by_class_name("account-header-left")
        )
        session_token = driver.get_cookie("grok_session")["value"]
        get_jar().set("grok_session", session_token, domain=".groklearning.com")
        logger.info(f"session_token={session_token}")
        return session_token


def get_jar():
    if not get_jar.jar:
        get_jar.jar = requests.cookies.RequestsCookieJar()
    return get_jar.jar


get_jar.jar = None

# uncomment to cache the list of users, cache is stored at ~/.cachier
@cachier(stale_after=cache_expiry)
def get_users():
    resp = requests.get(user_url, cookies=get_jar())
    resp.raise_for_status()
    o = resp.json()
    print(f"Processing {len(o)} users...")
    return o


def response_hook(resp, logfile):
    # parse the json storing the result on the response object and write the result to the log file
    resp_object = None
    try:
        resp_object = resp.json()
    except JSONDecodeError as e:
        logger.error("Can't decode response")
        logger.error(resp.text)
        return

    if "full_name" not in resp_object:
        logger.error("No name attached to submission!")
        return

    name = resp_object["full_name"]
    logging.info(f"Processing {name}")

    if "submissions" not in resp_object or not resp_object["submissions"]:
        logfile.write(
            f"{name},{datetime.date.today().strftime('%Y-%m-%d %H:%M:%S')},-1\n"
        )
        return

    submissions = resp_object["submissions"]

    for submission in submissions:
        stime = submission["when"]
        stime = datetime.datetime.strptime(stime, "%Y-%m-%dT%H:%M:%S.%f%z").strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        logfile.write(f"{name},{stime},{submission['npassed']}\n")


def get_submission_history(session, user):
    problem_url = f"{base_url}/user/{user}/{problem_suffix}"
    future = session.get(
        problem_url, cookies=get_jar(), headers={"User-agent": "your bot 0.1"}
    )
    return future


def main():

    try:
        os.remove(OUTPUT_FILENAME)
    except Exception as e:
        pass

    session = FuturesSession()

    session_token = get_truthy_config_option("grok_token", MODULE_CONFIG_SECTION)
    if not session_token:
        logger.warning("Session token not found, launching Grok Login")
        session_token = get_session_token()
    else:
        get_jar().set("grok_session", session_token, domain=".groklearning.com")

    futures = []
    users = []
    logger.info("Getting User Details...")
    try:
        users = get_users()
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            logger.warning("Session token was invalid, launching Grok Login")
            session_token = get_session_token()
            users = get_users()

    logger.info(
        "Submitting jobs for user submissions... Warning this may take some time"
    )
    with logging_redirect_tqdm():
        for i, user in tqdm(enumerate(users)):
            futures.append(get_submission_history(session, user))
            if i % 10 == 0:
                time.sleep(0.3)  # add delay to prevent rate limiting by Grok servers

    logger.info("Awaiting responses...")
    with open(OUTPUT_FILENAME, "w") as f:
        with logging_redirect_tqdm():
            for future in tqdm(concurrent.futures.as_completed(futures)):
                response_hook(future.result(), f)


main()