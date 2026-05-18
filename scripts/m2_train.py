"""M2 Phase 2 — train the dummy-v0 grading model.

Pipeline:
  1. Load `corpus/features.csv` and merge in labels:
     - Delcamp grades from manifest (already in the CSV).
     - Dummy advisor placeholders from `corpus/dummy_advisor_grades.csv`.
  2. Project labels to a 6-class scheme matching the band labels used
     elsewhere ("3", "5", "6", "7", "8", "9"). G4 is folded into G5 and
     G10 into G9 because the corpus has fewer than ten examples of
     either — sklearn's solver complains otherwise.
  3. Standardise numeric features, train a multinomial logistic
     regression with class-balanced weights.
  4. Persist coefficients + scaler params + feature order to
     `corpus/model_dummy_v0.json` so the model can be re-applied without
     a sklearn round-trip.
  5. Score every piece in the corpus and write predictions to
     `corpus/model_grades.csv` with `model_version = "dummy-v0"`.

This is dummy data end-to-end. The training plumbing is real but every
output carries a version tag the advisor must change before the model
is allowed to be called real. See decisions/0010-m2-close-with-dummy-labels.md.

Usage:
    python scripts/m2_train.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from m1_common import REPO_ROOT


DEFAULT_FEATURES = REPO_ROOT / "corpus" / "features.csv"
DEFAULT_DUMMY = REPO_ROOT / "corpus" / "dummy_advisor_grades.csv"
DEFAULT_MODEL = REPO_ROOT / "corpus" / "model_dummy_v0.json"
DEFAULT_PREDICTIONS = REPO_ROOT / "corpus" / "model_grades.csv"

MODEL_VERSION = "dummy-v0"

# Feature columns fed into the model. Only fully numeric features here;
# string columns (time_sig, key_fifths) are skipped to keep the model
# minimal and the advisor's feature-list conversation simple.
NUMERIC_FEATURES = [
    "midi_min", "midi_max", "midi_range", "midi_median",
    "key_changes", "meter_changes",
    "smallest_division", "dotted_count", "tied_count", "tuplet_count",
    "notes_per_measure", "accidentals_outside_key",
    "max_chord_stack", "polyphonic_measure_ratio", "voice_count_max",
    "ornament_mordent", "ornament_trill", "ornament_turn", "grace_count",
    "harmonic_count", "barre_count",
    "pitch_min_fret_max", "pitch_min_fret_p90", "pitch_position_shifts",
    "measure_count", "note_count", "duration_sec_approx",
]

# Grade collapsing — see module docstring.
GRADE_REMAP = {"4": "5", "10": "9"}
GRADE_CLASSES = ["3", "5", "6", "7", "8", "9"]


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def load_labelled(features_path: Path, dummy_path: Path
                  ) -> tuple[list[dict[str, str]], dict[str, str]]:
    """Return (all-rows, label-map). Labels merge Delcamp + dummy advisor.

    Dummy advisor labels overwrite Delcamp grades for pieces that
    appear in both files (no overlap expected in practice; explicit
    behavior here so dual-labelling later is unambiguous).
    """
    with features_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    labels: dict[str, str] = {}
    for r in rows:
        if r.get("grade"):
            labels[r["candidate_id"]] = r["grade"]

    if dummy_path.exists():
        with dummy_path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                cid = r.get("candidate_id")
                g = r.get("dummy_grade")
                if cid and g:
                    labels[cid] = g

    return rows, labels


def featurize(rows: list[dict[str, str]]) -> tuple[np.ndarray, list[int]]:
    """Build X = (n_rows, n_features). Missing values get column-median.

    Returns (X, kept_indices) where kept_indices is the row indices
    in the original list whose features were all extractable.
    """
    cols: list[list[float | None]] = []
    for f in NUMERIC_FEATURES:
        col = [_to_float(r.get(f, "")) for r in rows]
        cols.append(col)

    # Median imputation per column.
    medians: list[float] = []
    for col in cols:
        present = [v for v in col if v is not None]
        medians.append(float(np.median(present)) if present else 0.0)

    n = len(rows)
    X = np.zeros((n, len(NUMERIC_FEATURES)))
    for j, col in enumerate(cols):
        for i, v in enumerate(col):
            X[i, j] = v if v is not None else medians[j]
    return X, list(range(n))


def _project_grade(g: str) -> str:
    return GRADE_REMAP.get(g, g)


def train_and_save(features_path: Path, dummy_path: Path,
                   model_path: Path, predictions_path: Path) -> dict:
    rows, labels = load_labelled(features_path, dummy_path)
    X_all, _ = featurize(rows)

    labelled_idx: list[int] = []
    y_raw: list[str] = []
    for i, r in enumerate(rows):
        cid = r["candidate_id"]
        if cid in labels:
            labelled_idx.append(i)
            y_raw.append(_project_grade(labels[cid]))

    if not labelled_idx:
        raise SystemExit("No labelled rows found. Did m2_features.py run?")

    X = X_all[labelled_idx]
    y = np.array(y_raw)

    # Standardise on the labelled set; reuse scaler params for all rows.
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    X_scaled = (X - mean) / std

    model = LogisticRegression(
        solver="lbfgs",
        class_weight="balanced",
        max_iter=2000,
        C=1.0,
        random_state=42,
    )
    model.fit(X_scaled, y)

    # Score every piece (labelled + unlabelled) on the same scaler.
    X_all_scaled = (X_all - mean) / std
    preds = model.predict(X_all_scaled)
    probs = model.predict_proba(X_all_scaled)
    classes = list(model.classes_)

    # Training-set agreement (in-sample; honest eval lives in m2_eval.py).
    in_sample = model.predict(X_scaled)
    exact = float(np.mean(in_sample == y))
    within1 = float(np.mean(np.abs(in_sample.astype(int) - y.astype(int)) <= 1))

    # Persist a JSON form so the model is reloadable without sklearn.
    payload = {
        "model_version": MODEL_VERSION,
        "trained_on": {
            "labelled_rows": len(labelled_idx),
            "delcamp_rows": sum(
                1 for r in rows if r.get("grade")
                and r.get("grade_source") and "delcamp" in r["grade_source"].lower()
            ),
            "dummy_advisor_rows": sum(
                1 for cid in labels
                if cid in {r["candidate_id"] for r in rows
                           if not r.get("grade")}
            ),
        },
        "in_sample": {"exact": exact, "within_one": within1},
        "feature_order": NUMERIC_FEATURES,
        "scaler_mean": mean.tolist(),
        "scaler_std": std.tolist(),
        "classes": classes,
        "coef": model.coef_.tolist(),
        "intercept": model.intercept_.tolist(),
        "notes": (
            "DUMMY-V0. Trained on Delcamp + placeholder advisor labels "
            "(see corpus/dummy_advisor_grades.csv). Not advisor-blessed. "
            "Replace dummy labels with real ones and retrain before "
            "treating these grades as anything but plumbing."
        ),
    }
    model_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with predictions_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "candidate_id", "source", "composer_normalized", "title",
            "actual_grade", "actual_grade_source",
            "predicted_grade", "model_version",
            *[f"p_G{c}" for c in classes],
        ])
        for i, r in enumerate(rows):
            cid = r["candidate_id"]
            actual = labels.get(cid, "")
            source = (
                "delcamp:guitarloot" if r.get("grade") else
                "dummy-advisor-v0" if cid in labels else ""
            )
            w.writerow([
                cid, r.get("source", ""),
                r.get("composer_normalized", ""), r.get("title", ""),
                actual, source,
                preds[i], MODEL_VERSION,
                *[f"{probs[i, j]:.3f}" for j in range(len(classes))],
            ])

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--dummy", type=Path, default=DEFAULT_DUMMY)
    parser.add_argument("--model-out", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--predictions-out", type=Path,
                        default=DEFAULT_PREDICTIONS)
    args = parser.parse_args()

    if not args.features.exists():
        print(f"Missing {args.features}. Run scripts/m2_features.py first.",
              file=sys.stderr)
        return 1

    payload = train_and_save(args.features, args.dummy,
                             args.model_out, args.predictions_out)
    print(f"==> Trained {MODEL_VERSION} on "
          f"{payload['trained_on']['labelled_rows']} labelled pieces")
    print(f"    In-sample exact: {payload['in_sample']['exact']:.1%}, "
          f"within ±1: {payload['in_sample']['within_one']:.1%}")
    print(f"==> Wrote model to {args.model_out}")
    print(f"==> Wrote predictions to {args.predictions_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
