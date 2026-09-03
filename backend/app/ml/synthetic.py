"""Deterministic synthetic interview data for offline experimentation.

Real candidates must never be silently turned into training data, so the
baseline is developed against generated scenarios instead. Every row produced
here is stamped `source="synthetic"` and must never be presented as an
observation of a real person.

How a scenario is built
-----------------------
Each interview draws a latent `ability` in [0, 1]. Each turn computes a latent
`performance` from that ability against the demand of the question difficulty,
plus noise. The observable features -- what Answer Intelligence and the
Evaluation Engine would have reported -- are then sampled *around* that latent
performance, so they are informative but imperfect proxies for it.

The labels come from an interviewing policy applied to the latent performance,
not from the observable features and not from a coin flip. That is what makes
the learning problem real: a model has to infer the latent state through noisy
observations, and cannot reach perfect accuracy by memorizing one column.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.ml.schema import (
    EVALUATION_CONFIDENCE,
    TrainingExample,
    TurnFeatures,
    build_example_id,
)
from app.schemas.interview_decision import DifficultyDirection, InterviewerActionType
from app.schemas.question import QuestionDifficulty

DIFFICULTY_LADDER: tuple[QuestionDifficulty, ...] = ("easy", "medium", "hard")

#: How much competence each difficulty demands. Performance is ability net of this.
_DIFFICULTY_DEMAND = {"easy": 0.28, "medium": 0.50, "hard": 0.72}

# Ordinal ladders, worst outcome first, matching the vocabularies documented on
# the interview schemas these features mirror.
_ANALYSIS_CORRECTNESS = ("incorrect", "partially_correct", "correct")
_ANALYSIS_REASONING = ("unclear", "weak", "adequate", "strong")
_ANALYSIS_RELEVANCE = ("off_topic", "low", "medium", "high")
_ANALYSIS_DEPTH = ("insufficient", "shallow", "moderate", "deep")
_ANALYSIS_COMPLETENESS = ("vague", "incomplete", "partial", "complete")

_EVAL_CORRECTNESS = ("weak", "partial", "moderate", "strong")
_EVAL_UNDERSTANDING = ("limited", "weak", "moderate", "strong")
_EVAL_COMPLETENESS = ("vague", "incomplete", "partial", "complete")
_EVAL_DEPTH = ("limited", "shallow", "moderate", "deep")
_EVAL_REASONING = ("limited", "weak", "moderate", "strong")
_EVAL_RELEVANCE = ("off_topic", "low", "medium", "high")
_EVAL_APPLICATION = ("weak", "limited", "moderate", "strong")

_QUESTION_INTENTS: tuple[InterviewerActionType, ...] = (
    "DEEPEN",
    "CLARIFY",
    "CHALLENGE",
    "EXPLORE_RELATED_CONCEPT",
    "INVESTIGATE_CLAIM",
    "CHANGE_TOPIC",
)

#: Spread of the observation noise around latent performance.
_OBSERVATION_JITTER = 0.15
#: Latent performance above/below which the interviewer moves difficulty.
_RAISE_THRESHOLD = 0.66
_LOWER_THRESHOLD = 0.34


@dataclass(frozen=True)
class SyntheticConfig:
    """Shape of a generated dataset."""

    interviews: int = 220
    min_turns: int = 4
    max_turns: int = 9
    seed: int = 20260903


def _graded(rng: random.Random, performance: float, ladder: tuple[str, ...]) -> str:
    """Sample an ordinal category near `performance`, worst-first ladder."""
    position = performance + rng.gauss(0.0, _OBSERVATION_JITTER)
    clamped = min(0.9999, max(0.0, position))
    return ladder[int(clamped * len(ladder))]


def _count_near(rng: random.Random, centre: float, spread: int) -> int:
    """A small non-negative count centred on `centre`."""
    return max(0, round(centre + rng.uniform(-spread, spread)))


def _decide_direction(performance: float, confidence: str) -> DifficultyDirection:
    """The interviewing policy the synthetic labels follow.

    This is the interviewer's *intent*, matching what InterviewDecision records:
    move on clear evidence, hold when the evidence is too thin to justify it.
    Clamping to the ends of the ladder happens when the intent is applied (see
    _step_difficulty), exactly as InterviewTurnService._select_difficulty does,
    so the label stays the decision rather than its clamped effect.
    """
    if confidence == "low":
        return "maintain"
    if performance >= _RAISE_THRESHOLD:
        return "increase"
    if performance <= _LOWER_THRESHOLD:
        return "decrease"
    return "maintain"


def _decide_action(
    rng: random.Random, performance: float, incorrect_concepts: int, investigating_claim: bool
) -> InterviewerActionType:
    """A plausible next action for the same scenario."""
    if investigating_claim:
        return "INVESTIGATE_CLAIM"
    if incorrect_concepts >= 2 or (incorrect_concepts >= 1 and performance < 0.5):
        return "CLARIFY"
    if performance >= _RAISE_THRESHOLD:
        return rng.choice(["CONCLUDE_TOPIC", "CHANGE_TOPIC", "CHALLENGE"])
    if performance <= _LOWER_THRESHOLD:
        return rng.choice(["DECREASE_DIFFICULTY", "CLARIFY"])
    return rng.choice(["DEEPEN", "EXPLORE_RELATED_CONCEPT"])


def _step_difficulty(
    difficulty: QuestionDifficulty, direction: DifficultyDirection
) -> QuestionDifficulty:
    """Apply a difficulty direction, clamped to the ladder."""
    index = DIFFICULTY_LADDER.index(difficulty)
    if direction == "increase":
        index = min(index + 1, len(DIFFICULTY_LADDER) - 1)
    elif direction == "decrease":
        index = max(index - 1, 0)
    return DIFFICULTY_LADDER[index]


def generate_dataset(config: SyntheticConfig | None = None) -> list[TrainingExample]:
    """Generate a synthetic training set. Identical for identical config."""
    settings = config or SyntheticConfig()
    rng = random.Random(settings.seed)
    examples: list[TrainingExample] = []

    for interview_index in range(settings.interviews):
        ability = rng.random()
        turns = rng.randint(settings.min_turns, settings.max_turns)
        difficulty: QuestionDifficulty = "medium"

        # Knowledge accumulates over the interview rather than resetting per turn.
        concepts_tracked = 0
        concepts_demonstrated = 0
        concepts_missing = 0
        concepts_incorrect = 0
        claims_supported = 0
        claims_unsupported = 0
        claims_uncertain = 0

        for turn_number in range(1, turns + 1):
            demand = _DIFFICULTY_DEMAND[difficulty]
            performance = min(1.0, max(0.0, 0.5 + (ability - demand) + rng.gauss(0.0, 0.10)))

            investigating_claim = rng.random() < 0.25
            intent: InterviewerActionType = (
                "INVESTIGATE_CLAIM" if investigating_claim else rng.choice(_QUESTION_INTENTS)
            )

            demonstrated = _count_near(rng, performance * 3.5, 1)
            missing = _count_near(rng, (1.0 - performance) * 3.0, 1)
            incorrect = _count_near(rng, (1.0 - performance) * 1.6, 1)
            unsupported = _count_near(rng, (1.0 - performance) * 1.2, 1)
            evidence = _count_near(rng, 1.5 + performance * 3.0, 1)
            gaps = missing
            strengths = demonstrated

            # Richer evidence supports a more confident evaluation; thin evidence
            # keeps the interviewer from moving difficulty at all.
            if evidence >= 4:
                confidence = "high"
            elif evidence >= 2:
                confidence = "medium"
            else:
                confidence = "low"
            assert confidence in EVALUATION_CONFIDENCE

            concepts_tracked += max(1, demonstrated + missing)
            concepts_demonstrated += demonstrated
            concepts_missing += missing
            concepts_incorrect += incorrect
            if investigating_claim:
                if performance >= 0.6:
                    claims_supported += 1
                elif performance <= 0.35:
                    claims_unsupported += 1
                else:
                    claims_uncertain += 1

            features = TurnFeatures(
                question_difficulty=difficulty,
                question_intent=intent,
                evaluation_focus_count=rng.randint(1, 4),
                turn_number=turn_number,
                analysis_technical_correctness=_graded(rng, performance, _ANALYSIS_CORRECTNESS),
                analysis_reasoning_quality=_graded(rng, performance, _ANALYSIS_REASONING),
                analysis_answer_relevance=_graded(rng, performance, _ANALYSIS_RELEVANCE),
                analysis_technical_depth=_graded(rng, performance, _ANALYSIS_DEPTH),
                analysis_completeness=_graded(rng, performance, _ANALYSIS_COMPLETENESS),
                demonstrated_concept_count=demonstrated,
                missing_concept_count=missing,
                incorrect_concept_count=incorrect,
                analysis_unsupported_claim_count=unsupported,
                evaluation_technical_correctness=_graded(rng, performance, _EVAL_CORRECTNESS),
                evaluation_conceptual_understanding=_graded(rng, performance, _EVAL_UNDERSTANDING),
                evaluation_completeness=_graded(rng, performance, _EVAL_COMPLETENESS),
                evaluation_technical_depth=_graded(rng, performance, _EVAL_DEPTH),
                evaluation_reasoning_quality=_graded(rng, performance, _EVAL_REASONING),
                evaluation_relevance=_graded(rng, performance, _EVAL_RELEVANCE),
                evaluation_application_ability=_graded(rng, performance, _EVAL_APPLICATION),
                evaluation_confidence=confidence,
                evidence_count=evidence,
                gap_count=gaps,
                strength_count=strengths,
                concepts_tracked=concepts_tracked,
                concepts_demonstrated=concepts_demonstrated,
                concepts_missing=concepts_missing,
                concepts_incorrect=concepts_incorrect,
                claims_supported=claims_supported,
                claims_unsupported=claims_unsupported,
                claims_uncertain=claims_uncertain,
            )

            direction = _decide_direction(performance, confidence)
            action = _decide_action(rng, performance, incorrect, investigating_claim)

            examples.append(
                TrainingExample(
                    example_id=build_example_id(
                        f"synthetic:{settings.seed}:{interview_index}", turn_number
                    ),
                    source="synthetic",
                    features=features,
                    label_difficulty_direction=direction,
                    label_action=action,
                    label_should_probe_further=performance < _RAISE_THRESHOLD or missing > 0,
                )
            )

            difficulty = _step_difficulty(difficulty, direction)

    return examples
