"""Deterministic encoding of training examples into a numeric feature matrix.

Kept free of any ML dependency on purpose: the column layout is part of the data
contract, so it has to be reproducible and testable wherever the contract is,
not only where scikit-learn happens to be installed.

Two normalizations happen here:

* categorical features become fixed-width one-hot blocks over a closed
  vocabulary, so a value the model has never seen cannot silently add a column;
* counts are clipped to a documented ceiling and scaled to [0, 1], so one
  unusually long answer cannot dominate a distance- or gradient-based model.

Column order is derived from the feature tuples in app.ml.schema and never from
dictionary iteration, so two processes encode identically.
"""

from __future__ import annotations

from app.ml.schema import (
    ANALYSIS_COMPLETENESS,
    ANALYSIS_CORRECTNESS,
    ANALYSIS_DEPTH,
    ANALYSIS_REASONING,
    ANALYSIS_RELEVANCE,
    CATEGORICAL_FEATURES,
    EVALUATION_APPLICATION,
    EVALUATION_COMPLETENESS,
    EVALUATION_CONFIDENCE,
    EVALUATION_CORRECTNESS,
    EVALUATION_DEPTH,
    EVALUATION_REASONING,
    EVALUATION_RELEVANCE,
    EVALUATION_UNDERSTANDING,
    NUMERIC_FEATURES,
    UNKNOWN_CATEGORY,
    TrainingExample,
)

_QUESTION_DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")
_QUESTION_INTENTS: tuple[str, ...] = (
    "DEEPEN",
    "CLARIFY",
    "CHALLENGE",
    "INCREASE_DIFFICULTY",
    "DECREASE_DIFFICULTY",
    "INVESTIGATE_CLAIM",
    "EXPLORE_RELATED_CONCEPT",
    "CHANGE_TOPIC",
    "CONCLUDE_TOPIC",
)

#: Allowed values per categorical feature. UNKNOWN_CATEGORY is appended to every
#: vocabulary so an out-of-vocabulary value lands in a real column instead of
#: vanishing into an all-zero row that looks like missing data.
FEATURE_VOCABULARIES: dict[str, tuple[str, ...]] = {
    "question_difficulty": _QUESTION_DIFFICULTIES,
    "question_intent": _QUESTION_INTENTS,
    "analysis_technical_correctness": ANALYSIS_CORRECTNESS,
    "analysis_reasoning_quality": ANALYSIS_REASONING,
    "analysis_answer_relevance": ANALYSIS_RELEVANCE,
    "analysis_technical_depth": ANALYSIS_DEPTH,
    "analysis_completeness": ANALYSIS_COMPLETENESS,
    "evaluation_technical_correctness": EVALUATION_CORRECTNESS,
    "evaluation_conceptual_understanding": EVALUATION_UNDERSTANDING,
    "evaluation_completeness": EVALUATION_COMPLETENESS,
    "evaluation_technical_depth": EVALUATION_DEPTH,
    "evaluation_reasoning_quality": EVALUATION_REASONING,
    "evaluation_relevance": EVALUATION_RELEVANCE,
    "evaluation_application_ability": EVALUATION_APPLICATION,
    "evaluation_confidence": EVALUATION_CONFIDENCE,
}

#: Ceiling each count is clipped to before scaling into [0, 1]. Chosen from what
#: the interview pipeline plausibly produces; values above a ceiling carry no
#: extra signal for this target and would only stretch the scale.
NUMERIC_CEILINGS: dict[str, int] = {
    "evaluation_focus_count": 6,
    "turn_number": 15,
    "demonstrated_concept_count": 8,
    "missing_concept_count": 8,
    "incorrect_concept_count": 6,
    "analysis_unsupported_claim_count": 6,
    "evidence_count": 10,
    "gap_count": 8,
    "strength_count": 8,
    "concepts_tracked": 40,
    "concepts_demonstrated": 30,
    "concepts_missing": 30,
    "concepts_incorrect": 20,
    "claims_supported": 10,
    "claims_unsupported": 10,
    "claims_uncertain": 10,
}


def _vocabulary(feature: str) -> tuple[str, ...]:
    return (*FEATURE_VOCABULARIES[feature], UNKNOWN_CATEGORY)


def feature_names() -> list[str]:
    """Every column the encoder produces, in the order it produces them."""
    names: list[str] = []
    for feature in CATEGORICAL_FEATURES:
        names.extend(f"{feature}={value}" for value in _vocabulary(feature))
    names.extend(NUMERIC_FEATURES)
    return names


def encode_example(example: TrainingExample) -> list[float]:
    """Encode one example into the fixed-width numeric row."""
    features = example.features
    row: list[float] = []

    for feature in CATEGORICAL_FEATURES:
        value = getattr(features, feature)
        vocabulary = _vocabulary(feature)
        matched = value if value in vocabulary else UNKNOWN_CATEGORY
        row.extend(1.0 if candidate == matched else 0.0 for candidate in vocabulary)

    for feature in NUMERIC_FEATURES:
        ceiling = NUMERIC_CEILINGS[feature]
        raw = float(getattr(features, feature))
        row.append(min(raw, float(ceiling)) / float(ceiling))

    return row


def encode_dataset(
    examples: list[TrainingExample],
) -> tuple[list[list[float]], list[str]]:
    """Encode examples into (feature matrix, target labels)."""
    matrix = [encode_example(example) for example in examples]
    targets = [example.label_difficulty_direction for example in examples]
    return matrix, targets
