"""Baseline: the original EVE estimation formula (article §4.7.8).

Estimate = sum over response types of (count × expected proportion),
minus fake guests, then adjusted by the event's external effects. The field
experiment had no poster/video signals, so the [(x+y)+(z+y)]/2 branch reduces
to the RSVP-based estimate alone.

The article's own arithmetic is not fully reproducible (see data/README.md);
this module implements one clean interpretation — per-type expectation
truncated to int (matches 7 of 8 printed values), effects applied
multiplicatively, final value rounded — and reports the deviation from the
article's printed predictions rather than forcing agreement.

Run from the project root:  python src/baseline.py
"""

from __future__ import annotations

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

RESPONSE_TYPES = ("confirmed", "maybe", "declined", "no_reply")


def load_experiment() -> list[dict]:
    with open(DATA_DIR / "experiment_eve.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    effects: dict[str, list[float]] = {}
    with open(DATA_DIR / "external_effects.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            effects.setdefault(r["date"], []).append(float(r["influence_pct"]))
    for row in rows:
        row["effects_pct"] = effects.get(row["date"], [])
    return rows


def eve_estimate(
    counts: dict[str, int],
    proportions: dict[str, float],
    effects_pct: list[float],
    fake_guests: int = 0,
) -> float:
    """EVE formula: per-type expected attendees, minus fakes, times effects."""
    expected = sum(int(counts[t] * proportions[t]) for t in RESPONSE_TYPES)
    expected -= fake_guests
    for pct in effects_pct:
        expected *= 1 + pct / 100
    return expected


def run() -> list[dict]:
    results = []
    for row in load_experiment():
        counts = {t: int(row[f"{t}_responses"]) for t in RESPONSE_TYPES}
        props = {t: float(row[f"prop_{t}"]) for t in RESPONSE_TYPES}
        est = eve_estimate(counts, props, row["effects_pct"])
        real = sum(int(row[f"{t}_present"]) for t in RESPONSE_TYPES)
        results.append(
            {
                "date": row["date"],
                "estimate": round(est),
                "article_prediction": int(row["article_prediction"]),
                "attendance": real,
                "article_attendance": int(row["article_attendance"]),
            }
        )
    return results


def mae(pairs: list[tuple[float, float]]) -> float:
    return sum(abs(p - a) for p, a in pairs) / len(pairs)


def mape(pairs: list[tuple[float, float]]) -> float:
    return 100 * sum(abs(p - a) / a for p, a in pairs) / len(pairs)


def main() -> None:
    results = run()
    header = f"{'date':<12}{'our est.':>11}{'article':>9}{'actual':>8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['date']:<12}{r['estimate']:>11}{r['article_prediction']:>9}"
            f"{r['attendance']:>8}"
        )

    ours = [(r["estimate"], r["attendance"]) for r in results]
    article = [(r["article_prediction"], r["attendance"]) for r in results]
    print()
    print(f"MAE  — our implementation: {mae(ours):.2f} | article predictions: {mae(article):.2f}")
    print(f"MAPE — our implementation: {mape(ours):.1f}% | article predictions: {mape(article):.1f}%")

    drift = [r for r in results if abs(r["estimate"] - r["article_prediction"]) > 2]
    if drift:
        print("\nDeviations >2 vs article (known inconsistencies — see data/README.md):")
        for r in drift:
            print(f"  {r['date']}: ours {r['estimate']} vs article {r['article_prediction']}")


if __name__ == "__main__":
    main()
