import dataclasses
from types import NoneType
import yaml2pyclass


class GrokTest(yaml2pyclass.CodeGenerator):
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
