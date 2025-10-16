import os
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from datetime import datetime

# -------- Paths (edit only if my repo differs) --------
DATA_PATH = "app/data/processed/facility_features.csv"
SCORES_OUT = "app/data/processed/scores_latest.csv"
MODEL_OUT = "app/models/predictor_logit.json"

# -------- Thresholds --------
# Global default; can be overridden via env:
DEFAULT_RED_THRESHOLD = float(os.environ.get("RED_THRESHOLD", "0.70"))

# Optional per-specialty overrides via env:
#   RED_THRESHOLD_HO=0.68
#   RED_THRESHOLD_PDH=0.72
RED_THRESHOLD_HO = os.environ.get("RED_THRESHOLD_HO")
RED_THRESHOLD_PDH = os.environ.get("RED_THRESHOLD_PDH")

FEATURE_CANDIDATES = [
    "postings_90d", "postings_365d", "last_post_days",
    "competitor_postings_30d", "census_index", "seasonality_index",
    "turnover_index", "credentialing_days", "beds"
]

def _safe_num(x):
    """Convert text ranges like '16-18' -> 17; leave numbers as float; NaNs -> np.nan."""
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    if "-" in s:
        try:
            parts = [float(p) for p in s.split("-") if p.strip() != ""]
            return float(np.mean(parts)) if parts else np.nan
        except:
            return np.nan
    try:
        return float(s)
    except:
        return np.nan

def build_matrix(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame()
    for col in FEATURE_CANDIDATES:
        if col in df.columns:
            X[col] = df[col].apply(_safe_num)
        else:
            X[col] = 0.0

    # Recency helper boosts recent activity
    if "last_post_days" in X.columns:
        X["recency_1_over"] = 1.0 / (1.0 + X["last_post_days"].fillna(999))
    else:
        X["recency_1_over"] = 0.0

    # Fill remaining NaNs and add intercept
    X = X.fillna(0.0)
    X = sm.add_constant(X, has_constant="add")
    return X

def heuristic_score(df: pd.DataFrame) -> pd.Series:
    """Fallback 0..1 score when no labels are available."""
    X = build_matrix(df)
    w = {
        "const": 0.00,
        "postings_90d": 0.22,
        "postings_365d": 0.10,
        "recency_1_over": 0.25,
        "competitor_postings_30d": 0.18,
        "census_index": 0.10,
        "seasonality_index": 0.10,
        "turnover_index": 0.08,
        "credentialing_days": -0.04,
        "beds": 0.03
    }
    lin = (
        w["const"]
        + w["postings_90d"] * X["postings_90d"]
        + w["postings_365d"] * X["postings_365d"]
        + w["recency_1_over"] * X["recency_1_over"]
        + w["competitor_postings_30d"] * X["competitor_postings_30d"]
        + w["census_index"] * X["census_index"]
        + w["seasonality_index"] * X["seasonality_index"]
        + w["turnover_index"] * X["turnover_index"]
        + w["credentialing_days"] * X["credentialing_days"]
        + w["beds"] * X["beds"]
    )

    # Normalize to 0..1
    lin = (lin - lin.min()) / (lin.max() - lin.min() + 1e-9)
    return lin.clip(0, 1)

def fit_logit(df: pd.DataFrame, y_col: str):
    X = build_matrix(df)
    y = df[y_col].astype(float).clip(0,1)
    if y.nunique() < 2:
        return None, None
    model = sm.Logit(y, X).fit(disp=False)
    proba = model.predict(X)
    coefs = dict(model.params)
    return proba, coefs

def apply_coefs(df: pd.DataFrame, coefs: dict) -> pd.Series:
    X = build_matrix(df)
    z = 0.0
    for k, v in coefs.items():
        if k in X.columns:
            z += X[k] * float(v)
    return 1 / (1 + np.exp(-z))

def _threshold_for_spec(spec: str) -> float:
    if spec == "HO" and RED_THRESHOLD_HO is not None:
        try: return float(RED_THRESHOLD_HO)
        except: pass
    if spec == "PDH" and RED_THRESHOLD_PDH is not None:
        try: return float(RED_THRESHOLD_PDH)
        except: pass
    return DEFAULT_RED_THRESHOLD

def main():
    # Ensure output dirs exist
    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    os.makedirs(os.path.dirname(SCORES_OUT), exist_ok=True)

    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Missing features file: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    # Try to find a label column for supervised training
    label_col = next((c for c in ["had_locum_next_45d", "need_within_45d", "need_within_30d"] if c in df.columns), None)

    if label_col:
        print(f"[train] Using supervised label: {label_col}")
        proba, coefs = fit_logit(df, label_col)
        if proba is None:
            print("[train] Not enough label variation; falling back to heuristic.")
            score = heuristic_score(df)
            coefs = None
        else:
            score = proba.clip(0,1)
            with open(MODEL_OUT, "w") as f:
                json.dump({
                    "trained_at": datetime.utcnow().isoformat(),
                    "label_col": label_col,
                    "coefficients": coefs
                }, f, indent=2)
    else:
        print("[train] No label column; using heuristic scoring.")
        score = heuristic_score(df)

    df_out = df.copy()
    df_out["score"] = score.round(4)

    # High-likelihood flag per specialty threshold
    df_out["high_likelihood"] = [
        float(s) >= _threshold_for_spec(str(spc))
        for s, spc in zip(df_out["score"], df_out.get("specialty", "HO"))
    ]

    # Keep active_posting as-is if present; otherwise default False
    if "active_posting" not in df_out.columns:
        df_out["active_posting"] = False

    # Export scored table
    df_out.to_csv(SCORES_OUT, index=False)
    print(f"[train] Wrote scores  {SCORES_OUT}")

    # Show preview
    prev = (
        df_out.sort_values(["specialty","score"], ascending=[True, False])
        [["facility_name","state","specialty","score","high_likelihood"]]
        .head(10)
    )
    print(prev.to_string(index=False))

if __name__ == "__main__":
    main()
