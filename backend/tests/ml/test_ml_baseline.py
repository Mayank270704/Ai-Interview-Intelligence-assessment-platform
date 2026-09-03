"""Offline baseline training and evaluation.

Requires scikit-learn (backend/requirements-dev.txt). It is not in the runtime
requirements because nothing in the request path imports it.
"""

import pytest

from app.ml.baseline import LABEL_ORDER, train_baseline
from app.ml.schema import TARGET_FIELD
from app.ml.synthetic import SyntheticConfig, generate_dataset

pytest.importorskip(
    "sklearn",
    reason="scikit-learn is an offline-experimentation dependency; install backend/requirements-dev.txt",
)

DATASET = SyntheticConfig(interviews=180, seed=20260903)


@pytest.fixture(scope="module")
def report():
    return train_baseline(generate_dataset(DATASET), seed=20260903)


def test_reports_the_documented_target(report):
    assert report.target == TARGET_FIELD
    assert report.label_order == list(LABEL_ORDER)


def test_split_is_held_out_and_non_empty(report):
    assert report.train_size > 0
    assert report.validation_size > 0
    assert report.validation_size < report.train_size


def test_training_is_deterministic_for_a_seed():
    first = train_baseline(generate_dataset(DATASET), seed=20260903)
    second = train_baseline(generate_dataset(DATASET), seed=20260903)

    assert first.model_metrics == second.model_metrics
    assert first.confusion_matrix == second.confusion_matrix


def test_model_beats_the_majority_class_baseline(report):
    """The whole point of the baseline comparison: accuracy alone flatters this
    target because `maintain` dominates, so macro F1 is what has to improve."""
    assert report.model_metrics["macro_f1"] > report.majority_baseline_metrics["macro_f1"]
    assert report.model_metrics["accuracy"] > report.majority_baseline_metrics["accuracy"]
    assert (
        report.model_metrics["balanced_accuracy"]
        > report.majority_baseline_metrics["balanced_accuracy"]
    )


def test_minority_classes_are_actually_detected(report):
    """A model that ignored `increase` and `decrease` would still score well on
    accuracy, so each class has to carry real F1 of its own."""
    for label in LABEL_ORDER:
        assert report.per_class_f1[label] > 0.4, f"{label} is not being detected"


def test_metrics_are_not_suspiciously_perfect(report):
    """The generator observes latent ability through noise, so a perfect score
    would mean the label had leaked into the features."""
    assert report.model_metrics["macro_f1"] < 0.99


def test_confusion_matrix_matches_the_validation_size(report):
    total = sum(sum(row) for row in report.confusion_matrix)

    assert total == report.validation_size
    assert len(report.confusion_matrix) == len(LABEL_ORDER)


def test_synthetic_runs_are_labelled_as_synthetic(report):
    """A report must never be readable as real candidate performance."""
    assert report.data_source == "synthetic"
    assert any("Synthetic data only" in note for note in report.notes)
    assert any("Not wired into the interview decision path" in note for note in report.notes)


def test_report_serializes_for_the_evaluation_artifact(report):
    payload = report.to_dict()

    assert payload["target"] == TARGET_FIELD
    assert payload["model_metrics"]["macro_f1"] == report.model_metrics["macro_f1"]
    assert payload["seed"] == 20260903


def test_mixed_sources_in_one_run_are_rejected():
    """Synthetic and real rows must not be silently averaged into one metric."""
    examples = generate_dataset(DATASET)
    mixed = [*examples[:-1], examples[-1].model_copy(update={"source": "consented_interview"})]

    with pytest.raises(ValueError, match="Mixed example sources"):
        train_baseline(mixed)


def test_too_little_data_is_refused_rather_than_scored():
    with pytest.raises(ValueError, match="At least 50 examples"):
        train_baseline(generate_dataset(SyntheticConfig(interviews=2, seed=1)))
