from json import JSONDecodeError
from typing import Iterable, List, Dict, Callable, Any
import re

"""
This script scrapes problems and modules from the Grok Learning platform and exports them to a local directory.
It uses various libraries for web scraping, logging, and caching.

Modules:
    - requests: For making HTTP requests.
    - rich: For rich text and logging.
    - cachier: For caching function results.
    - tqdm: For progress bars.
    - bs4: For parsing HTML.
    - markdown: For Markdown processing.
    - convert_grok: Custom module for converting Grok problems.
    - preprocess_markdown: Custom module for preprocessing Markdown files.

Functions:
    - get_truthy_config_option(option: str, section: str = CONFIG_GLOBAL_KEY) -> str:
        Retrieves a configuration option and ensures it is set.

    - attempt_auth(f: Callable) -> Callable:
        Decorator to handle authentication and retry on HTTP 401 errors.

    - get_session_token() -> str:
        Launches a browser to log in to Grok Learning and retrieves the session token.

    - get_jar() -> requests.cookies.RequestsCookieJar:
        Returns a cookie jar for storing session cookies.

    - get_problems(session: FuturesSession) -> List[str]:
        Retrieves a list of problems from Grok Learning.

    - get_modules(session: FuturesSession) -> List[str]:
        Retrieves a list of modules from Grok Learning.

    - export_problem(problem: str) -> None:
        Exports a problem from Grok Learning to a local directory.

    - slow_tqdm(f: Callable, arg: List[Any]) -> None:
        Wraps a function with a progress bar and adds a delay to prevent rate limiting.

    - main() -> None:
        Main function to orchestrate the scraping and exporting process.

    - generate_problem_id_map() -> Dict[str, str]:
        Generates a map of problem IDs to problem slugs.

    - export_slide(slides: List[Dict[str, Any]], slide_dir: Path) -> None:
        Exports slides from a module to a local directory.

    - export_module(module: str, modules_dir: Path) -> None:
        Exports a module from Grok Learning to a local directory.

Usage:
    Run the script to scrape problems and modules from Grok Learning and export them to the "output" directory.
"""
import requests
from cachier import cachier
import datetime
import logging
import os
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
import json
import convert_grok
import preprocess_markdown
from cachier import cachier
import requests.cookies
import rich
import configparser

## Read config

logger = logging.getLogger(__name__)
FORMAT = "%(message)s"
rich_handler = RichHandler(markup=True)

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[rich_handler],
)

rich.traceback.install()

print("Reading Configuration File")
config = configparser.ConfigParser()
CONFIG_FILENAME = "config/config_busa90539.ini"
CONFIG_GLOBAL_KEY = "GLOBAL"
LOCAL_CONFIG_PATH = Path(Path(os.path.realpath(__file__)).parent / CONFIG_FILENAME)
result = []

if LOCAL_CONFIG_PATH.exists():
    result = config.read(LOCAL_CONFIG_PATH)
elif Path(CONFIG_FILENAME).exists():
    result = config.read(CONFIG_FILENAME)
else:
    raise FileNotFoundError(
        f"Could not find the configuration file '{CONFIG_FILENAME}' in either the current working directory or the script directory"
    )

assert result
print("Configuration File Successfully Read.")

global_section = config[CONFIG_GLOBAL_KEY]
cache_expiry = int(global_section.get("cache_expiry", fallback="0"))


def get_truthy_config_option(option: str, section: str = CONFIG_GLOBAL_KEY) -> str:
    """
    Retrieves a configuration option and ensures it is set.

    Args:
        option (str): The configuration option to retrieve.
        section (str, optional): The section of the configuration file. Defaults to CONFIG_GLOBAL_KEY.

    Returns:
        str: The value of the configuration option if it is set and truthy.
    """
    r = config.get(section, option=option, fallback=None)
    if not r:
        raise ValueError(f"Needed configuration value '{option}' not set")
    return r


MODULE_CONFIG_SECTION = "GROK"
course_slug = get_truthy_config_option("grok_course_slug", MODULE_CONFIG_SECTION)
# problem_suffix = get_truthy_config_option("grok_problem_suffix", MODULE_CONFIG_SECTION)
excluded_problems = config.get(MODULE_CONFIG_SECTION, option="excluded_problems", fallback="").split(",")
excluded_modules = config.get(MODULE_CONFIG_SECTION, option="excluded_modules", fallback="").split(",")
excluded_submodules = config.get(MODULE_CONFIG_SECTION, option="excluded_submodules", fallback="").split(",")

grok_url = "https://groklearning.com"
base_search_url = (
    f"{grok_url}/admin/author-problems/?q_authoring_state=3&q_language=&q={course_slug}"
)
full_search_url = f"{base_search_url}q={course_slug}"

if "log_level" in config[CONFIG_GLOBAL_KEY]:
    level = get_truthy_config_option("log_level", "GLOBAL", )
    logger.info(f"Setting log level to {level}")
    logger.setLevel(level)

log_dir = Path("output") / course_slug / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
file_handler = logging.FileHandler(filename=log_dir / "scrape_grok.log")
file_handler.formatter = logging.Formatter(
    "%(asctime)s %(name)-12s %(levelname)-8s %(message)s", datefmt="%d-%b-%y %H:%M:%S"
)
logger.addHandler(file_handler)

DRY_RUN = False


def attempt_auth(f: Callable) -> Callable:
    """
    Decorator to handle authentication and retry on HTTP 401 errors.

    Args:
        f (function): The function to decorate.

    Returns:
        function: The decorated function with authentication handling.
    """

    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 401:
                logger.warning("Session token was invalid, launching Grok Login")
                session_token = get_session_token()
                logger.debug(f"Token: {session_token}")
                return f(*args, **kwargs)

    return inner


def get_session_token() -> str:
    """
    Launches a browser to log in to Grok Learning and retrieves the session token.

    Returns:
        str: The session token retrieved after logging in.
    """
    firefox_path = get_truthy_config_option("firefox_path", "GLOBAL")
    logger.debug(f"Firefox Path is {firefox_path}")
    options = webdriver.FirefoxOptions()
    options.binary_location = firefox_path

    with contextlib.closing(webdriver.Firefox()) as driver:
        driver.get("https://groklearning.com/login/")
        wait = ui.WebDriverWait(driver, 180)  # timeout after 180 seconds
        wait.until(
            lambda driver: driver.find_elements_by_class_name("account-header-left")
        )
        cookie = driver.get_cookie("grok_session")
        if not cookie:
            raise Exception("Could not find grok_session cookie")
        session_token = cookie.get["value"]
        get_jar().set("grok_session", session_token, domain=".groklearning.com")
        logger.info(f"session_token={session_token}")
        return session_token


def get_jar() -> requests.cookies.RequestsCookieJar:
    """
    Returns a cookie jar for storing session cookies.

    Returns:
        RequestsCookieJar: The cookie jar for storing session cookies.
    """
    if not get_jar.jar:
        get_jar.jar = requests.cookies.RequestsCookieJar()
    return get_jar.jar


get_jar.jar = None


@attempt_auth
@cachier(stale_after=datetime.timedelta(days=3))
def get_problems(session: FuturesSession) -> List[str]:
    """
    Retrieves a list of problems from Grok Learning.

    Args:
        session (FuturesSession): The session to use for making requests.

    Returns:
        list: A list of problem IDs.
    """
    search_url = base_search_url
    hrefs = []
    while True:
        response: requests.Response = requests.get(
            search_url, cookies=get_jar(), headers={"User-agent": "your bot 0.1"}
        )
        response.raise_for_status()

        if "Please log in below" in response.text:
            logger.fatal("Login unsuccessful, please check your credentials")
            raise ValueError("Unsuccessful login")

        soup = bs4.BeautifulSoup(response.text, "html.parser")
        # get all hrefs inside links that follow tbody > tr > td > a
        links = soup.select("tbody > tr > td > a")
        hrefs += [str(link.get("href")).split("/")[-2] for link in links]

        next_page_links = soup.select("nav > ul > li.active + li > a")

        # deal with case where there is no next page
        if not next_page_links:
            logger.debug(
                "No next page links! Are you sure you have the right course slug and token?"
            )
            break

        next_href = next_page_links[0].get("href")
        if next_href == "#":
            break
        search_url = f"https://groklearning.com/admin/author-problems/{next_href}"
        logger.debug(search_url)

    logger.debug(hrefs)
    return hrefs


@attempt_auth
@cachier(stale_after=datetime.timedelta(days=3))
def get_modules(session: FuturesSession) -> List[str]:
    """
    Retrieves a list of modules from Grok Learning.

    Args:
        session (FuturesSession): The session to use for making requests.

    Returns:
        list: A list of module IDs.
    """
    search_url = f"{grok_url}/admin/author-modules/?q_authoring_state=&q={course_slug}"
    hrefs = []
    while True:
        response: requests.Response = requests.get(
            search_url, cookies=get_jar(), headers={"User-agent": "your bot 0.1"}
        )
        response.raise_for_status()
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        # get all hrefs inside links that follow tbody > tr > td > a
        links = soup.select("tbody > tr > td > a")
        hrefs += [str(link.get("href")).split("/")[-2] for link in links]

        next_page_links = soup.select("nav > ul > li.active + li > a")
        next_href = next_page_links[0].get("href")
        if next_href == "#":
            break
        search_url = f"{grok_url}/admin/author-modules/{next_href}"
        logger.debug(search_url)

    logger.debug(hrefs)
    return hrefs


def export_problem(problem: str) -> None:
    """
    Exports a problem from Grok Learning to a local directory.

    Args:
        problem (str): The problem ID to export.
    """
    response: requests.Response = requests.get(
        f"{grok_url}/admin/author-problems/{problem}/export/",
        cookies=get_jar(),
        headers={"User-agent": "your bot 0.1"},
    )

    response.raise_for_status()
    # check if content type is json
    if response.headers["Content-Type"] == "application/json":
        try:
            data = response.json()
        except JSONDecodeError:
            logger.error(f"Error decoding JSON for {problem}")
            return

        #TODO: there was a dangling else here i removed it.

        # make a directory for the course
        course_dir = Path("output") / course_slug / "grok_exercises"
        course_dir.mkdir(parents=True, exist_ok=True)

        # write the json to a file
        dest = Path(course_dir) / f"{problem}.json"
        logger.info(f"Exported {problem} to {dest}")
        if not DRY_RUN:
            dest.write_text(response.text)

        obj = response.json()
        title = obj["title"]
        if title.startswith("Ex"):
            title = title.split(":")[0]
        else:
            return
        problem_obj: convert_grok.Problem = convert_grok.Problem(
            title.replace("Exercise ", "Ex"),
            obj,
            course_dir / title.replace("Exercise ", "Ex"),
        )
        problem_obj.load()

        content_file = problem_obj.wd / "content.md"
        if content_file.exists():
            preprocess_markdown.process_file(content_file)
            preprocess_markdown.unescape_file(content_file.with_suffix(".xml"))

        content_file = problem_obj.wd / "solution_notes.md"
        if content_file.exists():
            preprocess_markdown.process_file(content_file)
            preprocess_markdown.unescape_file(content_file.with_suffix(".xml"))

    else:
        logger.error(
            f"Error exporting {problem}: Expecting JSON, received {response.headers['Content-Type']}"
        )


def slow_tqdm(f: Callable, iter: Iterable, args=None) -> None:
    """
    Wraps a function with a progress bar and adds a delay to prevent rate limiting.

    Args:
        f (function): The function to wrap.
        arg (iterable): The iterable to process with the function.
    """
    with logging_redirect_tqdm():
        for i, elem in tqdm(enumerate(iter)):
            args = args or ()
            f(elem, *args)
            if i % 10 == 0:
                time.sleep(0.3)  # add delay to prevent rate limiting by Grok servers


def main() -> None:
    """
    Main function to orchestrate the scraping and exporting process.
    """
    session: FuturesSession = FuturesSession()

    # Get the session token and validate
    try:
        session_token: str = get_truthy_config_option(
            "grok_token", MODULE_CONFIG_SECTION
        )

        # remove starting ' and ending ' from the token if it does exist
        if session_token.startswith("'") and session_token.endswith("'"):
            session_token = session_token[1:-1]

        if not session_token:
            raise ValueError("Session token not found")
    except ValueError:
        logger.warning("Session token not found, launching Grok Login")
        session_token = get_session_token()
        logger.debug(session_token)
    else:
        get_jar().set("grok_session", session_token, domain=".groklearning.com")

    # get list of problems and export
    logger.info("Getting List of Problems...")
    problems = get_problems(session)
    logger.debug(problems)
    slow_tqdm(export_problem, problems)
    logger.debug(generate_problem_id_map())

    # sys.exit(0)

    # get list of modules and export
    logger.info("Getting List of Modules...")
    modules = get_modules(session)
    logger.debug(modules)
    modules_dir = Path("output") / course_slug / "modules"
    os.makedirs(modules_dir, exist_ok=True)
    slow_tqdm(export_module, modules, [modules_dir])

    # TODO: what about getting slides outside module and exporting


def generate_problem_id_map() -> Dict[str, str]:
    """
    Generates a map of problem IDs to problem slugs.

    Returns:
        dict: A dictionary mapping problem IDs to problem slugs.
    """
    if generate_problem_id_map.problem_id_map:
        return generate_problem_id_map.problem_id_map

    for jf in Path(f"output/{course_slug}/grok_exercises").rglob("*.json"):
        # load the json file
        data = {}
        with open(jf, "r") as f:
            data = json.load(f)
        # get the title
        # title = data["title"]
        # problem_slug = title.split(":")[0]
        problem_slug = jf.parent.name
        # get the problem id
        problem_id = jf.name.split(".")[0]
        generate_problem_id_map.problem_id_map[problem_id] = problem_slug

    return generate_problem_id_map.problem_id_map


generate_problem_id_map.problem_id_map = {}


def export_slide(slides: List[Dict[str, Any]], slide_dir: Path) -> None:
    """
    Exports slides from a module to a local directory.

    Args:
        slides (list): The list of slides to export.
        slide_dir (Path): The directory to export the slides to.
    """
    for i, slide in enumerate(slides):
        slide_title = slide["title"]
        dest = slide_dir / f"{i}.json"

        logger.info(f"Exported {slide_title} to {dest}")
        if not DRY_RUN:
            dest.write_text(json.dumps(slide, indent=4))
        if "problem_id" in slide and slide["problem_id"] in excluded_problems:
            continue
        if slide["type"] == 1:
            problem_id = slide["problem_id"]
            if problem_id in excluded_problems:
                continue
            if not problem_id in generate_problem_id_map():
                logger.warning(f"{problem_id} not in {excluded_problems} but not found in grok_exercises")
                continue
            exercise_dir = generate_problem_id_map()[str(problem_id)]
            dest = Path(slide_dir) / f"{i}.ref"
            logger.info(f"Exported {slide_title} to {dest}")
            if not DRY_RUN:
                dest.write_text(exercise_dir)

        elif slide["type"] == 0:
            slide_content = slide["content_raw"]
            dest = Path(slide_dir) / f"{i}.md"
            logger.info(f"Exported {slide_title} to {dest}")
            if not DRY_RUN:
                dest.write_text(slide_content)
            download_resources(slide_content)

        else:
            raise ValueError(f"Unknown slide type {slide['type']}")


@attempt_auth
def download_resources(slide_content: str):
    """
    Downloads resources - images and additional scripts from a slide's content and saves in resources folder

    Args:
        slide_content: content to be parsed for grok learning cdn hyperlinks for resources
    """
    pattern = r'https://groklearning-cdn\.com/[^\s")]+'
    matches = re.findall(pattern, slide_content)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    })
    for match in matches:
        logger.info(f"Downloading resources : {match}")
        response: requests.Response = session.get(match)

        response.raise_for_status()
        resources_dir = Path("output") / course_slug / "resources"
        resources_dir.mkdir(parents=True, exist_ok=True)

        content_type = response.headers.get('Content-Type', '').lower()
        filename = "_".join(match.split("/")[-2:])

        if "image" in content_type:
            # Handle image files
            file_path = os.path.join(resources_dir, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Image saved to {file_path}")
        elif "text" in content_type or "json" in content_type:
            # Handle text-based files
            file_path = os.path.join(resources_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(response.text)
            print(f"Text saved to {file_path}")
        else:
            # Handle other binary files
            file_path = os.path.join(resources_dir, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Binary file saved to {file_path}")


def export_module(module: str, modules_dir: Path) -> None:
    """
    Exports a module from Grok Learning to a local directory.

    Args:
        module (str): The module ID to export.
        modules_dir (Path): The directory to export the module to.
    """
    response: requests.Response = requests.get(
        f"{grok_url}/admin/api/module/{module}",
        cookies=get_jar(),
        headers={"User-agent": "your bot 0.1"},
    )

    response.raise_for_status()

    # check if content type is json

    module_dir = modules_dir / str(module)
    module_dir.mkdir(parents=True, exist_ok=True)

    data = {}
    if response.headers["Content-Type"] == "application/json":
        try:
            data = response.json()
        except JSONDecodeError:
            logger.error(f"Error decoding JSON for {module}")
            return
        else:
            data = data["module"]

    else:
        logger.error(
            f"Error exporting {module}: Expecting JSON, received {response.headers['Content-Type']}"
        )

    module_title = data["title"]
    module_slug = data["slug"]
    logger.info(f"Processing Module {str(module)}: {module_title}, {module_slug}")
    if "2024" not in module_slug:  # Removed s2 from the condition as some subjects are only available in s1
        logger.info("skipping module, incorrect slug")
        return

    if "assignment" in module_slug or "playground" in module_slug:
        logger.info("skipping module, assignment")
        return

    idx: int = 0
    for submodule in data["content"]:
        slides = submodule["slides"]
        submodule_title: str = str(idx) + "_" + submodule["title"]
        submodule_dir = module_dir / submodule_title
        submodule_dir.mkdir(parents=True, exist_ok=True)
        idx += 1
        # move all the files in the module dir to the submodule dir
        slug = data["slug"]
        if slug in excluded_submodules:
            continue

        export_slide(slides, submodule_dir)

    (module_dir / f"{module}.json").write_text(json.dumps(data, indent=4))
    title = data["title"]
    slug = data["slug"]
    logging.debug(f"Obtained Slug and Title: {slug}, {title}")
    if course_slug not in slug:
        logging.warning("Skipping module, incorrect slug: " + slug)
        return

    if slug in excluded_modules:
        return

    # import ipdb

    # ipdb.set_trace()
    # if title.startswith("Ex"):
    #     title = title.split(":")[0]
    # else:
    #     logging.warning("Skipping module, incorrect title: " + title)
    #     return

    sub_dir = Path("output") / course_slug / "grok_exercises" / title


main()
