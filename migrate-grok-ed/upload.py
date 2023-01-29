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
from pydantic import BaseModel
from pprint import pprint

## add logging with rich
from rich.logging import RichHandler
import logging
FORMAT = "%(message)s"
logging.basicConfig(
    level="DEBUG", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")

ED_COURSE_ID : str = '10611' # playground
# ED_COURSE_ID : str = '10507' -- real class

DRY_RUN = False
DRY_RUN_ALLOW_GETS = True


session = requests.Session()

class edAPI:

    token: Optional[str]
    base_url: Optional[str]

    def new(self, base_url, token):
        self.token = token
        self.base_url = base_url
        return self
  
    # create a new class for api requests that requires the server side id of the object to be modified
    class EDAPI_OBJ():
        token: Optional[str]
        base_url: Optional[str]
        url_suffix: Optional[str]
        sid: Optional[int]
        Schema: ClassVar[Type[Schema]] = Schema # type: ignore

        def new(self, base_url, url_suffix, token, sid=None):
            self.base_url = base_url
            self.url_suffix = url_suffix
            self.sid = sid
            self.token = token

        def api_request(self, method, data=None, json_data=None, files=None, url_suffix='', include_sid=True):
            if not hasattr(self, 'base_url') or not self.base_url:
                log.error("No base_url set!")
                return {}

            if not hasattr(self, 'token') or not self.token:
                log.error("No token set!")
                return {}

            if self.url_suffix and not url_suffix:
                url_suffix = self.url_suffix


            full_url = self.base_url + '/' + url_suffix

            if include_sid:
                if (not hasattr(self, 'sid') or not self.sid):
                    log.error("No sid set!")    
                    return {}   
                else:
                    full_url = full_url + '/' + str(self.sid)

            auth = {'Authorization': 'Bearer ' + self.token}

            # if data: # todo add more checks here
            #     data.pop('sid')
            #     data.pop('url_suffix')
            #     data.pop('base_url')
            #     data.pop('token')
                
            request = None
            
            if data and json_data:
                raise Exception("Cannot have both data and json_data")
            


            if data:
                request = requests.Request(method, full_url, data=data, headers=auth).prepare()
            elif json_data:
                request = requests.Request(method, full_url, json=json_data, headers=auth).prepare()
            elif files:
                request = requests.Request(method, full_url, files=files, headers=auth).prepare()
            else:
                request = requests.Request(method, full_url, headers=auth).prepare()

            log.debug(request.__dict__)
            if (DRY_RUN_ALLOW_GETS and method == 'GET') or not DRY_RUN:
                response = session.send(request)
                response.raise_for_status()
                return response.json()
            else:
                return {}

        def get_internal(self) -> Mapping[str, Any]:
            return self.api_request('GET')

        def get(self):
            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()
            data = self.get_internal()
            class_name = self.__class__.__name__
            data = data[class_name.lower()]
            log.debug(data)

            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

        def wrap(self, data):
            class_name = self.__class__.__name__
            return {class_name.lower(): data}

        def put(self, data=None, json_data=None, files=None):
            if json_data:
                json_data = self.wrap(json_data)
            return self.api_request('PUT', data=data, json_data=json_data, files=files)

        def delete(self):
            return self.api_request('DELETE')

        def patch(self, data=None, json_data=None):
            if json_data:
                json_data = self.wrap(json_data)
            return self.api_request('PATCH', data=data, json_data=json_data)

        def post(self, data=None, json_data=None):
            if json_data:
                json_data = self.wrap(json_data)
            request = self.api_request('POST', data=data, json_data=json_data)
            if request:
                self.sid = request['id']
            return request

        def dump(self):
            return marshmallow_dataclass.class_schema(self.__class__)().dump(self)

        def json_str(self):
            return marshmallow_dataclass.class_schema(self.__class__)().dumps(self)

        def json(self):
            return json.loads(self.json_str())

        def __str__(self):
            return str(self.json_str())

        def create(self):
            return self.post(self)

    class Module(EDAPI_OBJ):
        def new(self, base_url=None, token=None, sid=None):
            super().new(base_url,'modules', token, sid)
            self.name: str | None = None
            return self


    class Slide(EDAPI_OBJ):
        original_id: Optional[int | None]
        lesson_id: Optional[int | None ]
        user_id: Optional[int | None ]
        course_id: Optional[int | None ]
        type: Optional[str | None ]
        title: Optional[str | None ]
        points: Optional[int | None ]
        index: Optional[int | None ]
        is_hidden: Optional[bool | None ]
        status: Optional[str | None ]
        correct: Optional[bool | None ]
        response: Optional[str | None ]
        created_at: Optional[datetime | None ]
        updated_at: Optional[datetime | None ]
        challenge_id: Optional[int | None ]
        content: Optional[str | None ]
        id: Optional[int | None]
        index: Optional[int | None]
        type: Optional[str | None]
        status: Optional[str | None]


        def save(self):
            return self.put(data=self.dump())



        def put(self, data):
            data = json.loads(self.json_str())
            data.pop('created_at')
            data.pop('updated_at')
            data.pop('original_id')

            data = dict(slide=json.dumps(data))

            log.debug(data)

            return super().put(data=data)


        def new(self, base_url=None, token=None, sid=None):
            super().new(base_url,'lessons/slides', token, sid)
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
            challenge = edAPI.Challenge(None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None).new(self.base_url, self.token, self.challenge_id)# type: ignore
            data = challenge.get_internal()
            class_name = edAPI.Challenge.__name__
            data = data[class_name.lower()]
            if 'tickets' in data and 'connect' in data['tickets']:
                for ticket in data['tickets']['connect']:
                    if 'from' in ticket:
                        bak = data['tickets']['connect']['from']
                        del data['tickets']['connect']['from']
                        data['tickets']['connect']['from_'] = bak
                        break

            obj: edAPI.Challenge = schema.load(data) # type: ignore
            obj.base_url = self.base_url
            obj.token = self.token
            obj.sid = self.challenge_id
            obj.url_suffix = 'challenges'

            return obj


    class Lesson(EDAPI_OBJ):
        def new(self, base_url=None, token=None, sid=None):
            super().new({base_url},"lessons", token, sid)
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
            return self

    class Challenge(EDAPI_OBJ):
        check_hash: Optional[ str | None ]
        content: Optional[ str | None ]
        course_id: Optional[ int | None ]
        created_at: Optional[ datetime | None ]
        category: Optional[ str | None ]
        difficulty: Optional[ str | None ]
        due_at: Optional[ datetime | None ]
        exam_visibility: Optional[ str | None ]
        exam_visibility_alternate_hour: Optional[ bool | None ]
        explanation: Optional[ str | None ]
        features: Optional[Dict[str,  bool] | None ]
        id: Optional[ int | None ]
        is_active: Optional[ bool | None ]
        is_exam: Optional[ bool | None ]
        is_feedback_visible: Optional[ bool | None ]
        is_hidden: Optional[ bool | None ]
        kind: Optional[ str | None ]
        lab_category: Optional[ str | None ]
        lab_name_regex: Optional[ str | None ]
        lab_reset: Optional[ bool | None ]
        language: Optional[ str | None ]
        manual_solution_control: Optional[ bool | None ]
        outline: Optional[ str | None ]
        password: Optional[ str | None ]
        points: Optional[ int | None ]
        requires_lti_link: Optional[ bool | None ]
        scaffold_hash: Optional[ str | None ]
        score: Optional[ int | None ]
        sequential_completion: Optional[ bool | None ]
        session: Optional[ str | None ]
        settings: Optional[ challenge.Settings | None ]
        solution_hash: Optional[ str | None ]
        status: Optional[ str | None ]
        testbase_hash: Optional[ str | None ]
        tickets: Optional[ challenge.Tickets | None ]
        tutorial_regex: Optional[ str | None ]
        type: Optional[ str | None ]
        unavailable_after_completion: Optional[ bool | None ]
        updated_at: Optional[ datetime | None ]
        title: Optional[ str | None ]
        number: Optional[ int | None ]
        original_id: Optional[ int | None ]

        def json_str(self):
            tmp = super().dump()
            bak = tmp['tickets']['connect']['from_'] # type: ignore
            tmp['tickets']['connect'].pop('from_') # type: ignore
            tmp['tickets']['connect']['from'] = bak # type: ignore
            return json.dumps(tmp)

        def get(self):
            class_name = self.__class__
            schema = marshmallow_dataclass.class_schema(class_name)()
            data = self.get_internal()
            class_name = self.__class__.__name__
            data = data[class_name.lower()]

            if 'tickets' in data and 'connect' in data['tickets']:
                for ticket in data['tickets']['connect']:
                    if 'from' in ticket:
                        bak = data['tickets']['connect']['from']
                        del data['tickets']['connect']['from']
                        data['tickets']['connect']['from_'] = bak
                        break

            obj = schema.load(data)
            self.__dict__.update(obj.__dict__)
            return self

        def new(self, base_url=None, token=None, sid=None):
            super().new(base_url,'challenges', token, sid)
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
            base_suffix = self.url_suffix + '/'  + str(self.sid) + '/connect/'
            urls = [base_suffix + a for a in ['scaffold', 'solution', 'testbase', 'check']]
            data = {'i': '', 'password':'', 'user_id':''}
            for url in urls:
                log.debug(f"Posting {url}")
                self.api_request('POST', url_suffix=url,include_sid=False)


        def patch(self, json_data):
            data = json.loads(self.json_str())
            data.pop('check_hash')
            data.pop('scaffold_hash')
            data.pop('solution_hash')
            data.pop('testbase_hash')
            data.pop('created_at')
            data.pop('updated_at')
            data.pop('score')
            data.pop('status')


            return super().patch(json_data=data)
    
    def slide(self,sid=None):
        return self.Slide().new(self.base_url, self.token, sid)


    
    def lesson(self,sid=None):
        return self.Lesson().new(self.base_url, self.token, sid)

    
    def module(self,sid=None):
        return self.Module().new(self.base_url, self.token, sid)

    
    def challenge(self,sid=None):
        return self.Challenge().new(self.base_url,self.token, sid)


def main():

    session = edAPI().new(f'https://edstem.org/api',Path('api-token').read_text())
    # for every folder in output/grok_exercises
    for folder in Path('output/grok_exercises').iterdir():
        if not folder.is_dir:
            continue
        # set content to the contents of content.amber
        content = (folder / 'content.xml').read_text()
        # set solution_text to the contents of solution_notes.amber
        solution_text = (folder / 'solution_notes.amber').read_text()

        # read in problem.yaml
        #problem = None
        problem_yaml_path = folder / 'problem.yaml'
        grok_problem = GrokProblem.from_yaml(str(problem_yaml_path))
        
        # create a new slide object
        #slide = session.slide('217582').get()
        #challenge = slide.get_challenge()
        #challenge = session.challenge('75698').get()
        #log.debug(challenge)

        slide = session.slide('217582').get()
        challenge = slide.get_challenge()

        slide.title = grok_problem.title # type: ignore
        slide.content = content

        # set the content to the contents of content.amber
        #challenge.content = content
        # set the explanation to the contents of solution_notes.amber
        #challenge.explanation = solution_text
        #log.debug(grok_problem.title)
        #log.debug(content)

        #challenge.save()
        slide.save()

        log.debug(solution_text)
        #log.debug(challenge.json())


        break


main()

