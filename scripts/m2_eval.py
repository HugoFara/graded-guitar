"""M2 Phase 2 — honest evaluation of the dummy-v0 grader.

Three eval cuts, written to `corpus/model_eval.md`:

1. **Stratified k-fold CV** on the union of Delcamp + dummy advisor
   labels. Reports exact-match and within-±1 accuracy at k=5.
2. **Per-era confusion** — bin the predictions by `_era_of(composer)`.
   Surfaces whether the model under-confidence on Modern repertoire
   (the corpus-coverage caveat from ADR 0009).
3. **Composer-out probe** — hold one prolific composer (e.g. Carcassi
   if present, else the largest single-composer group) completely out
   of training, then measure performance. This catches "the model
   memorised composer identity," which the label-bias finding flagged
   as the dominant failure mode of a Delcamp-only model.

Output is intentionally numeric and small — the advisor's role is to
react to the table, not to the implementation. Bias and dummy-label
caveats are spelled out at the top of the report.

Usage:
    python scripts/m2_eval.py
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold

from m1_common import REPO_ROOT
from m2_label_bias import _era_of
from m2_train import (
    NUMERIC_FEATURES,
    GRADE_CLASSES,
    _project_grade,
    featurize,
    load_labelled,
)


DEFAULT_FEATURES = REPO_ROOT / "corpus" / "features.csv"
DEFAULT_DUMMY = REPO_ROOT / "corpus" / "dummy_advisor_grades.csv"
DEFAULT_REPORT = REPO_ROOT / "corpus" / "model_eval.md"


def _new_model() -> LogisticRegression:
    return LogisticRegression(
        solver="lbfgs",
        class_weight="balanced",
        max_iter=2000,
        C=1.0,
        random_state=42,
    )


def _scale(X_train: np.ndarray, X_eval: np.ndarray
           ) -> tuple[np.ndarray, np.ndarray]:
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std[std == 0] = 1.0
    return (X_train - mean) / std, (X_eval - mean) / std


def _accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    exact = float(np.mean(y_true == y_pred))
    deltas = np.abs(y_true.astype(int) - y_pred.astype(int))
    within1 = float(np.mean(deltas <= 1))
    return exact, within1


def kfold_eval(X: np.ndarray, y: np.ndarray, k: int = 5) -> dict:
    """Stratified k-fold CV. Re-fits the scaler per fold."""
    # Drop classes with fewer than k samples — sklearn can't stratify.
    counts = Counter(y.tolist())
    keep_mask = np.array([counts[g] >= k for g in y])
    X_k = X[keep_mask]
    y_k = y[keep_mask]
    if len(y_k) < k:
        return {"exact": None, "within_one": None,
                "n": int(keep_mask.sum()), "dropped_classes":
                [g for g, c in counts.items() if c < k]}

    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=42)
    exacts, within1s = [], []
    for train_idx, test_idx in skf.split(X_k, y_k):
        Xtr, Xte = _scale(X_k[train_idx], X_k[test_idx])
        m = _new_model()
        m.fit(Xtr, y_k[train_idx])
        y_pred = m.predict(Xte)
        e, w = _accuracy(y_k[test_idx], y_pred)
        exacts.append(e)
        within1s.append(w)

    return {
        "exact": float(np.mean(exacts)),
        "within_one": float(np.mean(within1s)),
        "exact_std": float(np.std(exacts)),
        "n": int(keep_mask.sum()),
        "dropped_classes": [g for g, c in counts.items() if c < k],
    }


def per_era_breakdown(X: np.ndarray, y: np.ndarray,
                     eras: list[str]) -> dict[str, dict]:
    """Train once on all labelled, score per-era on in-sample data.

    In-sample, so optimistic — but useful for spotting eras where the
    model never converges on a band (e.g. Modern with n=1 will be a
    coin flip).
    """
    Xtr, _ = _scale(X, X)
    m = _new_model()
    m.fit(Xtr, y)
    pred = m.predict(Xtr)
    by_era: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for era, t, p in zip(eras, y, pred):
        by_era[era].append((t, p))

    out: dict[str, dict] = {}
    for era, pairs in by_era.items():
        ys = np.array([t for t, _ in pairs])
        ps = np.array([p for _, p in pairs])
        e, w = _accuracy(ys, ps)
        out[era] = {
            "n": len(pairs),
            "exact": e,
            "within_one": w,
            "predicted_distribution": dict(Counter(ps.tolist())),
        }
    return out


def composer_out_probe(X: np.ndarray, y: np.ndarray,
                       composers: list[str]) -> dict:
    """Hold the largest single-composer group out and report accuracy.

    Picks the most-frequent composer with ≥10 examples. If none qualify
    the probe returns {"skipped": True, ...}.
    """
    counts = Counter(composers)
    candidates = [(c, n) for c, n in counts.most_common() if n >= 10]
    if not candidates:
        return {"skipped": True, "reason": "no composer with ≥10 examples"}
    held_out, n = candidates[0]

    is_held = np.array([c == held_out for c in composers])
    Xtr, Xte = _scale(X[~is_held], X[is_held])
    m = _new_model()
    m.fit(Xtr, y[~is_held])
    pred = m.predict(Xte)
    e, w = _accuracy(y[is_held], pred)

    truth = Counter(y[is_held].tolist())
    pred_dist = Counter(pred.tolist())
    return {
        "held_out_composer": held_out,
        "n": int(is_held.sum()),
        "exact": e,
        "within_one": w,
        "truth_distribution": dict(truth),
        "predicted_distribution": dict(pred_dist),
    }


def render_report(kfold: dict, per_era: dict, comp_out: dict,
                  delcamp_n: int, dummy_n: int) -> str:
    lines: list[str] = []
    lines.append("# M2 dummy-v0 — evaluation")
    lines.append("")
    lines.append(
        "**Dummy data warning.** Every label backing this evaluation "
        "is either a Delcamp grade (composer-confounded, see "
        "`corpus/label_bias.md`) or a placeholder generated by "
        "`scripts/m2_dummy_advisor.py`. Numbers below describe how "
        "well the pipeline learns to reproduce *those labels*, not "
        "how well it grades difficulty. Replace the dummy labels and "
        "re-run before treating any of this as a metric."
    )
    lines.append("")
    lines.append(f"- Delcamp-labelled rows: **{delcamp_n}**")
    lines.append(f"- Dummy-advisor rows: **{dummy_n}**")
    lines.append(f"- Total labelled: **{delcamp_n + dummy_n}**")
    lines.append("")
    lines.append("## 1. 5-fold stratified CV")
    lines.append("")
    if kfold["exact"] is None:
        lines.append(f"Skipped: too few examples in some classes "
                     f"({', '.join(kfold['dropped_classes'])}).")
    else:
        lines.append(f"- **Exact match:** {kfold['exact']:.1%} "
                     f"(±{kfold['exact_std']:.1%})")
        lines.append(f"- **Within ±1:** {kfold['within_one']:.1%}")
        lines.append(f"- N (after dropping sparse classes): {kfold['n']}")
        if kfold["dropped_classes"]:
            lines.append(f"- Dropped classes (n<5): "
                         f"`{', '.join(kfold['dropped_classes'])}`")
    lines.append("")
    lines.append("Spec §7 mandates ≥70% within-±1 on holdout before M2 "
                 "can close. This number is informative for the pipeline "
                 "but not authoritative — the labels themselves aren't.")
    lines.append("")
    lines.append("## 2. Per-era breakdown (in-sample)")
    lines.append("")
    lines.append("| era | n | exact | within ±1 | predicted bands |")
    lines.append("| --- | --- | --- | --- | --- |")
    for era in sorted(per_era):
        d = per_era[era]
        dist = ", ".join(f"G{g}:{n}" for g, n
                         in sorted(d["predicted_distribution"].items()))
        lines.append(f"| {era} | {d['n']} | {d['exact']:.0%} | "
                     f"{d['within_one']:.0%} | {dist} |")
    lines.append("")
    lines.append("Eras with n<5 are statistically meaningless; they're "
                 "listed for completeness. The Modern row in particular "
                 "is one example, by construction.")
    lines.append("")
    lines.append("## 3. Composer-out probe")
    lines.append("")
    if comp_out.get("skipped"):
        lines.append(f"Skipped: {comp_out['reason']}.")
    else:
        lines.append(f"- **Held-out composer:** `{comp_out['held_out_composer']}` "
                     f"(n={comp_out['n']})")
        lines.append(f"- **Exact match:** {comp_out['exact']:.1%}")
        lines.append(f"- **Within ±1:** {comp_out['within_one']:.1%}")
        truth_dist = ", ".join(f"G{g}:{n}" for g, n
                               in sorted(comp_out['truth_distribution'].items()))
        pred_dist = ", ".join(f"G{g}:{n}" for g, n
                              in sorted(comp_out['predicted_distribution'].items()))
        lines.append(f"- Truth distribution: {truth_dist}")
        lines.append(f"- Predicted distribution: {pred_dist}")
        lines.append("")
        lines.append("Per `corpus/label_bias.md`, 123 of 124 graded composers "
                     "sit at a single Delcamp grade. Holding one composer out "
                     "of training is therefore close to holding out an entire "
                     "label band. A large gap between in-sample exact and the "
                     "composer-out exact is the expected failure mode.")
    lines.append("")
    lines.append("## What's missing from this report")
    lines.append("")
    lines.append("- Real test-set holdout. With ~480 labelled rows, "
                 "5-fold CV is the honest split; a held-out test set "
                 "shrinks the train set below LR's noise floor here.")
    lines.append("- Spec §7's 50-piece advisor plausibility check. "
                 "That's a human eval and lives in the advisor "
                 "engagement (ADR 0004, ADR 0010), not here.")
    lines.append("- Calibration plot. Deferred to post-advisor work — "
                 "calibrating a dummy classifier against dummy labels "
                 "is theatre.")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=DEFAULT_FEATURES)
    parser.add_argument("--dummy", type=Path, default=DEFAULT_DUMMY)
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    rows, labels = load_labelled(args.features, args.dummy)
    X_all, _ = featurize(rows)

    labelled_idx: list[int] = []
    y_raw: list[str] = []
    composers: list[str] = []
    eras: list[str] = []
    delcamp_n = 0
    dummy_n = 0
    for i, r in enumerate(rows):
        cid = r["candidate_id"]
        if cid not in labels:
            continue
        labelled_idx.append(i)
        y_raw.append(_project_grade(labels[cid]))
        composers.append(r.get("composer_normalized", "") or "Unknown")
        eras.append(_era_of(r.get("composer_normalized", "") or ""))
        if r.get("grade"):
            delcamp_n += 1
        else:
            dummy_n += 1

    X = X_all[labelled_idx]
    y = np.array(y_raw)

    kfold = kfold_eval(X, y, k=5)
    per_era = per_era_breakdown(X, y, eras)
    comp_out = composer_out_probe(X, y, composers)

    report = render_report(kfold, per_era, comp_out, delcamp_n, dummy_n)
    args.out.write_text(report, encoding="utf-8")
    print(f"==> Wrote {args.out}")
    if kfold["exact"] is not None:
        print(f"    5-fold exact: {kfold['exact']:.1%} | "
              f"within ±1: {kfold['within_one']:.1%}")
    if not comp_out.get("skipped"):
        print(f"    Held-out {comp_out['held_out_composer']}: "
              f"exact {comp_out['exact']:.1%}, "
              f"within ±1 {comp_out['within_one']:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
