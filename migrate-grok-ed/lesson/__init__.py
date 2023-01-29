from datetime import datetime
from typing import List, Any


class Settings:
    quiz_active_status: str
    quiz_mode: str
    quiz_question_number_style: str

    def __init__(self, quiz_active_status: str, quiz_mode: str, quiz_question_number_style: str) -> None:
        self.quiz_active_status = quiz_active_status
        self.quiz_mode = quiz_mode
        self.quiz_question_number_style = quiz_question_number_style

