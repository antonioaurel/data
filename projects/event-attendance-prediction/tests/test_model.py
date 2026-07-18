"""Tests for the learned-rates model."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import model  # noqa: E402


def test_rates_ordered_by_size():
    """Confirmation→attendance conversion should fall (nearly) monotonically."""
    coef = model.fit()
    r = coef["rates"]
    assert r["micro"]["confirmed"] > r["small"]["confirmed"] > r["medium"]["confirmed"]
    # medium vs large is noisy in the data (tables 8 vs 7) — only same magnitude
    assert abs(r["medium"]["confirmed"] - r["large"]["confirmed"]) < 0.05


def test_declined_rate_zero_and_bounds():
    coef = model.fit()
    for size in model.SIZES:
        assert coef["rates"][size]["declined"] == 0.0
        for t in model.RESPONSE_TYPES:
            assert 0.0 <= coef["rates"][size][t] <= 1.0


def test_predict_with_effects():
    coef = model.fit()
    counts = {"confirmed": 100, "maybe": 0, "declined": 0, "no_reply": 0}
    without = model.predict(counts, "micro", coef)
    with_eff = model.predict(counts, "micro", coef, effects_pct=[-20])
    assert abs(with_eff - without * 0.8) < 1e-9


def test_metrics_regression():
    """Pins the current metrics; refits with altered data should flag here."""
    coef = model.fit()
    ev = model.evaluate(coef)
    assert len(ev["rows"]) == 20
    assert round(ev["mae"], 1) == 34.4
    assert round(ev["mape_pct"], 1) == 24.4
    # on the experiment, the operator-free model nearly ties the baseline (MAE 3.0)
    exp = [r for r in ev["rows"] if r["set"] == "experiment"]
    mae_exp = sum(abs(r["predicted"] - r["actual"]) for r in exp) / len(exp)
    assert mae_exp < 4.0


def test_export_json_consistent(tmp_path):
    coef = model.fit()
    ev = model.evaluate(coef)
    out = model.export(coef, ev, path=tmp_path / "coef.json")
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert set(payload["rates"]) == set(model.SIZES)
    for size in model.SIZES:
        assert set(payload["rates"][size]) == set(model.RESPONSE_TYPES)
