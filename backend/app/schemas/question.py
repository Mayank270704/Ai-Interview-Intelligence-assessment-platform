"""Question schemas."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.interview_decision import InterviewerActionType

QuestionDifficulty = Literal["easy", "medium", "hard"]


class GeneratedQuestion(BaseModel):
    """Interview question generated from an InterviewDecision."""

    question: str = Field(
        ..., min_length=1, description="The interview question to ask the candidate"
    )
    target_concept: str = Field(
        ..., min_length=1, description="The concept or topic the question investigates"
    )
    difficulty: QuestionDifficulty = Field(
        ..., description="Difficulty level the question was generated for"
    )
    intent: InterviewerActionType = Field(
        ..., description="The interview action this question implements"
    )
    evaluation_focus: list[str] = Field(
        default_factory=list,
        description="Concepts or evidence the candidate's answer should be evaluated against",
    )
