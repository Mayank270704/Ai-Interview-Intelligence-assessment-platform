"""The training-data contract: what a training example may and may not carry."""

import pytest
from pydantic import ValidationError

from app.ml.encoding import encode_example, feature_names
from app.ml.schema import (
    ANALYSIS_CORRECTNESS,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    SCHEMA_VERSION,
    UNKNOWN_CATEGORY,
    TrainingExample,
    TurnFeatures,
    build_example_id,
    normalize_category,
)


def _features(**overrides) -> TurnFeatures:
    base = {
        "question_difficulty": "medium",
        "question_intent": "DEEPEN",
        "evaluation_focus_count": 2,
        "turn_number": 3,
        "analysis_technical_correctness": "correct",
        "analysis_reasoning_quality": "strong",
        "analysis_answer_relevance": "high",
        "analysis_technical_depth": "deep",
        "analysis_completeness": "complete",
        "demonstrated_concept_count": 3,
        "missing_concept_count": 0,
        "incorrect_concept_count": 0,
        "analysis_unsupported_claim_count": 0,
        "evaluation_technical_correctness": "strong",
        "evaluation_conceptual_understanding": "strong",
        "evaluation_completeness": "complete",
        "evaluation_technical_depth": "deep",
        "evaluation_reasoning_quality": "strong",
        "evaluation_relevance": "high",
        "evaluation_application_ability": "strong",
        "evaluation_confidence": "high",
        "evidence_count": 4,
        "gap_count": 0,
        "strength_count": 3,
        "concepts_tracked": 5,
        "concepts_demonstrated": 4,
        "concepts_missing": 1,
        "concepts_incorrect": 0,
        "claims_supported": 1,
        "claims_unsupported": 0,
        "claims_uncertain": 0,
    }
    base.update(overrides)
    return TurnFeatures(**base)


def _example(**overrides) -> TrainingExample:
    payload = {
        "example_id": build_example_id("interview-1", 3),
        "source": "synthetic",
        "features": _features(),
        "label_difficulty_direction": "increase",
        "label_action": "DEEPEN",
        "label_should_probe_further": False,
    }
    payload.update(overrides)
    return TrainingExample(**payload)


# ---------------------------------------------------------------------------
# Privacy: the contract must be structurally incapable of carrying content
# ---------------------------------------------------------------------------


def test_features_carry_no_free_text_fields():
    """Every feature is a closed-vocabulary category or a count -- never content."""
    allowed = set(CATEGORICAL_FEATURES) | set(NUMERIC_FEATURES)

    assert set(TurnFeatures.model_fields) == allowed


def test_features_reject_unknown_fields():
    """A question, answer, or concept name cannot be smuggled in as an extra."""
    with pytest.raises(ValidationError):
        _features(question_text="How did you build the sentiment model?")

    with pytest.raises(ValidationError):
        TrainingExample(
            example_id=build_example_id("interview-1", 1),
            source="synthetic",
            features=_features(),
            label_difficulty_direction="maintain",
            label_action="DEEPEN",
            label_should_probe_further=True,
            candidate_email="jane@example.com",
        )


def test_categories_must_arrive_normalized():
    """Raw model output is a leak risk and an unusable feature, so it is rejected."""
    with pytest.raises(ValidationError):
        _features(analysis_technical_correctness="Partially Correct")


def test_example_id_is_deterministic_and_one_way():
    first = build_example_id("interview-abc", 4)

    assert first == build_example_id("interview-abc", 4)
    assert first != build_example_id("interview-abc", 5)
    assert first != build_example_id("interview-abd", 4)
    assert "interview-abc" not in first


# ---------------------------------------------------------------------------
# Normalization of upstream categories
# ---------------------------------------------------------------------------


def test_normalize_maps_known_values_onto_the_vocabulary():
    assert normalize_category("Partially Correct", ANALYSIS_CORRECTNESS) == "partially_correct"
    assert normalize_category("  CORRECT  ", ANALYSIS_CORRECTNESS) == "correct"


def test_normalize_buckets_unknown_values_explicitly():
    """The upstream fields are free strings, so anything unrecognized is recorded
    as unknown rather than trusted or dropped."""
    assert normalize_category("mostly_right", ANALYSIS_CORRECTNESS) == UNKNOWN_CATEGORY
    assert normalize_category(None, ANALYSIS_CORRECTNESS) == UNKNOWN_CATEGORY
    assert normalize_category("", ANALYSIS_CORRECTNESS) == UNKNOWN_CATEGORY


def test_unsupported_schema_version_is_rejected():
    with pytest.raises(ValidationError):
        _example(schema_version="0.9")


def test_current_schema_version_round_trips():
    assert _example().schema_version == SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------


def test_encoding_width_matches_the_declared_columns():
    assert len(encode_example(_example())) == len(feature_names())


def test_encoding_is_stable_across_calls():
    example = _example()

    assert encode_example(example) == encode_example(example)


def test_one_hot_blocks_select_exactly_one_value_each():
    row = encode_example(_example())
    names = feature_names()
    categorical_width = len(names) - len(NUMERIC_FEATURES)

    for feature in CATEGORICAL_FEATURES:
        indices = [i for i, name in enumerate(names[:categorical_width]) if name.startswith(f"{feature}=")]
        assert sum(row[i] for i in indices) == 1.0, f"{feature} did not select one value"


def test_counts_are_clipped_into_the_unit_range():
    """An outlier count must not be able to dominate a scaled model."""
    assert all(0.0 <= value <= 1.0 for value in encode_example(_example()))

    extreme = TrainingExample(
        example_id=build_example_id("interview-1", 1),
        source="synthetic",
        features=_features(evidence_count=10_000, concepts_tracked=10_000),
        label_difficulty_direction="maintain",
        label_action="DEEPEN",
        label_should_probe_further=True,
    )

    assert all(0.0 <= value <= 1.0 for value in encode_example(extreme))
