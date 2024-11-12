import dataclasses
from typing import Any, Dict
import yaml2pyclass
import os
import yaml
from inspect import getmembers


@dataclasses.dataclass
class GrokProblem:
    @staticmethod
    def _to_class_name(key: str) -> str:
        return "".join(x.title() for x in key.split("_")) + "Class"

    @classmethod
    def from_yaml(cls, config_file: str):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Could not find YAML file at {config_file}")
        with open(config_file, "r") as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
            data = {} if data is None else data

        old_fields = list(
            [value for key, value in getmembers(cls) if key == "__dataclass_fields__"][
                0
            ].keys()
        )
        dummy_data = {field: None for field in old_fields}

        c = cls(**dummy_data)
        cls._update_data(c, data)

        return c

    @classmethod
    def _update_data(cls, obj: object, data: Dict[str, Any]) -> object:

        obj.__dict__.clear()
        obj.__dict__.update(data)

        for key, value in data.items():
            if not isinstance(value, dict):
                continue

            subclass = type(cls._to_class_name(key), (), {})
            obj.__dict__[key] = cls._update_data(subclass(), value)

        return obj

    @dataclasses.dataclass
    class ChoicesClass:
        pass

    @dataclasses.dataclass
    class OptionsClass:
        pass

    @dataclasses.dataclass
    class TestsClass:
        @dataclasses.dataclass
        class CommonClass:
            checker: int
            driver: int
            files: list
            validate_behaviour: int

        common: CommonClass
        tests: list

    blockly_blocks: list
    choices: ChoicesClass
    concepts: list
    content: str
    editor: int
    language: int
    notes: str
    options: OptionsClass
    slug: str
    solutions: list
    teacher_notes: str
    tests: TestsClass
    title: str
    updated_at: str
    workspace: list
