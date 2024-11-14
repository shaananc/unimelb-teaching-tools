from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SlideDataClass:
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
    active_status: Optional[str | None]
    is_survey: Optional[bool | None]
    passage: Optional[str | None]
    mode: Optional[str | None]
    rubric_points: Optional[int | None]
    lesson_markable_id: Optional[int | None]
    auto_points: Optional[int | None]
    rubric_id: Optional[int | None]


@dataclass
class SlideSummaryDataClass:
    id: Optional[int | None]
    is_hidden: Optional[bool | None]
    rubric_points: Optional[int | None]
    auto_points: Optional[int | None]
    scoring_mode: Optional[str | None]
    scale_to: Optional[int | None]
    scale_to_auto: Optional[int | None]
    scale_to_rubric: Optional[int | None]
