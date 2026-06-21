from pydantic import BaseModel, Field
from typing import Optional


class SessionResponse(BaseModel):
    session_id: str
    state: str


class QuestionOut(BaseModel):
    id: str
    question_number: int
    question_text: str
    difficulty_rationale: str


class AnswerIn(BaseModel):
    question_id: str
    user_answer: str = Field(min_length=1)


class AnswersSubmission(BaseModel):
    answers: list[AnswerIn] = Field(min_length=5, max_length=5)


class RetryResponse(BaseModel):
    session_id: str
    reset_to_state: str
    retry_count: int
