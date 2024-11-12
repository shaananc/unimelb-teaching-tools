import shutil

"""
This script is used to interact with the EdStem API to create and manage lessons, slides, and challenges.
It uses various libraries including requests, marshmallow_dataclass, pydantic, and rich for logging and pretty printing.

Classes:
    edAPI: Main class to interact with the EdStem API.
        - EDAPI_OBJ: Base class for API objects that require server-side IDs.
        - Module: Represents a module in the EdStem system.
        - Slide: Represents a slide in the EdStem system.
        - Lesson: Represents a lesson in the EdStem system.
        - Challenge: Represents a challenge in the EdStem system.

Functions:
    rsync(src: str, dest: str, args): A retrying rsync function to synchronize files.
    create_challenge(folder: Path, session: edAPI, lesson: edAPI.Lesson): Creates a challenge from a given folder.
    get_new_or_old_slide(session: edAPI, lesson: edAPI.Lesson, slide_title: str, slide_type: str) -> edAPI.Slide: Retrieves or creates a new slide.
    create_slides_and_challenges(slide_folder: Path, session: edAPI, lesson: edAPI.Lesson): Creates slides and challenges from a given folder.
    create_lesson(lesson_folder: Path, session: edAPI, module: edAPI.Module, existing_lessons): Creates a lesson from a given folder.
    create_module(module_folder: Path, session: edAPI, existing_modules, existing_lessons): Creates a module from a given folder.
    create_all_modules(session: edAPI): Creates all modules by iterating through the output/grok_exercises directory.
    main(): Main function to initiate the session and create all modules.
"""
import requests
import json
import rich

# replace print with rich.print
from rich import print
from typing import Iterable, List, Any, Mapping, Optional, Dict
from typing import ClassVar, Type
from datetime import datetime
import challenge
import lesson
import slide
from pathlib import Path
import yaml
from marshmallow_dataclass import dataclass
from marshmallow import Schema
import marshmallow_dataclass
import yaml2pyclass
from grok_problem import GrokProblem
from grok_test import GrokTest
from pydantic import BaseModel
from pprint import pprint
import subprocess
import sys
from collections import defaultdict
from retrying import retry

## add logging with rich
from rich.logging import RichHandler
import logging
import ipdb

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

ED_COURSE_ID: str = "16527"  # playground
# ED_COURSE_ID : str = '10507' -- real class

DRY_RUN = False
DRY_RUN_ALLOW_GETS = True
ALLOW_RSYNC = True


session = requests.Session()


class edAPI:

    token: Optional[str]
    base_url: Optional[str]
    class_id: Optional[str]
    url_suffix: Optional[str]

    def new(self, base_url="", token="", class_id=None, url_suffix=""):
        if not base_url:
            raise Exception("No base_url set!")
        if not token:
            raise Exception("No token set!")

        self.token = token
        self.base_url = base_url
        self.class_id = class_id
        self.url_suffix = url_suffix
        return self

    # create a new class for api requests that requires the server side id of the object to be modified
    class EDAPI_OBJ:
        token: Optional[str]
        base_url: Optional[str]
        url_suffix: Optional[str]
        id: Optional[int]
        Schema: ClassVar[Type[Schema]] = Schema  # type: ignore

        def new(self, base_url="", url_suffix="", token="", sid=None, class_id=None):
            self.base_url = base_url
            self.url_suffix = url_suffix
            self.id = sid
            self.token = token
            self.class_id = class_id

        @retry(wait_fixed=2000)
        def api_request(
            self,
            method,
            data=None,
            json_data=None,
            files=None,
            url_suffix="",
            include_sid=True,
        ):
            if not hasattr(self, "base_url") or not self.base_url:
                log.error("No base_url set!")
                raise Exception("No base_url set!")

            if not hasattr(self, "token") or not self.token:
                log.error("No token set!")
                raise Exception("No token set!")
            if self.url_suffix and not url_suffix:
                url_suffix = self.url_suffix

            full_url = self.base_url + "/" + url_suffix

            if include_sid:
                if not hasattr(self, "id") or not self.id:
                    log.error("No sid set!")
                    raise Exception("No sid set!")
                else:
                    full_url = full_url + "/" + str(self.id)

            auth = {"Authorization": "Bearer " + self.token}

            # if data: # todo add more checks here
            #     data.pop('sid')
            #     data.pop('url_suffix')
            #     data.pop('base_url')
            #     data.pop('token')

            request = None

            if data and json_data:
                raise Exception("Cannot have both data and json_data")

            if data:
                request = requests.Request(
                    method, full_url, data=data, headers=auth
                ).prepare()
            elif json_data:
                request = requests.Request(
                    method, full_url, json=json_data, headers=auth
                ).prepare()
            elif files:
                request = requests.Request(
                    method,
                    full_url,
                    files=files,
                    headers=auth,
                ).prepare()
            else:
                request = requests.Request(method, full_url, headers=auth).prepare()

            # log.debug(request.__dict__)
            if (DRY_RUN_ALLOW_GETS and method == "GET") or not DRY_RUN:
                response = session.send(request, verify=True)
                try:
                    response.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    try:
                        log.error(response.json())
                    except requests.exceptions.JSONDecodeError:
                        pass
                    raise e

                try:
                    return response.json()
                except requests.exceptions.JSONDecodeError as e:
                    if response.status_code == 200:
                        return {}
                    else:
                        raise e

            else:
                return {}

        def get_internal(self) -> Mapping[str, Any]:
            return self.api_request("GET")

        def get(self):
            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()
            data = self.get_internal()
            class_name = self.__class__.__name__
            data = data[class_name.lower()]

            obj: edAPI.EDAPI_OBJ = schema.load(data)  # type: ignore
            obj.base_url = self.base_url
            obj.url_suffix = self.url_suffix
            obj.token = self.token
            obj.class_id = self.class_id
            obj.url_suffix = self.url_suffix

            return obj

        def wrap(self, data):
            class_name = self.__class__.__name__
            return {class_name.lower(): data}

        def unwrap(self, data):
            class_name = self.__class__.__name__
            return data[class_name.lower()]

        def put(self, data=None, json_data=None, files=None):
            if json_data:
                json_data = self.wrap(json_data)
            return self.api_request("PUT", data=data, json_data=json_data, files=files)

        def delete(self):
            return self.api_request("DELETE")

        def patch(self, data=None, json_data=None):
            if json_data:
                json_data = self.wrap(json_data)
            return self.api_request("PATCH", data=data, json_data=json_data)

        def post(self, data=None, json_data=None, include_sid=True, url_suffix=""):
            if json_data:
                json_data = self.wrap(json_data)
            response = self.api_request(
                "POST",
                data=data,
                json_data=json_data,
                include_sid=include_sid,
                url_suffix=url_suffix,
            )
            if response:
                self.id = self.unwrap(response)["id"]
            return response

        def dump(self):
            return marshmallow_dataclass.class_schema(self.__class__)().dump(self)

        def json_str(self):
            return marshmallow_dataclass.class_schema(self.__class__)().dumps(self)

        def json(self):
            return json.loads(self.json_str())

        def __str__(self):
            return str(self.json_str())

        def save(self):
            return self.put(json_data=self.json())

        def create(self, create_suffix=""):
            if not create_suffix:
                create_suffix = self.url_suffix
            response = self.post(
                json_data=self.json(),
                include_sid=False,
                url_suffix=create_suffix,
            )
            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()

            class_name = self.__class__.__name__
            data = response[class_name.lower()]
            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

    @dataclass
    class Module(EDAPI_OBJ):
        name: Optional[str | None]
        user_id: Optional[int | None]
        created_at: Optional[datetime | None]
        updated_at: Optional[datetime | None]
        course_id: Optional[int | None]
        id: Optional[int | None]

        def new(self, base_url="", token="", sid=None, class_id=None):
            super().new(
                base_url=base_url,
                url_suffix=f"lessons/modules",
                token=token,
                sid=sid,
                class_id=class_id,
            )
            self.name: str | None = None
            self.user_id: int | None = None
            self.created_at: datetime | None = None
            self.updated_at: datetime | None = None
            self.course_id: int | None = None
            return self

        def create(self):
            return super().create(f"courses/{self.class_id}/{self.url_suffix}")

    @dataclass
    class Slide(EDAPI_OBJ):
        original_id: Optional[int | None]
        lesson_id: Optional[int | None]
        user_id: Optional[int | None]
        course_id: Optional[int | None]
        type: Optional[str | None]
        title: Optional[str | None]
        points: Optional[int | None]
        index: Optional[int | None]
        is_hidden: Optional[bool | None]
        status: Optional[str | None]
        correct: Optional[bool | None]
        response: Optional[str | None]
        created_at: Optional[datetime | None]
        updated_at: Optional[datetime | None]
        challenge_id: Optional[int | None]
        content: Optional[str | None]
        id: Optional[int | None]
        index: Optional[int | None]
        type: Optional[str | None]
        status: Optional[str | None]
        active_status: Optional[bool | None]
        is_survey: Optional[bool | None]
        passage: Optional[str | None]
        mode: Optional[str | None]

        def save(self):
            ffiles = {"slide": (None, json.dumps(self.dump()))}
            return self.api_request(method="PUT", files=ffiles)

        def new(self, base_url="", token="", sid=None, class_id=None):
            super().new(
                base_url=base_url,
                url_suffix="lessons/slides",
                token=token,
                sid=sid,
                class_id=class_id,
            )
            self.original_id: int | None = None
            self.lesson_id: int | None = None
            self.user_id: int | None = None
            self.course_id: int | None = None
            self.type: str | None = None
            self.title: str | None = None
            self.points: int | None = None
            self.index: int | None = None
            self.is_hidden: bool | None = None
            self.status: str | None = None
            self.correct: bool | None = None
            self.response: str | None = None
            self.created_at: datetime | None = None
            self.updated_at: datetime | None = None
            self.challenge_id: int | None = None
            self.content: str | None = None
            self.private = object()
            self.index: int | None = None
            self.type: str | None = None
            self.status: str | None = None
            self.active_status: Optional[bool | None]
            self.is_survey: Optional[bool | None]
            self.passage: Optional[str | None]
            self.mode: Optional[str | None]
            return self

        def create(self):

            ffiles = {"slide": (None, json.dumps({"type": self.type}))}
            response = self.api_request(
                method="POST",
                url_suffix=f"lessons/{self.lesson_id}/slides",
                files=ffiles,
                include_sid=False,
            )

            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()

            class_name = self.__class__.__name__
            data = response[class_name.lower()]
            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

        def put(self, data=None, json_data=None, files=None):
            return self.api_request("PUT", data=data, json_data=json_data, files=files)

        def get_challenge(self):
            schema = marshmallow_dataclass.class_schema(edAPI.Challenge)()
            challenge = edAPI.Challenge(None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None).new(self.base_url, self.token, self.challenge_id)  # type: ignore
            data = challenge.get_internal()
            class_name = edAPI.Challenge.__name__
            data = data[class_name.lower()]
            if "tickets" in data and "connect" in data["tickets"]:
                for ticket in data["tickets"]["connect"]:
                    if "from" in ticket:
                        bak = data["tickets"]["connect"]["from"]
                        del data["tickets"]["connect"]["from"]
                        data["tickets"]["connect"]["from_"] = bak
                        break

            obj: edAPI.Challenge = schema.load(data)  # type: ignore
            obj.base_url = self.base_url
            obj.token = self.token
            obj.id = self.challenge_id
            obj.url_suffix = "challenges"

            return obj

    class Lesson(EDAPI_OBJ):
        available_at: Optional[datetime | None] = None
        due_at: Optional[datetime | None] = None
        index: Optional[int | None] = None
        is_hidden: Optional[bool | None] = None
        is_timed: Optional[bool | None] = None
        is_unlisted: Optional[bool | None] = None
        late_submissions: Optional[bool | None] = None
        locked_at: Optional[datetime | None] = None
        module_id: Optional[int | None] = None
        openable: Optional[bool | None] = None
        outline: Optional[str | None] = None
        password: Optional[str | None] = None
        prerequisites: Optional[List[Any] | None] = None
        release_challenge_feedback: Optional[bool | None] = None
        release_challenge_feedback_while_active: Optional[bool | None] = None
        release_challenge_solutions: Optional[bool | None] = None
        release_challenge_solutions_while_active: Optional[bool | None] = None
        release_quiz_correctness_only: Optional[bool | None] = None
        release_quiz_solutions: Optional[bool | None] = None
        reopen_submissions: Optional[bool | None] = None
        settings: Optional[lesson.Settings | None] = None
        solutions_at: Optional[datetime | None] = None
        state: Optional[str | None] = None
        timer_duration: Optional[int | None] = None
        timer_expiration_access: Optional[bool | None] = None
        title: Optional[str | None] = None
        tutorial_regex: Optional[str | None] = None
        type: Optional[str | None] = None
        updated_at: Optional[datetime | None] = None
        last_viewed_slide_id: Optional[int | None] = None
        original_id: Optional[int | None] = None
        timer_effective_duration: Optional[int | None] = None
        slide_count: Optional[int | None] = None
        created_at: Optional[datetime | None] = None
        status: Optional[str | None] = None
        first_viewed_at: Optional[datetime | None] = None
        user_id: Optional[int | None] = None
        course_id: Optional[int | None] = None
        number: Optional[int | None] = None
        attempted_at: Optional[datetime | None] = None
        id: Optional[int | None] = None
        slides: Optional[List[slide.SlideDataClass] | None] = None

        def create(self):
            return super().create(f"courses/{self.class_id}/{self.url_suffix}")

        def new(self, base_url="", token="", sid=None, url_suffix=None, class_id=None):
            super().new(
                base_url=base_url,
                url_suffix="lessons",
                token=token,
                sid=sid,
                class_id=class_id,
            )
            if url_suffix:
                self.url_suffix = url_suffix
            self.available_at: datetime | None = None
            self.due_at: datetime | None = None
            self.index: int | None = None
            self.is_hidden: bool | None = None
            self.is_timed: bool | None = None
            self.is_unlisted: bool | None = None
            self.late_submissions: bool | None = None
            self.locked_at: datetime | None = None
            self.module_id: int | None = None
            self.openable: bool | None = None
            self.outline: str | None = None
            self.password: str | None = None
            self.prerequisites: List[Any] | None = None
            self.release_challenge_feedback: bool | None = None
            self.release_challenge_feedback_while_active: bool | None = None
            self.release_challenge_solutions: bool | None = None
            self.release_challenge_solutions_while_active: bool | None = None
            self.release_quiz_correctness_only: bool | None = None
            self.release_quiz_solutions: bool | None = None
            self.reopen_submissions: bool | None = None
            self.settings: lesson.Settings | None = None
            self.solutions_at: datetime | None = None
            self.state: str | None = None
            self.timer_duration: int | None = None
            self.timer_expiration_access: bool | None = None
            self.title: str | None = None
            self.tutorial_regex: str | None = None
            self.type: str | None = None
            self.updated_at: Optional[datetime | None] = None
            self.last_viewed_slide_id: Optional[int | None] = None
            self.original_id: Optional[int | None] = None
            self.timer_effective_duration: Optional[int | None] = None
            self.slide_count: Optional[int | None] = None
            self.created_at: Optional[datetime | None] = None
            self.status: Optional[str | None] = None
            self.first_viewed_at: Optional[datetime | None] = None
            self.user_id: Optional[int | None] = None
            self.course_id: Optional[int | None] = None
            self.number: Optional[int | None] = None
            self.attempted_at: Optional[datetime | None] = None
            self.id: Optional[int | None] = sid
            self.slides: Optional[List[slide.SlideDataClass] | None] = None

            return self

        def get_all(self):
            response = self.api_request(
                "GET", url_suffix=f"courses/{self.class_id}/lessons", include_sid=False
            )
            new_lessons = []
            new_modules = []
            lesson_schema = marshmallow_dataclass.class_schema(edAPI.Lesson)()
            for lesson in response["lessons"]:
                new_lessons.append(lesson_schema.load(lesson))

            module_schema = marshmallow_dataclass.class_schema(edAPI.Module)()
            for module in response["modules"]:
                new_modules.append(module_schema.load(module))

            return new_lessons, new_modules

    class Challenge(EDAPI_OBJ):
        check_hash: Optional[str | None]
        content: Optional[str | None]
        course_id: Optional[int | None]
        created_at: Optional[datetime | None]
        category: Optional[str | None]
        difficulty: Optional[str | None]
        due_at: Optional[datetime | None]
        exam_visibility: Optional[str | None]
        exam_visibility_alternate_hour: Optional[bool | None]
        explanation: Optional[str | None]
        features: Optional[Dict[str, bool] | None]
        id: Optional[int | None]
        is_active: Optional[bool | None]
        is_exam: Optional[bool | None]
        is_feedback_visible: Optional[bool | None]
        is_hidden: Optional[bool | None]
        kind: Optional[str | None]
        lab_category: Optional[str | None]
        lab_name_regex: Optional[str | None]
        lab_reset: Optional[bool | None]
        language: Optional[str | None]
        manual_solution_control: Optional[bool | None]
        outline: Optional[str | None]
        password: Optional[str | None]
        points: Optional[int | None]
        requires_lti_link: Optional[bool | None]
        scaffold_hash: Optional[str | None]
        score: Optional[int | None]
        sequential_completion: Optional[bool | None]
        session: Optional[str | None]
        settings: Optional[challenge.Settings | None]
        solution_hash: Optional[str | None]
        status: Optional[str | None]
        testbase_hash: Optional[str | None]
        tickets: Optional[challenge.Tickets | None]
        tutorial_regex: Optional[str | None]
        type: Optional[str | None]
        unavailable_after_completion: Optional[bool | None]
        updated_at: Optional[datetime | None]
        title: Optional[str | None]
        number: Optional[int | None]
        original_id: Optional[int | None]

        def json_str(self):
            tmp = super().dump()
            bak = tmp["tickets"]["connect"]["from_"]  # type: ignore
            tmp["tickets"]["connect"].pop("from_")  # type: ignore
            tmp["tickets"]["connect"]["from"] = bak  # type: ignore
            return json.dumps(tmp)

        def get(self):
            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()
            data = self.get_internal()
            class_name = self.__class__.__name__
            data = data[class_name.lower()]

            if "tickets" in data and "connect" in data["tickets"]:
                for ticket in data["tickets"]["connect"]:
                    if "from" in ticket:
                        bak = data["tickets"]["connect"]["from"]
                        del data["tickets"]["connect"]["from"]
                        data["tickets"]["connect"]["from_"] = bak
                        break

            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

        def new(self, base_url="", token="", sid=None, class_id=None):
            super().new(
                base_url=base_url,
                url_suffix="challenges",
                token=token,
                sid=sid,
                class_id=class_id,
            )
            self.check_hash: str | None = None
            self.content: str | None = None
            self.course_id: int | None = None
            self.created_at: datetime | None = None
            self.difficulty: str | None = None
            self.due_at: datetime | None = None
            self.exam_visibility: str | None = None
            self.exam_visibility_alternate_hour: bool | None = None
            self.explanation: str | None = None
            self.features: Dict[str, bool] | None = None
            self.id: int | None = sid
            self.is_active: bool | None = None
            self.is_exam: bool | None = None
            self.is_feedback_visible: bool | None = None
            self.is_hidden: bool | None = None
            self.kind: str | None = None
            self.lab_category: str | None = None
            self.lab_name_regex: str | None = None
            self.lab_reset: bool | None = None
            self.language: str | None = None
            self.manual_solution_control: bool | None = None
            self.original_id: int | None = None
            self.outline: str | None = None
            self.password: str | None = None
            self.requires_lti_link: bool | None = None
            self.scaffold_hash: str | None = None
            self.score: int | None = None
            self.sequential_completion: bool | None = None
            self.session: str | None = None
            self.settings: challenge.Settings | None = None
            self.solution_hash: str | None = None
            self.status: str | None = None
            self.testbase_hash: str | None = None
            self.tickets: challenge.Tickets | None = None
            self.tutorial_regex: str | None = None
            self.type: str | None = None
            self.unavailable_after_completion: bool | None = None
            self.updated_at: datetime | None = None
            self.title: str | None = None
            return self

        def save(self):
            base_suffix = self.url_suffix + "/" + str(self.id) + "/connect/"
            urls = [
                base_suffix + a for a in ["scaffold", "solution", "testbase", "check"]
            ]
            for url in urls:
                self.api_request("POST", url_suffix=url, include_sid=False)

            base_suffix = self.url_suffix + "/" + str(self.id) + "/update/"
            urls = [
                base_suffix + a for a in ["scaffold", "solution", "testbase", "check"]
            ]
            for url in urls:
                self.api_request("POST", url_suffix=url, include_sid=False)

            self.api_request(
                "POST",
                url_suffix=self.url_suffix + f"/{self.id}/connect/testbase",
                json_data=json.dumps({"user_id": None, "password": None, "i": None}),
                include_sid=False,
            )
            self.patch(json_data=self.json_str())

        def patch(self, json_data):
            data = json.loads(self.json_str())
            data.pop("check_hash")
            data.pop("scaffold_hash")
            data.pop("solution_hash")
            data.pop("testbase_hash")
            data.pop("created_at")
            data.pop("updated_at")
            data.pop("score")
            data.pop("status")

            return super().patch(json_data=data)

    def slide(self, sid=None):
        return self.Slide(
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ).new(base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id)

    def lesson(self, sid=None):
        return self.Lesson().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )

    def module(self, sid=None):
        return self.Module(None, None, None, None, None, None).new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )

    def challenge(self, sid=None):
        return self.Challenge().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )


# a retrying rsync function
@retry(wait_fixed=2000)
def rsync(src: str, dest: str, args):
    subprocess.run(
        [
            "rsync",
            *args,
            str(src),
            dest,
        ],
        timeout=20,
        check=True,
    )


def create_challenge(folder: Path, session: edAPI, lesson: edAPI.Lesson):
    # set content to the contents of content.amber
    content = (folder / "content.xml").read_text()
    # set solution_text to the contents of solution_notes.amber
    solution_text = (folder / "solution_notes.xml").read_text()

    # read in problem.yaml
    # problem = None
    problem_yaml_path = folder / "problem.yaml"
    grok_problem = GrokProblem.from_yaml(str(problem_yaml_path))

    slide = get_new_or_old_slide(session, lesson, grok_problem.title, "code")  # type: ignore
    slide.content = content
    slide.save()

    if grok_problem.language == 20:
        log.warning(
            f"Skipping slide {grok_problem.title} because it is a multiple choice quiz"
        )
        return

    mychallenge = slide.get_challenge()

    grok_ed_map = (
        ("workspace", "scaffold"),
        ("solutions", "solution"),
        ("tests", "check"),
        ("tests", "testbase"),
    )
    makefile = folder / "workspace" / "Makefile"
    for grok_folder, ed_folder in grok_ed_map:
        # log.info(f"Uploading {grok_folder} to {ed_folder}")
        for wfile in (folder / grok_folder).glob("*"):
            if not wfile.name.endswith(".yaml"):
                url = f"challenge.{mychallenge.id}.{ed_folder}@git.edstem.org:"
                if not DRY_RUN and ALLOW_RSYNC:
                    log.info(f"Uploading {wfile} to {url}")
                    rsync(str(wfile.absolute()), url, ["-r", "--exclude", "*.yaml"])
                    if makefile.exists():
                        rsync(str(makefile.absolute()), url, [])
                    else:
                        log.warning(f"Makefile does not exist at {makefile}")
                else:
                    log.warning(
                        "Not uploading files because either DRY_RUN is set or ALLOW_RSYNC is off"
                    )
    # set the content to the contents of content.amber
    mychallenge.content = content
    mychallenge.explanation = solution_text
    mychallenge.settings.build_command = "make all"  # type: ignore
    mychallenge.settings.run_command = "make run"  # type: ignore
    mychallenge.settings.check_command = "make run"  # type: ignore
    mychallenge.tickets.run_standard.build_command = "make all"  # type: ignore
    mychallenge.tickets.run_standard.run_command = "make run"  # type: ignore

    if not mychallenge.tickets:
        mychallenge.tickets = challenge.Tickets()
    if not mychallenge.tickets.mark_standard:
        mychallenge.tickets.mark_standard = challenge.Mark()
    if not mychallenge.tickets.mark_standard.run_limit:
        mychallenge.tickets.mark_standard.run_limit = challenge.MarkCustomRunLimit()

    mychallenge.tickets.mark_standard.easy = False  # penalize whitespace infractions
    mychallenge.tickets.mark_standard.run_limit.pty = False  # make the output match up with the terminal output without having to interleave
    mychallenge.type = "code"

    testcases: List[challenge.Testcase] = []
    for f in (folder / "tests").rglob("*.yaml"):
        grok_test = GrokTest.from_yaml(str(f))
        log.info(f)
        relative_dir = f.relative_to(folder / "tests").parent
        testcase = challenge.Testcase(
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        testcase.name = grok_test.label
        testcase.run_command = "./program"
        if (folder / "tests" / relative_dir / "stdin").exists():
            testcase.stdin_path = str(relative_dir / "stdin")
        else:
            log.warning(f"stdin does not exist for {grok_test.label}")
            testcase.stdin_path = str("")

        check = challenge.Check(
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )
        # if stdout exists use it, if stdio exists use that instead
        if (folder / "tests" / relative_dir / "stdout").exists():
            check.expect_path = str(relative_dir / "stdout")
        elif (folder / "tests" / relative_dir / "stdio").exists():
            check.expect_path = str(relative_dir / "stdio")
        else:
            log.warn(f"Neither stdout or stdio exist for {grok_test.label}")
            check.expect_path = str("")
            # raise Exception(f"Neither stdout or stdio exist for {grok_test.label}")

        check.type = "check_diff"
        check.source = challenge.Source("source_mixed", "")
        testcase.checks = [check]
        testcases.append(testcase)

    mychallenge.tickets.mark_standard.testcases = testcases
    mychallenge.save()
    slide.save()


def get_new_or_old_slide(
    session: edAPI, lesson: edAPI.Lesson, slide_title: str, slide_type: str
) -> edAPI.Slide:
    slide: edAPI.Slide = session.slide()
    new_slide = True
    lesson = session.lesson(lesson.id).get()  # type: ignore
    if lesson.slides:
        for t in lesson.slides:
            if t.title == slide_title:
                log.warning(f"Slide {slide_title} already exists")
                slide = session.slide(t.id).get()  # type: ignore
                new_slide = False
                break
    slide.type = slide_type
    slide.lesson_id = lesson.id
    if new_slide:
        log.info(f"Creating new slide {slide_title}")
        slide.create()
    slide.title = slide_title
    slide.save()
    return slide


def create_slides_and_challenges(
    slide_folder: Path, session: edAPI, lesson: edAPI.Lesson
):

    # TODO: check if the slide already exists

    i = 0
    while True:
        ref_path = Path(slide_folder / f"{i}.ref")
        xml_path = Path(slide_folder / f"{i}.xml")
        if ref_path.exists():
            # create challenge
            ref = ref_path.read_text()
            challenge_path = Path("output/grok_exercises") / ref
            if not challenge_path.exists():
                log.error(f"Challenge Path {challenge_path} does not exist")
                sys.exit(1)

            create_challenge(challenge_path, session, lesson)
        elif xml_path.exists():
            # create slide
            metadata = json.loads(xml_path.with_suffix(".json").read_text())
            slide = get_new_or_old_slide(session, lesson, metadata["title"], "document")
            slide.content = xml_path.read_text()
            slide.save()

        else:
            break
        i += 1


def create_lesson(
    lesson_folder: Path,
    session: edAPI,
    module: edAPI.Module,
    existing_lessons,
):
    # check if a lesson of that name already exists under that module
    lesson: edAPI.Lesson = session.lesson()
    still_not_seen = True
    if lesson_folder.name in existing_lessons:
        # check all the lessons with that name to see if they are under this module
        for l in existing_lessons[lesson_folder.name]:
            # lesson = session.lesson(l).get()
            if l.module_id == module.id:
                lesson = l
                log.warning(
                    f"Lesson {lesson_folder.name} already exists under {module.name}"
                )
                still_not_seen = False

    if still_not_seen == True:
        lesson.title = lesson_folder.name
        lesson.create()
        lesson.type = "c"
        lesson.module_id = module.id
        lesson.save()

    # create slides and challenges
    create_slides_and_challenges(lesson_folder, session, lesson)


def create_module(
    module_folder: Path, session: edAPI, existing_modules, existing_lessons
):
    # create a new lesson
    module = session.module()

    module_json_file = list(module_folder.glob("*.json"))

    if len(module_json_file) == 0:
        log.info(f"Found no json files in {module_folder}")
        return

    if len(module_json_file) != 1:
        log.error(f"Found {len(module_json_file)} json files in {module_folder}")
        sys.exit(1)
    module_json_file = module_json_file[0]
    module_json = json.loads(module_json_file.read_text())

    module.name = module_json["title"]
    if module.name in existing_modules:
        log.info(f"Module {module.name} already exists, skipping")
        module = existing_modules[module.name][0]
    else:
        log.info(f"Creating module {module.name}")
        module.create()

    # for each lesson folder in the module folder
    for lesson_folder in module_folder.iterdir():
        if not lesson_folder.is_dir():
            continue
        log.info(f"Creating lesson {lesson_folder.name}")

        # if "Chapter 10: Dynamic Structures (FOA only)" in module.name:
        #     log.info(f"Skipping {module.name} entirely")
        #     continue

        create_lesson(lesson_folder, session, module, existing_lessons=existing_lessons)


def create_all_modules(session: edAPI):
    lessons, modules = session.lesson().get_all()
    existing_modules = defaultdict(list)
    existing_lessons = defaultdict(list)
    for module in modules:
        existing_modules[module.name].append(module)
    for lesson in lessons:
        existing_lessons[lesson.title].append(lesson)

    # for every folder in output/grok_exercises
    for module_folder in Path("output/modules").iterdir():
        if not module_folder.is_dir:
            continue

        create_module(module_folder, session, existing_modules, existing_lessons)


def main():

    session = edAPI().new(
        f"https://edstem.org/api", Path("api-token").read_text(), class_id="10611"
    )

    create_all_modules(session)
    # lesson: edAPI.lesson = session.lesson(31193).get()
    # create_challenge(Path("output/grok_exercises/Ex10.x1"), session, lesson)


main()
