from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import List, Any, Optional, Dict
from datetime import datetime
import json

temp_annotation = Any  # temp_annotation


@dataclass
class Passback:
    max_automatic_score: int
    scoring_mode: str
    scale_to: Optional[int]

    def __init__(
        self, max_automatic_score: int, scoring_mode: str, scale_to: Optional[int]
    ) -> None:
        self.max_automatic_score = max_automatic_score
        self.scoring_mode = scoring_mode
        self.scale_to = scale_to

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(asdict(self))


@dataclass
class Points:
    loss_amount: Optional[int]
    loss_every: Optional[int]
    loss_threshold: Optional[int]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


@dataclass
class Settings:
    build_command: Optional[str]
    check_command: Optional[str]
    chrome: Optional[str]
    criteria: Optional[List[str]]
    max_mark: Optional[str]
    max_submissions_with_intermediate_files: Optional[int]
    only_git_submission: Optional[bool]
    passback: Optional[Passback]
    per_testcase_scores: Optional[bool]
    playground: Optional[bool]
    points: Optional[Points]
    run_command: Optional[str]
    services: Optional[List[str]]
    terminal_command: Optional[str]
    allow_submit_after_marking_limit: Optional[bool]
    attempt_limit_interval: Optional[int]
    max_submissions_per_interval: Optional[int]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


class PtySize:
    cols: Optional[int]
    rows: Optional[int]


class BoxLimitClass:
    autospawn_vnc: Optional[bool]
    image: Optional[str]
    internet: Optional[bool]
    kvm: Optional[bool]
    networking: Optional[bool]
    pty_size: Optional[PtySize]
    vnc_height: Optional[int]
    vnc_width: Optional[int]


class Course:
    course_id: Optional[int]
    course_name: Optional[str]
    self_serve_course_files: Optional[bool]


class User:
    id: Optional[int]
    name: Optional[str]


class Workspace:
    hash: Optional[str]
    wid: Optional[str]


class WorkspaceSettings:
    rstudio_layout: Optional[str]


@dataclass
class Connect:
    box_limit: Optional[BoxLimitClass]
    course: Optional[Course]
    empty: Optional[bool]
    course: Optional[Course]
    connect_from: Optional[str]
    inactivity_timeout: Optional[int]
    no_quota: Optional[bool]
    preset: Optional[str]
    readonly: Optional[bool]
    region: Optional[str]
    services: Optional[List[str]]
    staff_tag: Optional[bool]
    temporary: Optional[bool]
    terminal: Optional[bool]
    user: Optional[User]
    web: Optional[bool]
    web_id: Optional[str]
    workspace: Optional[Workspace]
    workspace_settings: Optional[WorkspaceSettings]
    from_: Optional[str]
    lesson_id: Optional[int]
    challenge: Optional[temp_annotation]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


@dataclass
class BoxLimit:
    autospawn_vnc: Optional[bool]
    cpu_time: Optional[int]
    image: Optional[str]
    internet: Optional[bool]
    kvm: Optional[bool]
    networking: Optional[bool]
    preset: Optional[str]
    pty_size: Optional[PtySize]
    vnc_height: Optional[int]
    vnc_width: Optional[int]
    wall_time: Optional[int]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


@dataclass
class BuildLimitClass:
    pty_size: Optional[PtySize]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


@dataclass
class MarkCustomRunLimit:
    pty: Optional[bool]
    pty_size: Optional[PtySize]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)


@dataclass
class Source:
    type: Optional[str]
    file: Optional[str]


@dataclass
class Check:
    acceptable_line_errors: Optional[int]
    expect_path: Optional[str]
    source: Optional[Source]
    type: Optional[str]
    file: Optional[str]
    run_command: Optional[str]
    name: Optional[str]
    acceptable_char_errors: Optional[int]
    regex_match: Optional[str]
    markdown: Optional[bool]
    acceptable_line_error_rate: Optional[int]
    transforms: Optional[List[str]]
    acceptable_char_error_rate: Optional[int]
    run_limit: Optional[MarkCustomRunLimit]
    source: Optional[Source]


class TestcaseRunLimit:
    cpu_time: Optional[int]
    wall_time: Optional[int]
    pty_size: Optional[PtySize]


@dataclass
class Testcase:
    checks: Optional[List[Check]]
    hidden: Optional[bool]
    name: Optional[str]
    output_files: Optional[List[str]]
    run_command: Optional[str]
    run_limit: Optional[TestcaseRunLimit]
    skip: Optional[bool]
    stdin_path: Optional[str]
    description: Optional[str]
    private: Optional[bool]
    max_score: Optional[int]
    score: Optional[int]
    extra_paths: Optional[List[str]]


@dataclass
class Mark:
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimit]
    build_command: Optional[str]
    build_limit: Optional[BuildLimitClass]
    course: Optional[Course]
    files_limit: Optional[BoxLimitClass]
    mark: Optional[Workspace]
    no_quota: Optional[bool]
    preset: Optional[str]
    prev_staff_files: Optional[Workspace]
    prev_student_files: Optional[Workspace]
    region: Optional[str]
    run_command: Optional[str]
    run_limit: Optional[MarkCustomRunLimit]
    services: Optional[List[str]]
    solution: Optional[Workspace]
    staff_files: Optional[Workspace]
    staff_tag: Optional[bool]
    student_files: Optional[Workspace]
    user: Optional[User]
    easy: Optional[Optional[bool]]
    mark_all: Optional[Optional[bool]]
    overlay: Optional[Optional[bool]]
    testcases: Optional[List[Testcase]]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class MarkJupyter:
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimitClass]
    build_command: Optional[str]
    build_limit: Optional[BuildLimitClass]
    course: Optional[Course]
    jupyter_notebook_path: Optional[str]
    mark: Optional[Workspace]
    no_quota: Optional[bool]
    preset: Optional[str]
    region: Optional[str]
    run_limit: Optional[BuildLimitClass]
    services: Optional[List[str]]
    solution: Optional[Workspace]
    staff_tag: Optional[bool]
    testcase_path: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class MarkPostgres:
    attempt: Optional[Workspace]
    attempt_path: Optional[str]
    box_limit: Optional[BoxLimit]
    check_database: Optional[bool]
    check_select: Optional[bool]
    course: Optional[Course]
    ignore_column_names: Optional[bool]
    ignore_column_order: Optional[bool]
    ignore_row_order: Optional[bool]
    mark: Optional[Workspace]
    mark_all: Optional[bool]
    no_quota: Optional[bool]
    preset: Optional[str]
    region: Optional[str]
    server_box_limit: Optional[BoxLimitClass]
    solution: Optional[Workspace]
    solution_path: Optional[str]
    staff_tag: Optional[bool]
    testcases: Optional[List[str]]
    type: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class MarkUnit:
    additional_classpath: Optional[str]
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimit]
    build_command: Optional[str]
    build_limit: Optional[BuildLimitClass]
    course: Optional[Course]
    mark: Optional[Workspace]
    no_quota: Optional[bool]
    preset: Optional[str]
    region: Optional[str]
    run_limit: Optional[MarkCustomRunLimit]
    services: Optional[List[str]]
    solution: Optional[Workspace]
    staff_tag: Optional[bool]
    testcase_path: Optional[str]
    type: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class MarkWeb:
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimitClass]
    course: Optional[Course]
    main_html_path: Optional[str]
    main_js_path: Optional[str]
    mark: Optional[Workspace]
    no_quota: Optional[bool]
    preload_js_path: Optional[List[str]]
    preset: Optional[str]
    region: Optional[str]
    screen_height: Optional[int]
    screen_width: Optional[int]
    solution: Optional[Workspace]
    staff_tag: Optional[bool]
    testcases: Optional[List[str]]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


@dataclass
class Run:
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimit]
    build_command: Optional[str]
    build_limit: Optional[BuildLimitClass]
    course: Optional[Course]
    dump_files: Optional[bool]
    extra_paths: Optional[List[str]]
    no_quota: Optional[bool]
    overlay: Optional[bool]
    preset: Optional[str]
    process_file_events: Optional[bool]
    region: Optional[str]
    run: Optional[Workspace]
    run_command: Optional[str]
    run_limit: Optional[BuildLimitClass]
    services: Optional[List[str]]
    staff_tag: Optional[bool]
    test_command: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class RunPostgres:
    attempt: Optional[Workspace]
    attempt_path: Optional[str]
    box_limit: Optional[BoxLimit]
    course: Optional[Course]
    no_quota: Optional[bool]
    preset: Optional[str]
    psql: Optional[bool]
    region: Optional[str]
    run: Optional[Workspace]
    schema_path: Optional[str]
    server_box_limit: Optional[BoxLimitClass]
    staff_tag: Optional[bool]
    type: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


class RunStandard:
    attempt: Optional[Workspace]
    box_limit: Optional[BoxLimit]
    build_command: Optional[str]
    build_limit: Optional[BuildLimitClass]
    course: Optional[Course]
    dump_files: Optional[bool]
    extra_paths: Optional[List[str]]
    no_quota: Optional[bool]
    overlay: Optional[bool]
    preset: Optional[str]
    process_file_events: Optional[bool]
    region: Optional[str]
    run: Optional[Workspace]
    run_command: Optional[str]
    run_limit: Optional[MarkCustomRunLimit]
    services: Optional[List[str]]
    staff_tag: Optional[bool]
    test_command: Optional[str]
    user: Optional[User]
    challenge: Optional[temp_annotation]
    lesson_id: Optional[int]
    lesson_slide_id: Optional[int]
    source: Optional[str]


@dataclass
class Tickets:
    connect: Optional[Connect]
    mark_custom: Optional[Mark]
    mark_jupyter: Optional[MarkJupyter]
    mark_postgres: Optional[MarkPostgres]
    mark_standard: Optional[Mark]
    mark_unit: Optional[MarkUnit]
    mark_web: Optional[MarkWeb]
    run_custom: Optional[Run]
    run_postgres: Optional[RunPostgres]
    run_standard: Optional[RunStandard]
    run_unit: Optional[Run]
    lesson_id: Optional[int]
    from_secondary: Optional[bool]
    source: Optional[str]
    challenge: Optional[temp_annotation]
    lesson_slide_id: Optional[int]

    def to_json(self):
        # Serialize by converting to a dictionary and handling nested structures
        return json.dumps(asdict(self))

    def to_dict(self):
        # Serialize by converting to a dictionary and handling nested structures
        return asdict(self)
