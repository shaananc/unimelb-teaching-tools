import dataclasses
from types import NoneType
import yaml2pyclass


class GrokTest(yaml2pyclass.CodeGenerator):
  @dataclasses.dataclass
  class OptionsClass:
    floats: int
    image_ordering_mode: str
    punctuation: bool
    slice_end: int
    slice_start: int
    whitespace: bool
  
  label: str
  onerror: str
  onfail: str
  onpass: str
  options: OptionsClass
  type: int
  weight: NoneType
