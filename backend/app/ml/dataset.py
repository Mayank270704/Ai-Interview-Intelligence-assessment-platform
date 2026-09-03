"""Deterministic serialization and export of training datasets.

JSON Lines: one example per line, keys sorted, no wrapping object. The same
examples always produce byte-identical output, so a dataset can be hashed,
diffed, and reproduced.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Iterator

from sqlalchemy.orm import Session

from app.ml.consent import eligible_turns
from app.ml.features import example_from_turn
from app.ml.schema import TrainingExample


def serialize_example(example: TrainingExample) -> str:
    """Render one example as a single deterministic JSON line."""
    return json.dumps(
        example.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def deserialize_example(line: str) -> TrainingExample:
    """Parse and validate one JSON line back into an example."""
    return TrainingExample.model_validate(json.loads(line))


def write_jsonl(examples: Iterable[TrainingExample], path: str | Path) -> int:
    """Write examples to a JSON Lines file, returning how many were written."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with destination.open("w", encoding="utf-8", newline="\n") as handle:
        for example in examples:
            handle.write(serialize_example(example))
            handle.write("\n")
            written += 1
    return written


def read_jsonl(path: str | Path) -> Iterator[TrainingExample]:
    """Stream examples back from a JSON Lines file, validating each row."""
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                yield deserialize_example(stripped)


def dataset_digest(examples: Iterable[TrainingExample]) -> str:
    """Content hash of a dataset, for pinning which data a run was trained on."""
    digest = hashlib.sha256()
    for example in examples:
        digest.update(serialize_example(example).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def export_consented_examples(
    session: Session, *, interview_id: str | None = None
) -> list[TrainingExample]:
    """Build training examples from every consented, fully-derived interview turn.

    Turns that are unanswered, or missing any of the derived analysis, evaluation
    or decision, are skipped rather than filled in with defaults.
    """
    examples = []
    for turn in eligible_turns(session, interview_id=interview_id):
        example = example_from_turn(turn, source="consented_interview")
        if example is not None:
            examples.append(example)
    return examples
