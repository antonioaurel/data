"""Validation of the CSVs digitized from the EVE article.

Includes assertions of the article's *known inconsistencies* (data/README.md)
so nobody "fixes" them silently thinking they are typos.
"""

import csv
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name):
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------- events_by_size.csv (tables 7–10) ----------

def test_size_16_events_4_per_class():
    rows = load("events_by_size.csv")
    assert len(rows) == 16
    sizes = {}
    for r in rows:
        sizes[r["size"]] = sizes.get(r["size"], 0) + 1
    assert sizes == {"micro": 4, "small": 4, "medium": 4, "large": 4}


def test_size_sums_close():
    for r in load("events_by_size.csv"):
        total = int(r["no_reply"]) + int(r["maybe"]) + int(r["confirmed"])
        assert total == int(r["invited"]), r


def test_size_attendance_not_above_invited():
    for r in load("events_by_size.csv"):
        assert int(r["attendance"]) <= int(r["invited"]), r


def test_size_ranges_table6():
    ranges = {"micro": (0, 200), "small": (201, 1500),
              "medium": (1501, 5500), "large": (5501, 10**9)}
    for r in load("events_by_size.csv"):
        lo, hi = ranges[r["size"]]
        # documented exception: medium event 3 has 6506 invited (above table 6's
        # range, but classified as medium in the article — table 8)
        if r["size"] == "medium" and r["event"] == "3":
            assert int(r["invited"]) == 6506
            continue
        assert lo <= int(r["invited"]) <= hi, r


# ---------- experiment_pre_eve.csv (table 19) ----------

def test_pre_eve_sums_close():
    for r in load("experiment_pre_eve.csv"):
        total = (int(r["confirmed"]) + int(r["maybe"])
                 + int(r["declined"]) + int(r["no_reply"]))
        assert total == int(r["invited"]), r


# ---------- experiment_eve.csv (tables 22/25/27/28) ----------

RESP = ("confirmed", "maybe", "declined", "no_reply")


def test_experiment_present_not_above_responses():
    for r in load("experiment_eve.csv"):
        for t in RESP:
            assert int(r[f"{t}_present"]) <= int(r[f"{t}_responses"]), (r, t)


def test_experiment_proportions_valid():
    for r in load("experiment_eve.csv"):
        for t in RESP:
            assert 0.0 <= float(r[f"prop_{t}"]) <= 1.0


def test_experiment_sums_with_documented_inconsistency():
    """Sums close exactly, EXCEPT 2013-05-26: 35+4+2+29 = 70 ≠ 69.

    The article's own inconsistency (table 25 vs 22/26) — kept as printed. If
    this test fails, someone changed the source data.
    """
    for r in load("experiment_eve.csv"):
        total = sum(int(r[f"{t}_responses"]) for t in RESP)
        if r["date"] == "2013-05-26":
            assert total == 70 and int(r["invited"]) == 69
        else:
            assert total == int(r["invited"]), r


def test_experiment_attendance_inconsistency_0526():
    """Table 28 prints attendance 35 for 05-26; the per-type sum (table 25) is 37."""
    row = [r for r in load("experiment_eve.csv") if r["date"] == "2013-05-26"][0]
    per_type = sum(int(row[f"{t}_present"]) for t in RESP)
    assert per_type == 37
    assert int(row["article_attendance"]) == 35


# ---------- external_effects.csv (tables 23/28) ----------

def test_effects_dates_belong_to_experiment():
    exp_dates = {r["date"] for r in load("experiment_eve.csv")}
    for r in load("external_effects.csv"):
        assert r["date"] in exp_dates, r


def test_effects_percentages_valid():
    for r in load("external_effects.csv"):
        assert -100 <= float(r["influence_pct"]) <= 100
