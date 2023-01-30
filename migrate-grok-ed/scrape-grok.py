from json import JSONDecodeError
import shutil
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
import markdown
import json

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

def get_modules(session : FuturesSession):
    search_url = f'{grok_url}/admin/author-modules/?q_authoring_state=&q=comp10002-2022-s2'
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
        search_url = f"{grok_url}/admin/author-modules/{next_href}"
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
            course_dir = Path("output") / course_slug
            course_dir.mkdir(parents=True, exist_ok=True)

            # write the json to a file
            with open(Path(course_dir) / f"{problem}.json", "w") as f:
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
    # problems = []
    # logger.info("Getting List of Problems...")
    # try:
    #     problems = get_problems(session)
    # except requests.exceptions.HTTPError as err:
    #     if err.response.status_code == 401:
    #         logger.warning("Session token was invalid, launching Grok Login")
    #         session_token = get_session_token()
    #         problems = get_problems(session)

    # logger.debug(problems)

    # logger.info(
    #     "Submitting jobs for user submissions... Warning this may take some time"
    # )

    logger.debug(generate_problem_id_map())

    if False:
        with logging_redirect_tqdm():
            for i, problem in tqdm(enumerate(problems)):
                export_problem(problem)
                if i % 10 == 0:
                    time.sleep(0.3)  # add delay to prevent rate limiting by Grok servers


    modules = []
    logger.info("Getting List of Modules...")
    try:
        modules = get_modules(session)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 401:
            logger.warning("Session token was invalid, launching Grok Login")
            session_token = get_session_token()
            modules = get_modules(session)

    logger.debug(modules)

    modules_dir =Path("output") / "modules"
    os.makedirs(modules_dir, exist_ok=True)


    if True:
        with logging_redirect_tqdm():
            for i, module in tqdm(enumerate(modules)):
                export_module(module, modules_dir)
                if i % 10 == 0:
                    time.sleep(0.3)  # add delay to prevent rate limiting by Grok servers

    # logger.info("Awaiting responses...")
    # with open(OUTPUT_FILENAME, "w") as f:
    #     with logging_redirect_tqdm():
    #         for future in tqdm(concurrent.futures.as_completed(futures)):
    #             response_hook(future.result(), f)


def generate_problem_id_map():
    if generate_problem_id_map.problem_id_map:
        return generate_problem_id_map.problem_id_map

    for jf in Path("output/grok_exercises").rglob("*.json"):
        # load the json file
        data = {}
        with open(jf, "r") as f:
            data = json.load(f)
        # get the title
        #title = data["title"]
        #problem_slug = title.split(":")[0]
        problem_slug = jf.parent.name
        # get the problem id
        problem_id = (jf.name.split(".")[0])
        generate_problem_id_map.problem_id_map[problem_id] = problem_slug

    return generate_problem_id_map.problem_id_map


generate_problem_id_map.problem_id_map = {}


def export_slide(slides, slide_dir: Path):

        for i,slide in enumerate(slides):
            slide_title = slide['title']
            with open(slide_dir / f"{i}.json", "w") as f:
                json.dump(slide, f, indent=4)
            
            if slide['type'] == 1:
                problem_id = slide['problem_id']
                exercise_dir = generate_problem_id_map()[str(problem_id)]
                with open(slide_dir / f"{i}.ref", "w") as f:
                   f.write(exercise_dir)

            elif slide['type'] == 0:
                slide_content = slide['content_raw']
                with open(slide_dir / f"{i}.md", "w") as f:
                   f.write(slide_content)
                
            else:
                raise ValueError(f"Unknown slide type {slide['type']}")

def export_module(module, modules_dir: Path):
    response : requests.Response = \
        requests.get(f'{grok_url}/admin/api/module/{module}', cookies=get_jar(), headers={"User-agent": "your bot 0.1"})

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
        else:     data = data['module']

          
    else:
        logger.error(f"Error exporting {module}: Expecting JSON, received {response.headers['Content-Type']}")


    module_title = data['title']
    module_slug = data['slug']
    logger.info(f'Processing Module {str(module)}: {module_title}, {module_slug}')
    if '2022-s2' not in module_slug:
        logger.debug("skipping module, incorrect slug")
        return

    if 'assignment' in module_slug or 'playground' in module_slug:
        logger.debug("skipping module, assignment")
        return

    for submodule in data['content']:
        log.info("Skipping submodule slide processing...")
        continue
        slides = submodule['slides']

        submodule_dir = module_dir / submodule['title']
        submodule_dir.mkdir(parents=True, exist_ok=True)
        # move all the files in the module dir to the submodule dir

        export_slide(slides, submodule_dir)

        # (module_dir / f"{module}.json").unlink(missing_ok=True)
        # for f in module_dir.rglob("*"):
        #     if f.is_file():
        #         try:
        #             logger.debug(f"moving {f} to {submodule_dir}")
        #             shutil.move(f, submodule_dir)
        #         except:
        #             pass


        #break

    with open(module_dir / f"{module}.json", "w") as f:
        json.dump(data, f, indent=4)




    logger.debug(f"Exported {module}")

main()
