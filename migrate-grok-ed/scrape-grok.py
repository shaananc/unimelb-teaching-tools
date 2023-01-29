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
import bs4
import sys

from pathlib import Path

sys.path.insert(0, str(Path(os.path.realpath(__file__)).parent.parent))
from utils import (
    get_truthy_config_option,
    logger,
    cache_expiry,
)  # pylint:disable=wrong-import-position


MODULE_CONFIG_SECTION = "GROK"
course_slug = get_truthy_config_option("grok_course_slug", MODULE_CONFIG_SECTION)
#problem_suffix = get_truthy_config_option("grok_problem_suffix", MODULE_CONFIG_SECTION)

grok_url = 'https://groklearning.com' 
base_search_url = f"{grok_url}/admin/author-problems/?q_authoring_state=3&q_language=&"



full_search_url = f"{base_search_url}q={course_slug}"

FORMAT = "%(message)s"
logging.basicConfig(
    format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

logger = logging.getLogger(__name__)
log_level = get_truthy_config_option("log_level", "GLOBAL",)
if log_level: logger.setLevel(log_level)



def get_session_token():
    firefox_path = get_truthy_config_option("firefox_path","GLOBAL")
    logger.debug(f"Firefox Path is {firefox_path}")
    options = webdriver.FirefoxOptions()
    options.binary_location = firefox_path

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


def get_problems(session : FuturesSession):
    search_url = base_search_url
    hrefs = []
    while True:
        response : requests.Response = requests.get(
            search_url, cookies=get_jar(), headers={"User-agent": "your bot 0.1"}
        )
        response.raise_for_status()
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        # get all hrefs inside links that follow tbody > tr > td > a
        links = soup.select("tbody > tr > td > a")
        hrefs += [str(link.get("href")).split('/')[-2] for link in links]

        next_page_links = soup.select("nav > ul > li.active + li > a")
        next_href = next_page_links[0].get("href")
        if next_href == "#":
            break
        search_url = f"https://groklearning.com/admin/author-problems/{next_href}"
        logger.debug(search_url)


    logger.debug(hrefs)
    return hrefs



def export_problem(problem):
    response : requests.Response = \
        requests.get(f'{grok_url}/admin/author-problems/{problem}/export/', cookies=get_jar(), headers={"User-agent": "your bot 0.1"})

    response.raise_for_status()
    # check if content type is json
    if response.headers["Content-Type"] == "application/json":
        try:
            data = response.json()
        except JSONDecodeError:
            logger.error(f"Error decoding JSON for {problem}")
            return
        else:
            # make a directory for the course
            course_dir = os.path.join("output", course_slug)
            os.makedirs(course_dir, exist_ok=True)
            # write the json to a file
            with open(os.path.join(course_dir, f"{problem}.json"), "w") as f:
                f.write(response.text)



            logger.debug(f"Exported {problem}")
    else:
        logger.error(f"Error exporting {problem}: Expecting JSON, received {response.headers['Content-Type']}")

def main():

    session : FuturesSession = FuturesSession()

    try:
        session_token : str = get_truthy_config_option("grok_token", MODULE_CONFIG_SECTION)
    except ValueError:
        logger.warning("Session token not found, launching Grok Login")
        session_token = get_session_token()
        logger.debug(session_token)
    else:
        get_jar().set("grok_session", session_token, domain=".groklearning.com")

    futures = []
    problems = []
    logger.info("Getting List of Problems...")
    try:
        problems = get_problems(session)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            logger.warning("Session token was invalid, launching Grok Login")
            session_token = get_session_token()
            problems = get_problems(session)

    logger.debug(problems)

    logger.info(
        "Submitting jobs for user submissions... Warning this may take some time"
    )
    with logging_redirect_tqdm():
         for i, problem in tqdm(enumerate(problems)):
    #         # futures.append(get_submission_history(session, user))
             export_problem(problem)
             if i % 10 == 0:
                 time.sleep(0.3)  # add delay to prevent rate limiting by Grok servers

    # logger.info("Awaiting responses...")
    # with open(OUTPUT_FILENAME, "w") as f:
    #     with logging_redirect_tqdm():
    #         for future in tqdm(concurrent.futures.as_completed(futures)):
    #             response_hook(future.result(), f)


main()
