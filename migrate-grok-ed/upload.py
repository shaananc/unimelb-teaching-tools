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

## add logging with rich
from rich.logging import RichHandler
import logging

FORMAT = "%(message)s"
logging.basicConfig(
    level="DEBUG", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

ED_COURSE_ID: str = "10611"  # playground
# ED_COURSE_ID : str = '10507' -- real class

DRY_RUN = False
DRY_RUN_ALLOW_GETS = True


session = requests.Session()


class edAPI:

    token: Optional[str]
    base_url: Optional[str]
    class_id: Optional[str]
    url_suffix: Optional[str]

    def new(self, base_url="", token="", class_id=None, url_suffix=None):
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
        sid: Optional[int]
        Schema: ClassVar[Type[Schema]] = Schema  # type: ignore

        def new(self, base_url="", url_suffix="", token="", sid=None, class_id=None):
            self.base_url = base_url
            self.url_suffix = url_suffix
            self.sid = sid
            self.token = token
            self.class_id = class_id

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
                return {}

            if not hasattr(self, "token") or not self.token:
                log.error("No token set!")
                return {}

            if self.url_suffix and not url_suffix:
                url_suffix = self.url_suffix

            full_url = self.base_url + "/" + url_suffix

            if include_sid:
                if not hasattr(self, "sid") or not self.sid:
                    log.error("No sid set!")
                    return {}
                else:
                    full_url = full_url + "/" + str(self.sid)

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
                    method, full_url, files=files, headers=auth
                ).prepare()
            else:
                request = requests.Request(method, full_url, headers=auth).prepare()

            log.debug(request.__dict__)
            if (DRY_RUN_ALLOW_GETS and method == "GET") or not DRY_RUN:
                response = session.send(request)
                response.raise_for_status()
                log.debug(response.__dict__)
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

            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

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
                self.sid = self.unwrap(response)["id"]
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

        def create(self):
            # fast pluralize hack
            # url_suffix = self.url_suffix
            # if url_suffix and url_suffix[-1] != 's':
            #     url_suffix = url_suffix + 's'

            return self.post(
                json_data=self.json(),
                include_sid=False,
                url_suffix=f"courses/{self.class_id}/{self.url_suffix}",
            )

    class Module(EDAPI_OBJ):
        name: Optional[str | None]

        def new(self, base_url=None, token=None, sid=None, class_id=None):
            super().new(
                base_url=base_url,
                url_suffix=f"lessons/modules",
                token=token,
                sid=sid,
                class_id=class_id,
            )
            self.name: str | None = None
            return self

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

        def save(self):
            return self.put(data=self.dump())

        def put(self, data):
            data = json.loads(self.json_str())
            data.pop("created_at")
            data.pop("updated_at")
            data.pop("original_id")

            data = dict(slide=json.dumps(data))

            log.debug(data)

            return super().put(data=data)

        def new(self, base_url=None, token=None, sid=None, class_id=None):
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
            return self

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
            obj.sid = self.challenge_id
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
        slides: Optional[List[lesson.SlideDataClass] | None] = None

        def new(
            self, base_url=None, token=None, sid=None, url_suffix=None, class_id=None
        ):
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
            self.id: Optional[int | None] = None
            self.slides: Optional[List[lesson.SlideDataClass] | None] = None

            return self

        def get_all(self):
            return self.api_request(
                "GET", url_suffix=f"courses/{self.class_id}/lessons", include_sid=False
            )

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

        def new(self, base_url=None, token=None, sid=None, class_id=None):
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
            self.id: int | None = None
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
            self.patch(json_data=self.json_str())
            base_suffix = self.url_suffix + "/" + str(self.sid) + "/connect/"
            urls = [
                base_suffix + a for a in ["scaffold", "solution", "testbase", "check"]
            ]
            for url in urls:
                log.debug(f"Posting {url}")
                self.api_request("POST", url_suffix=url, include_sid=False)

            base_suffix = self.url_suffix + "/" + str(self.sid) + "/update/"
            urls = [
                base_suffix + a for a in ["scaffold", "solution", "testbase", "check"]
            ]
            for url in urls:
                log.debug(f"Posting {url}")
                self.api_request("POST", url_suffix=url, include_sid=False)

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
        return self.Slide().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )

    def lesson(self, sid=None):
        return self.Lesson().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )

    def module(self, sid=None):
        return self.Module().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )

    def challenge(self, sid=None):
        return self.Challenge().new(
            base_url=self.base_url, token=self.token, sid=sid, class_id=self.class_id
        )


def create_challenge(folder: Path, session: edAPI, slide: edAPI.Slide):
    # set content to the contents of content.amber
    content = (folder / "content.xml").read_text()
    # set solution_text to the contents of solution_notes.amber
    solution_text = (folder / "solution_notes.xml").read_text()

    # read in problem.yaml
    # problem = None
    problem_yaml_path = folder / "problem.yaml"
    grok_problem = GrokProblem.from_yaml(str(problem_yaml_path))

    # create a new slide object
    # slide = session.slide('217582').get()
    # challenge = slide.get_challenge()
    # challenge = session.challenge('75698').get()
    # log.debug(challenge)

    mychallenge = slide.get_challenge()

    slide.title = grok_problem.title  # type: ignore
    slide.content = content

    grok_ed_map = (
        ("workspace", "scaffold"),
        ("solutions", "solution"),
        ("tests", "check"),
        ("tests", "testbase"),
    )
    makefile = folder / "workspace" / "Makefile"
    for grok_folder, ed_folder in grok_ed_map:
        log.info(f"Uploading {grok_folder} to {ed_folder}")
        for wfile in (folder / grok_folder).glob("*"):
            if not wfile.name.endswith(".yaml"):
                url = f"challenge.{mychallenge.sid}.{ed_folder}@git.edstem.org:"
                log.info(f"Uploading {wfile} to {url}")
                if not DRY_RUN:
                    subprocess.run(
                        [
                            "rsync",
                            "-r",
                            "--exclude",
                            "*.yaml",
                            str(wfile.absolute()),
                            url,
                        ]
                    )
                    subprocess.run(["rsync", str(makefile.absolute()), url])

    # set the content to the contents of content.amber
    # challenge.content = content
    # set the explanation to the contents of solution_notes.amber
    # challenge.explanation = solution_text
    # log.debug(grok_problem.title)
    # log.debug(content)
    mychallenge.settings.build_command = "make all"  # type: ignore
    mychallenge.settings.run_command = "make run"  # type: ignore
    mychallenge.settings.check_command = "make run"  # type: ignore
    mychallenge.tickets.run_standard.build_command = "make all"  # type: ignore
    mychallenge.tickets.run_standard.run_command = "make run"  # type: ignore

    mychallenge.tickets.mark_standard.easy = False  # penalize whitespace infractions
    mychallenge.tickets.mark_standard.run_limit.pty = False  # make the output match up with the terminal output without having to interleave

    testcases: List[challenge.Testcase] = []
    for f in (folder / "tests").rglob("*.yaml"):
        grok_test = GrokTest.from_yaml(str(f))
        log.info(f)
        relative_dir = f.relative_to(folder / "tests").parent
        # log.info(grok_test.__dict__)
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
        testcase.stdin_path = str(relative_dir / "stdin")
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
            log.error(f"Neither stdout or stdio exist for {grok_test.label}")
            sys.exit(1)
        check.type = "check_diff"
        check.source = challenge.Source("source_mixed", "")
        testcase.checks = [check]
        testcases.append(testcase)

    mychallenge.tickets.mark_standard.testcases = testcases
    mychallenge.save()


def create_slides_and_challenges(slide_folder: Path, session: edAPI, lesson: edAPI.Lesson):
    i = 0
    while True:
        ref_path = Path(slide_folder / f"{i}.ref")
        html_path = Path(slide_folder / f"{i}.html")
        if ref_path.exists():
            # create challenge
            ref = ref_path.read_text()
        elif html_path.exists():
            # create slide
            content = html_path.read_text()
            slide = session.slide()
        else:
            break


def create_lesson(
    lesson_folder: Path,
    session: edAPI,
    module: edAPI.Module,
    existing_lessons: Dict[str, int],
):
    # check if a lesson of that name already exists under that module
    lesson: edAPI.Lesson | None = None
    if lesson_folder.name in existing_lessons:
        lesson = session.lesson(existing_lessons[lesson_folder.name]).get()
        if lesson.module_id != module.sid:
            log.warning(
                f"Lesson {lesson_folder.name} already exists under a different module, creating new lesson"
            )
            lesson = session.lesson()
            lesson.title = lesson_folder.name
            lesson.module_id = module.sid
            lesson.type = "c"
            lesson.create()
            lesson.save()

        else:
            log.debug(f"Lesson {lesson_folder.name} already exists under this module")
    else:
        lesson = session.lesson()
        lesson.title = lesson_folder.name
        lesson.module_id = module.sid
        lesson.type = "c"
        lesson.create()
        lesson.save()

    # create slides and challenges
    create_slides_and_challenges(lesson_folder, session, lesson)


def main():

    session = edAPI().new(
        f"https://edstem.org/api", Path("api-token").read_text(), class_id="10611"
    )

    lessons_and_modules = session.lesson().get_all()
    existing_lessons = lessons_and_modules["lessons"]
    existing_modules = lessons_and_modules["modules"]
    existing_lessons = {lesson["title"]: lesson["id"] for lesson in existing_lessons}
    log.info(existing_modules)
    existing_modules = {module["name"]: module["id"] for module in existing_modules}
    log.info(existing_modules)

    # for every folder in output/grok_exercises
    for module_folder in Path("output/modules").iterdir():
        if not module_folder.is_dir:
            continue

        # create a new lesson
        module = session.module()

        module_json_file = list(module_folder.glob("*.json"))

        if len(module_json_file) == 0:
            log.info(f"Found no json files in {module_folder}")
            continue

        if len(module_json_file) != 1:
            log.error(f"Found {len(module_json_file)} json files in {module_folder}")
            sys.exit(1)
        module_json_file = module_json_file[0]
        module_json = json.loads(module_json_file.read_text())

        module.name = module_json["title"]
        if module.name in existing_modules:
            log.info(f"Module {module.name} already exists, skipping")
            module = session.module(existing_modules[module.name])
        else:
            log.info(f"Creating module {module.name}")
            module.create()

        # for each lesson folder in the module folder
        for lesson_folder in module_folder.iterdir():
            if not lesson_folder.is_dir():
                continue
            log.debug(f"Creating lesson {lesson_folder.name}")
            create_lesson(
                lesson_folder, session, module, existing_lessons=existing_lessons
            )
            break

        break

        # slide.save()

        # log.debug(solution_text)
        # log.info(mychallenge.json())

        break


main()
