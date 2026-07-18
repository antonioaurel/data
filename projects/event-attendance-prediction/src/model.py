"""Learned-rates model: replaces EVE's operator-informed proportions.

EVE's weakness was requiring the operator to *guess* the attendance proportion
per response type. Here the rates are estimated from the digitized data:

1. **Per-response rates** (confirmed / maybe / declined / no_reply) pooled from
   the field experiment (table 25) — the only source with attendance broken
   down by response type.
2. **Size-class calibration**: a scale factor k per size class fitted on
   tables 7–10 so that predicted totals match observed attendance:
   k(size) = Σ attendance / Σ (counts · experiment_rates).

    rate[size][type] = rate_exp(type) × k(size)   (capped at 1)

Predictions: attendance ≈ Σ_type count_type × rate[size][type], optionally
adjusted by external effects (multiplicative, like the baseline).

`python src/model.py` fits, evaluates against the baseline and writes the
coefficients to data/model_coefficients.json (consumed by the app/dashboard).

Honest caveats (also in notebook 02): n is tiny; evaluation is in-sample;
treat this as v1 calibration, to be refit as the tool's history grows.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RESPONSE_TYPES = ("confirmed", "maybe", "declined", "no_reply")
SIZES = ("micro", "small", "medium", "large")

# Size class of each field-experiment event (article §5: 420 guests → small,
# the rehearsals of 73/77/69 guests → micro).
EXPERIMENT_SIZE = {
    "2013-05-05": "small",
    "2013-05-12": "micro",
    "2013-05-20": "micro",
    "2013-05-26": "micro",
}


def _read(name: str) -> list[dict]:
    with open(DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fit() -> dict:
    """Estimate rates from the digitized article data."""
    # 1. pooled per-response rates from the experiment
    exp = _read("experiment_eve.csv")
    exp_rates = {}
    for t in RESPONSE_TYPES:
        responses = sum(int(r[f"{t}_responses"]) for r in exp)
        present = sum(int(r[f"{t}_present"]) for r in exp)
        exp_rates[t] = present / responses if responses else 0.0

    # 2. per-size-class scale factor k fitted on tables 7–10:
    # k = Σ attendance / Σ (counts · experiment rates).
    # Attendance there is total (not per-type), so k calibrates the level
    # while the experiment provides the shape across response types.
    size_rows = _read("events_by_size.csv")
    k_size = {}
    for size in SIZES:
        rows = [r for r in size_rows if r["size"] == size]
        pred_base = sum(
            int(r["confirmed"]) * exp_rates["confirmed"]
            + int(r["maybe"]) * exp_rates["maybe"]
            + int(r["no_reply"]) * exp_rates["no_reply"]
            for r in rows
        )
        real = sum(int(r["attendance"]) for r in rows)
        k_size[size] = real / pred_base if pred_base else 1.0

    rates = {
        size: {t: min(1.0, exp_rates[t] * k_size[size])
               for t in RESPONSE_TYPES}
        for size in SIZES
    }

    return {"rates": rates, "exp_rates": exp_rates, "k_size": k_size}


def predict(counts: dict[str, int], size: str, coef: dict,
            effects_pct: list[float] | None = None) -> float:
    est = sum(counts[t] * coef["rates"][size][t] for t in RESPONSE_TYPES)
    for pct in effects_pct or []:
        est *= 1 + pct / 100
    return est


def evaluate(coef: dict) -> dict:
    """In-sample evaluation on the 16 size-class events + 4 experiment events."""
    rows = []
    for r in _read("events_by_size.csv"):
        counts = {
            "confirmed": int(r["confirmed"]),
            "maybe": int(r["maybe"]),
            "declined": 0,
            "no_reply": int(r["no_reply"]),
        }
        pred = predict(counts, r["size"], coef)
        rows.append({
            "set": "size",
            "id": f"{r['size']}-{r['event']}",
            "size": r["size"],
            "predicted": round(pred, 1),
            "actual": int(r["attendance"]),
        })
    for r in _read("experiment_eve.csv"):
        counts = {t: int(r[f"{t}_responses"]) for t in RESPONSE_TYPES}
        real = sum(int(r[f"{t}_present"]) for t in RESPONSE_TYPES)
        pred = predict(counts, EXPERIMENT_SIZE[r["date"]], coef)
        rows.append({
            "set": "experiment",
            "id": r["date"],
            "size": EXPERIMENT_SIZE[r["date"]],
            "predicted": round(pred, 1),
            "actual": real,
        })

    abs_err = [abs(x["predicted"] - x["actual"]) for x in rows]
    pct_err = [abs(x["predicted"] - x["actual"]) / x["actual"] for x in rows]
    return {
        "rows": rows,
        "mae": sum(abs_err) / len(abs_err),
        "mape_pct": 100 * sum(pct_err) / len(pct_err),
    }


def export(coef: dict, evaluation: dict,
           path: Path = DATA_DIR / "model_coefficients.json") -> Path:
    payload = {
        "version": 1,
        "source": "tables 7-10 and 25 of the EVE article (2016); in-sample fit",
        "response_types": list(RESPONSE_TYPES),
        "rates": coef["rates"],
        "metrics": {
            "mae": round(evaluation["mae"], 2),
            "mape_pct": round(evaluation["mape_pct"], 1),
        },
        "size_ranges": {
            "micro": [0, 200], "small": [201, 1500],
            "medium": [1501, 5500], "large": [5501, None],
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return path


def main() -> None:
    coef = fit()
    ev = evaluate(coef)

    print("Learned rates (expected attendance per response):")
    header = f"{'size':<10}" + "".join(f"{t:>11}" for t in RESPONSE_TYPES)
    print(header)
    for size in SIZES:
        line = f"{size:<10}" + "".join(
            f"{coef['rates'][size][t]:>11.3f}" for t in RESPONSE_TYPES)
        print(line)

    print(f"\nIn-sample evaluation (n={len(ev['rows'])} events):")
    print(f"MAE {ev['mae']:.2f} | MAPE {ev['mape_pct']:.1f}%")

    exp_rows = [r for r in ev["rows"] if r["set"] == "experiment"]
    print("\nExperiment (comparable to the baseline, which had MAE 3.0):")
    for r in exp_rows:
        print(f"  {r['id']}: predicted {r['predicted']:.0f} | actual {r['actual']}")

    out = export(coef, ev)
    print(f"\nCoefficients exported to {out.relative_to(DATA_DIR.parent)}")


if __name__ == "__main__":
    main()
