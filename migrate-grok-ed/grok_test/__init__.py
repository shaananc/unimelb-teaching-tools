import dataclasses
from inspect import getmembers
from types import NoneType
from typing import Any, Dict
import yaml2pyclass
import yaml
import os


@dataclasses.dataclass
class GrokTest:
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
    class OptionsClass:
        image_ordering_mode: str

    label: str
    onerror: str
    onfail: str
    onpass: str
    options: OptionsClass
    type: int
    weight: NoneType
