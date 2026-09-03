"""Reproducible offline baseline run for next-question difficulty direction.

Run from the repository root:

    python ai-lab/experiments/adaptive_interview/train_baseline.py

Writes the generated dataset and the metrics report under ai-lab/. Both are
reproducible from the seed and are not tracked in git. Nothing here touches the
running application or any candidate data: by default it trains on generated
scenarios, never on real interviews.

Pass --source consented to train on real interview turns instead. That path
exports only turns whose candidate explicitly opted in (app.ml.consent) and
requires DATABASE_URL to be configured.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml.baseline import train_baseline  # noqa: E402
from app.ml.dataset import dataset_digest, write_jsonl  # noqa: E402
from app.ml.schema import TrainingExample  # noqa: E402
from app.ml.synthetic import SyntheticConfig, generate_dataset  # noqa: E402

AI_LAB = REPO_ROOT / "ai-lab"
DATASET_PATH = AI_LAB / "datasets" / "adaptive_interview_baseline.jsonl"
REPORT_PATH = AI_LAB / "evaluation" / "adaptive_interview_baseline.json"


def load_examples(source: str, seed: int, interviews: int) -> list[TrainingExample]:
    if source == "synthetic":
        return generate_dataset(SyntheticConfig(interviews=interviews, seed=seed))

    from app.db.database import session_scope
    from app.ml.dataset import export_consented_examples

    with session_scope() as session:
        examples = export_consented_examples(session)
    if not examples:
        raise SystemExit(
            "No consented interview turns are available to export. Real interviews "
            "are only eligible once a candidate has explicitly opted in."
        )
    return examples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("synthetic", "consented"), default="synthetic")
    parser.add_argument("--seed", type=int, default=SyntheticConfig().seed)
    parser.add_argument("--interviews", type=int, default=SyntheticConfig().interviews)
    arguments = parser.parse_args()

    examples = load_examples(arguments.source, arguments.seed, arguments.interviews)
    digest = dataset_digest(examples)

    report = train_baseline(examples, seed=arguments.seed)
    report.dataset_digest = digest

    write_jsonl(examples, DATASET_PATH)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")

    banner = (
        "SYNTHETIC DATA - measures the pipeline, not real-world accuracy"
        if report.data_source == "synthetic"
        else "CONSENTED REAL INTERVIEW DATA"
    )
    print(f"=== Adaptive interview baseline | {banner} ===")
    print(f"target                 {report.target}")
    print(f"examples               {len(examples)} (train {report.train_size} / val {report.validation_size})")
    print(f"features               {report.feature_count}")
    print(f"class distribution     {report.class_distribution}")
    print(f"dataset digest         {report.dataset_digest[:16]}")
    print()
    print(f"model                  {report.model_metrics}")
    print(f"majority baseline      {report.majority_baseline_metrics}")
    print(f"per-class F1           {report.per_class_f1}")
    print(f"confusion ({'/'.join(report.label_order)})")
    for label, row in zip(report.label_order, report.confusion_matrix):
        print(f"  {label:9} {row}")
    print()
    print(f"dataset  -> {DATASET_PATH.relative_to(REPO_ROOT)}")
    print(f"report   -> {REPORT_PATH.relative_to(REPO_ROOT)}")
    for note in report.notes:
        print(f"note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
