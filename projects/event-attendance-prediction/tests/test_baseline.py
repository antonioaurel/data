"""Unit + regression tests for the EVE baseline formula."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import baseline  # noqa: E402


def test_simple_formula():
    counts = {"confirmed": 10, "maybe": 10, "declined": 10, "no_reply": 100}
    props = {"confirmed": 0.5, "maybe": 0.2, "declined": 0.0, "no_reply": 0.05}
    # int(5) + int(2) + 0 + int(5) = 12, no effects
    assert baseline.eve_estimate(counts, props, []) == 12


def test_per_type_truncation():
    # 19 × 0.5 = 9.5 → truncated to 9 (article behavior, table 28)
    counts = {"confirmed": 19, "maybe": 0, "declined": 0, "no_reply": 0}
    props = {"confirmed": 0.5, "maybe": 0, "declined": 0, "no_reply": 0}
    assert baseline.eve_estimate(counts, props, []) == 9


def test_fake_guests_subtracted():
    counts = {"confirmed": 20, "maybe": 0, "declined": 0, "no_reply": 0}
    props = {"confirmed": 1.0, "maybe": 0, "declined": 0, "no_reply": 0}
    assert baseline.eve_estimate(counts, props, [], fake_guests=5) == 15


def test_effects_multiplicative():
    counts = {"confirmed": 100, "maybe": 0, "declined": 0, "no_reply": 0}
    props = {"confirmed": 1.0, "maybe": 0, "declined": 0, "no_reply": 0}
    assert baseline.eve_estimate(counts, props, [-20]) == 80
    assert baseline.eve_estimate(counts, props, [-50, -50]) == 25


def test_zero_counts():
    counts = {"confirmed": 0, "maybe": 0, "declined": 0, "no_reply": 0}
    props = {"confirmed": 0.9, "maybe": 0.6, "declined": 0, "no_reply": 0.1}
    assert baseline.eve_estimate(counts, props, [-20]) == 0


def test_experiment_regression():
    """Pins the current results over the digitized CSVs.

    If the digitization or the formula changes, this test flags it.
    """
    results = baseline.run()
    assert [r["estimate"] for r in results] == [22, 20, 29, 32]
    assert [r["article_prediction"] for r in results] == [21, 21, 23, 32]
    assert [r["attendance"] for r in results] == [17, 22, 29, 37]

    ours = [(r["estimate"], r["attendance"]) for r in results]
    article = [(r["article_prediction"], r["attendance"]) for r in results]
    assert baseline.mae(ours) == 3.0
    assert baseline.mae(article) == 4.0
