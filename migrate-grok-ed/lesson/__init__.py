from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Any, Optional


class Settings:
    quiz_active_status: str
    quiz_mode: str
    quiz_question_number_style: str

    def __init__(
        self, quiz_active_status: str, quiz_mode: str, quiz_question_number_style: str
    ) -> None:
        self.quiz_active_status = quiz_active_status
        self.quiz_mode = quiz_mode
        self.quiz_question_number_style = quiz_question_number_style


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
