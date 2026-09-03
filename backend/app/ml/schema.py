"""The training-data contract: what an ML example is allowed to contain.

This is deliberately separate from the candidate-facing interview schemas. Those
carry the interview itself -- questions, answers, evidence, reasoning, all of it
free text derived from a real person's resume and speech. A training example
carries none of that.

Every feature here is either a closed-vocabulary category or a count. There is no
question text, no answer text, no transcript, no concept or claim *names* (a
concept label like "Acme payments migration" is resume content), no identity, and
no audio or video. What survives is the shape of a turn, not its content.

`example_id` is a one-way digest of the interview id and turn number: enough to
deduplicate and to delete a withdrawn interview's examples, not enough to recover
which interview produced a row.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.interview_decision import DifficultyDirection, InterviewerActionType
from app.schemas.question import QuestionDifficulty

SCHEMA_VERSION = "1.0"

#: Marks how an example was produced. Synthetic rows are generated scenarios and
#: must never be presented as observations of a real candidate.
ExampleSource = Literal["synthetic", "consented_interview"]

#: Value the extractor falls back to when a model returns a category outside the
#: documented vocabulary. Recorded explicitly rather than guessed at or dropped.
UNKNOWN_CATEGORY = "other"

# Vocabularies as documented on the interview schemas these features are read
# from. The upstream fields are plain strings (the LLM fills them), so anything
# outside these sets is normalized to UNKNOWN_CATEGORY instead of trusted.
ANALYSIS_CORRECTNESS = ("correct", "partially_correct", "incorrect", "unknown")
ANALYSIS_REASONING = ("strong", "adequate", "weak", "unclear")
ANALYSIS_RELEVANCE = ("high", "medium", "low", "off_topic")
ANALYSIS_DEPTH = ("shallow", "moderate", "deep", "insufficient")
ANALYSIS_COMPLETENESS = ("complete", "partial", "incomplete", "vague")

EVALUATION_CORRECTNESS = ("strong", "moderate", "weak", "partial")
EVALUATION_UNDERSTANDING = ("strong", "moderate", "weak", "limited")
EVALUATION_COMPLETENESS = ("complete", "partial", "incomplete", "vague")
EVALUATION_DEPTH = ("deep", "moderate", "shallow", "limited")
EVALUATION_REASONING = ("strong", "moderate", "weak", "limited")
EVALUATION_RELEVANCE = ("high", "medium", "low", "off_topic")
EVALUATION_APPLICATION = ("strong", "moderate", "limited", "weak")
EVALUATION_CONFIDENCE = ("low", "medium", "high")


def normalize_category(value: str | None, vocabulary: tuple[str, ...]) -> str:
    """Map a free-form category onto a known vocabulary, or to UNKNOWN_CATEGORY."""
    if value is None:
        return UNKNOWN_CATEGORY
    normalized = value.strip().lower().replace(" ", "_").replace("-", "_")
    return normalized if normalized in vocabulary else UNKNOWN_CATEGORY


def build_example_id(interview_id: str, turn_number: int) -> str:
    """Derive a stable, one-way identifier for one interview turn.

    Deterministic so re-exporting the same turn produces the same row, and
    one-way so the dataset cannot be joined back to an interview by anyone
    holding only the dataset.
    """
    digest = hashlib.sha256(f"{interview_id}:{turn_number}".encode("utf-8"))
    return digest.hexdigest()[:32]


class TurnFeatures(BaseModel):
    """Structured, non-identifying signals describing one answered interview turn.

    Counts summarize lists whose contents are free text: how many concepts were
    demonstrated, not which ones.
    """

    model_config = ConfigDict(extra="forbid")

    # --- What was asked -----------------------------------------------------
    question_difficulty: QuestionDifficulty
    question_intent: InterviewerActionType
    evaluation_focus_count: int = Field(..., ge=0)
    turn_number: int = Field(..., ge=1)

    # --- How Answer Intelligence read the answer ----------------------------
    analysis_technical_correctness: str
    analysis_reasoning_quality: str
    analysis_answer_relevance: str
    analysis_technical_depth: str
    analysis_completeness: str
    demonstrated_concept_count: int = Field(..., ge=0)
    missing_concept_count: int = Field(..., ge=0)
    incorrect_concept_count: int = Field(..., ge=0)
    analysis_unsupported_claim_count: int = Field(..., ge=0)

    # --- How the Evaluation Engine scored it --------------------------------
    evaluation_technical_correctness: str
    evaluation_conceptual_understanding: str
    evaluation_completeness: str
    evaluation_technical_depth: str
    evaluation_reasoning_quality: str
    evaluation_relevance: str
    evaluation_application_ability: str
    evaluation_confidence: str
    evidence_count: int = Field(..., ge=0)
    gap_count: int = Field(..., ge=0)
    strength_count: int = Field(..., ge=0)

    # --- Knowledge accumulated across the interview so far ------------------
    concepts_tracked: int = Field(..., ge=0)
    concepts_demonstrated: int = Field(..., ge=0)
    concepts_missing: int = Field(..., ge=0)
    concepts_incorrect: int = Field(..., ge=0)
    claims_supported: int = Field(..., ge=0)
    claims_unsupported: int = Field(..., ge=0)
    claims_uncertain: int = Field(..., ge=0)

    @field_validator(
        "analysis_technical_correctness",
        "analysis_reasoning_quality",
        "analysis_answer_relevance",
        "analysis_technical_depth",
        "analysis_completeness",
        "evaluation_technical_correctness",
        "evaluation_conceptual_understanding",
        "evaluation_completeness",
        "evaluation_technical_depth",
        "evaluation_reasoning_quality",
        "evaluation_relevance",
        "evaluation_application_ability",
        "evaluation_confidence",
    )
    @classmethod
    def _reject_free_text(cls, value: str) -> str:
        """Guard the contract: categories must already have been normalized.

        A raw model string reaching the dataset would be both a leak risk and a
        feature the model cannot use, so it fails here rather than silently
        becoming a one-off category.
        """
        if value != value.strip().lower() or " " in value:
            raise ValueError(f"category {value!r} was not normalized")
        return value


class TrainingExample(BaseModel):
    """One ML-ready row: features, the target, and the labels kept for later work."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    example_id: str = Field(..., min_length=8)
    source: ExampleSource
    features: TurnFeatures

    #: Baseline target -- how the interviewer moved difficulty for the next question.
    label_difficulty_direction: DifficultyDirection
    #: Recorded for future targets; the baseline model does not use these.
    label_action: InterviewerActionType
    label_should_probe_further: bool

    @field_validator("schema_version")
    @classmethod
    def _known_version(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(f"unsupported training schema version {value!r}")
        return value


#: Feature names in a fixed order, so any encoder built from this contract
#: produces the same column layout across runs and processes.
CATEGORICAL_FEATURES: tuple[str, ...] = (
    "question_difficulty",
    "question_intent",
    "analysis_technical_correctness",
    "analysis_reasoning_quality",
    "analysis_answer_relevance",
    "analysis_technical_depth",
    "analysis_completeness",
    "evaluation_technical_correctness",
    "evaluation_conceptual_understanding",
    "evaluation_completeness",
    "evaluation_technical_depth",
    "evaluation_reasoning_quality",
    "evaluation_relevance",
    "evaluation_application_ability",
    "evaluation_confidence",
)

NUMERIC_FEATURES: tuple[str, ...] = (
    "evaluation_focus_count",
    "turn_number",
    "demonstrated_concept_count",
    "missing_concept_count",
    "incorrect_concept_count",
    "analysis_unsupported_claim_count",
    "evidence_count",
    "gap_count",
    "strength_count",
    "concepts_tracked",
    "concepts_demonstrated",
    "concepts_missing",
    "concepts_incorrect",
    "claims_supported",
    "claims_unsupported",
    "claims_uncertain",
)

TARGET_FIELD = "label_difficulty_direction"
