#!/usr/bin/env python3
"""Score reverse-intelligence evidence with confidence calibration."""

from __future__ import annotations

import argparse
import json
from typing import Iterable


GRADE_BASE = {"A": 90, "B": 70, "C": 45, "D": 20}
RISK_DEDUCTION = {"low": 0, "medium": 12, "high": 25}
SOURCE_CLASS_WEIGHT = {
    "current_target_code": 10,
    "github_repo": 9,
    "technical_forum": 8,
    "security_writeup": 7,
    "package_registry": 7,
    "developer_blog": 5,
    "video_social": 4,
    "search_summary": 2,
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_grade(value: str) -> str:
    grade = value.upper().strip()
    if grade not in GRADE_BASE:
        raise ValueError("grade must be A, B, C, or D")
    return grade


def score_evidence(
    grade: str,
    source_weight: int,
    technical_similarity: int,
    freshness_risk: str,
    reuse_risk: str,
    positive_reasons: Iterable[str] = (),
    negative_reasons: Iterable[str] = (),
) -> dict[str, object]:
    grade = normalize_grade(grade)
    source_weight = int(clamp(source_weight, 0, 10))
    technical_similarity = int(clamp(technical_similarity, 0, 60))
    freshness_risk = freshness_risk.lower()
    reuse_risk = reuse_risk.lower()
    if freshness_risk not in RISK_DEDUCTION or reuse_risk not in RISK_DEDUCTION:
        raise ValueError("risks must be low, medium, or high")

    raw = (
        GRADE_BASE[grade]
        + source_weight * 2
        + technical_similarity * 0.45
        - RISK_DEDUCTION[freshness_risk]
        - RISK_DEDUCTION[reuse_risk]
    )
    reference_value = round(clamp(raw, 0, 100), 1)
    confidence = round(reference_value / 100, 2)

    return {
        "grade": grade,
        "source_weight": source_weight,
        "technical_similarity": technical_similarity,
        "freshness_risk": freshness_risk,
        "reuse_risk": reuse_risk,
        "reference_value": reference_value,
        "confidence": confidence,
        "positive_reasons": list(positive_reasons),
        "negative_reasons": list(negative_reasons),
    }


def parse_repeated(values: list[str] | None) -> list[str]:
    return [item for item in (values or []) if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grade", required=True, choices=tuple(GRADE_BASE), help="Evidence grade")
    parser.add_argument("--source-weight", type=int, help="Manual source weight from 0-10")
    parser.add_argument("--source-class", choices=tuple(SOURCE_CLASS_WEIGHT), help="Known source class")
    parser.add_argument("--technical-similarity", type=int, default=0, help="Technical similarity from 0-60")
    parser.add_argument("--freshness-risk", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--reuse-risk", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--positive", action="append", help="Reason supporting confidence; repeatable")
    parser.add_argument("--negative", action="append", help="Reason reducing confidence; repeatable")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    return parser.parse_args()


def render_markdown(result: dict[str, object]) -> str:
    positives = result["positive_reasons"] or ["none recorded"]
    negatives = result["negative_reasons"] or ["none recorded"]
    lines = [
        f"# Evidence Score",
        "",
        f"- Grade: `{result['grade']}`",
        f"- Reference value: `{result['reference_value']}`",
        f"- Confidence: `{result['confidence']}`",
        f"- Source weight: `{result['source_weight']}`",
        f"- Technical similarity: `{result['technical_similarity']}`",
        f"- Freshness risk: `{result['freshness_risk']}`",
        f"- Reuse risk: `{result['reuse_risk']}`",
        "",
        "## Positive Reasons",
        "",
    ]
    lines.extend(f"- {item}" for item in positives)
    lines.extend(["", "## Negative Reasons", ""])
    lines.extend(f"- {item}" for item in negatives)
    return "\n".join(lines) + "\n"


def main() -> None:
    args = parse_args()
    source_weight = args.source_weight
    if source_weight is None:
        source_weight = SOURCE_CLASS_WEIGHT.get(args.source_class or "search_summary", 2)
    result = score_evidence(
        args.grade,
        source_weight,
        args.technical_similarity,
        args.freshness_risk,
        args.reuse_risk,
        parse_repeated(args.positive),
        parse_repeated(args.negative),
    )
    if args.format == "markdown":
        print(render_markdown(result), end="")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
