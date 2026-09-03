"""Offline baseline model for next-question difficulty direction.

EXPERIMENTAL. Nothing in the request path imports this module, and no API
response is derived from it. The Interviewer Brain still decides difficulty on
its own; this exists to establish whether the structured signals the pipeline
already produces carry enough information to predict that decision at all.

Target
------
`InterviewDecision.difficulty_direction` -- increase / maintain / decrease, the
interviewer's intent for the next question. It is a real decision, it is not a
restatement of any deterministic formula the codebase already computes (unlike,
say, the final assessment score, which app.ai.assessment.scorer derives in
closed form and which a model would only be memorizing).

Baseline comparison
-------------------
Always reported against a most-frequent-class classifier. On this target the
majority class is large, so accuracy alone flatters any model; macro F1 and
balanced accuracy are what actually show whether the minority movements are
being detected.

scikit-learn is imported inside the functions rather than at module scope, so
importing app.ml never pulls an ML stack into the API process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ml.encoding import encode_dataset, feature_names
from app.ml.schema import TARGET_FIELD, TrainingExample

#: Label order used for every report, so confusion matrices line up across runs.
LABEL_ORDER: tuple[str, ...] = ("decrease", "maintain", "increase")

DEFAULT_SEED = 20260903
DEFAULT_VALIDATION_FRACTION = 0.25


@dataclass
class BaselineReport:
    """Everything needed to judge, and reproduce, one training run."""

    target: str
    model: str
    data_source: str
    train_size: int
    validation_size: int
    feature_count: int
    label_order: list[str]
    class_distribution: dict[str, int]
    model_metrics: dict[str, float]
    majority_baseline_metrics: dict[str, float]
    per_class_f1: dict[str, float]
    confusion_matrix: list[list[int]]
    seed: int
    dataset_digest: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "model": self.model,
            "data_source": self.data_source,
            "train_size": self.train_size,
            "validation_size": self.validation_size,
            "feature_count": self.feature_count,
            "label_order": self.label_order,
            "class_distribution": self.class_distribution,
            "model_metrics": self.model_metrics,
            "majority_baseline_metrics": self.majority_baseline_metrics,
            "per_class_f1": self.per_class_f1,
            "confusion_matrix": self.confusion_matrix,
            "seed": self.seed,
            "dataset_digest": self.dataset_digest,
            "notes": self.notes,
        }


def _metrics(y_true: list[str], y_pred: list[str]) -> dict[str, float]:
    from sklearn.metrics import (
        accuracy_score,
        balanced_accuracy_score,
        f1_score,
    )

    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_true, y_pred)), 4),
    }


def train_baseline(
    examples: list[TrainingExample],
    *,
    seed: int = DEFAULT_SEED,
    validation_fraction: float = DEFAULT_VALIDATION_FRACTION,
) -> BaselineReport:
    """Fit and evaluate the baseline classifier on a held-out split.

    Raises ValueError if the data cannot support a stratified split, rather than
    silently reporting a metric computed on a degenerate set.
    """
    from sklearn.dummy import DummyClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import confusion_matrix, f1_score
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    if len(examples) < 50:
        raise ValueError("At least 50 examples are required to train a baseline.")

    sources = {example.source for example in examples}
    if len(sources) != 1:
        raise ValueError(f"Mixed example sources in one run: {sorted(sources)}")
    data_source = sources.pop()

    matrix, targets = encode_dataset(examples)
    distribution = {label: targets.count(label) for label in LABEL_ORDER}
    if min(distribution.values()) < 2:
        raise ValueError(f"Every class needs at least 2 examples, got {distribution}")

    x_train, x_val, y_train, y_val = train_test_split(
        matrix,
        targets,
        test_size=validation_fraction,
        random_state=seed,
        stratify=targets,
    )

    # Scaled inside the pipeline so the fit is learned on the training split
    # only and travels with the model.
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, random_state=seed, class_weight="balanced"),
    )
    model.fit(x_train, y_train)
    predictions = list(model.predict(x_val))

    majority = DummyClassifier(strategy="most_frequent", random_state=seed)
    majority.fit(x_train, y_train)
    majority_predictions = list(majority.predict(x_val))

    per_class = f1_score(y_val, predictions, average=None, labels=list(LABEL_ORDER), zero_division=0)

    return BaselineReport(
        target=TARGET_FIELD,
        model="LogisticRegression(class_weight=balanced) on one-hot + scaled counts",
        data_source=data_source,
        train_size=len(x_train),
        validation_size=len(x_val),
        feature_count=len(feature_names()),
        label_order=list(LABEL_ORDER),
        class_distribution=distribution,
        model_metrics=_metrics(y_val, predictions),
        majority_baseline_metrics=_metrics(y_val, majority_predictions),
        per_class_f1={
            label: round(float(score), 4) for label, score in zip(LABEL_ORDER, per_class)
        },
        confusion_matrix=[
            [int(cell) for cell in row]
            for row in confusion_matrix(y_val, predictions, labels=list(LABEL_ORDER))
        ],
        seed=seed,
        notes=[
            "Synthetic data only. These numbers measure whether the pipeline and "
            "feature contract work end to end, not real-world accuracy.",
            "Not wired into the interview decision path.",
        ]
        if data_source == "synthetic"
        else [
            "Trained on consented real interview turns.",
            "Not wired into the interview decision path.",
        ],
    )
