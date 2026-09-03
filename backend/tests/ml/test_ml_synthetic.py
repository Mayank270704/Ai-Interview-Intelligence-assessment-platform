"""Deterministic synthetic scenario generation."""

from collections import Counter

from app.ml.dataset import dataset_digest
from app.ml.schema import TrainingExample
from app.ml.synthetic import SyntheticConfig, generate_dataset

SMALL = SyntheticConfig(interviews=40, seed=7)


def test_generation_is_deterministic_for_a_seed():
    first = generate_dataset(SMALL)
    second = generate_dataset(SMALL)

    assert dataset_digest(first) == dataset_digest(second)
    assert [example.example_id for example in first] == [
        example.example_id for example in second
    ]


def test_different_seeds_produce_different_data():
    first = generate_dataset(SyntheticConfig(interviews=40, seed=7))
    second = generate_dataset(SyntheticConfig(interviews=40, seed=8))

    assert dataset_digest(first) != dataset_digest(second)


def test_every_example_is_marked_synthetic():
    """Generated rows must never be mistakable for real observations."""
    examples = generate_dataset(SMALL)

    assert {example.source for example in examples} == {"synthetic"}


def test_examples_satisfy_the_training_contract():
    for example in generate_dataset(SMALL):
        TrainingExample.model_validate(example.model_dump())


def test_all_three_difficulty_directions_are_represented():
    labels = Counter(
        example.label_difficulty_direction for example in generate_dataset(SMALL)
    )

    assert set(labels) == {"increase", "maintain", "decrease"}
    assert min(labels.values()) >= 2


def test_scenarios_cover_all_question_difficulties():
    difficulties = {
        example.features.question_difficulty for example in generate_dataset(SMALL)
    }

    assert difficulties == {"easy", "medium", "hard"}


def test_claim_verification_outcomes_are_all_exercised():
    examples = generate_dataset(SMALL)

    assert any(example.features.claims_supported > 0 for example in examples)
    assert any(example.features.claims_unsupported > 0 for example in examples)
    assert any(example.features.claims_uncertain > 0 for example in examples)


# ---------------------------------------------------------------------------
# Labels must track the scenario, not be noise
# ---------------------------------------------------------------------------


def test_labels_track_answer_quality_rather_than_being_random():
    """Turns labelled `increase` must genuinely look stronger than those labelled
    `decrease`, otherwise the dataset would teach nothing."""
    examples = generate_dataset(SyntheticConfig(interviews=150, seed=11))
    strong_scale = {"strong": 3, "moderate": 2, "partial": 1, "weak": 0, "other": 1}

    def mean_correctness(label: str) -> float:
        scores = [
            strong_scale.get(example.features.evaluation_technical_correctness, 1)
            for example in examples
            if example.label_difficulty_direction == label
        ]
        return sum(scores) / len(scores)

    assert mean_correctness("increase") > mean_correctness("maintain")
    assert mean_correctness("maintain") > mean_correctness("decrease")


def test_thin_evidence_holds_difficulty_steady():
    """Low evaluation confidence means the interviewer has no basis to move."""
    examples = generate_dataset(SyntheticConfig(interviews=150, seed=11))

    low_confidence = [
        example for example in examples if example.features.evaluation_confidence == "low"
    ]

    assert low_confidence, "the generator should produce some low-confidence turns"
    assert all(
        example.label_difficulty_direction == "maintain" for example in low_confidence
    )


def test_turn_numbers_restart_for_each_interview():
    examples = generate_dataset(SyntheticConfig(interviews=5, seed=3))
    turn_numbers = [example.features.turn_number for example in examples]

    assert turn_numbers.count(1) == 5
    assert min(turn_numbers) == 1


def test_knowledge_counts_accumulate_within_an_interview():
    """Concepts tracked is cumulative, so it never decreases inside one interview."""
    examples = generate_dataset(SyntheticConfig(interviews=8, seed=5))

    previous_turn = 0
    previous_tracked = 0
    for example in examples:
        turn = example.features.turn_number
        tracked = example.features.concepts_tracked
        if turn > previous_turn:
            assert tracked >= previous_tracked
        previous_turn, previous_tracked = (turn, tracked) if turn != 1 else (1, tracked)
