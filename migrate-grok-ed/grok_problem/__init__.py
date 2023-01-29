import dataclasses
import yaml2pyclass


class GrokProblem(yaml2pyclass.CodeGenerator):
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
