import os
import pandas as pd

SCORES_PATH = "app/data/processed/scores_latest.csv"

def predict_needs(df=None):
    """Return a DataFrame with predictions.
    If df is provided, return df with 'score' if present; otherwise try to read the latest scores file.
    """
    if df is not None:
        # if score column already present, return as-is
        if "score" in df.columns:
            return df
        # else, try to merge by facility_id
        if os.path.exists(SCORES_PATH) and "facility_id" in df.columns:
            scores = pd.read_csv(SCORES_PATH)
            out = df.merge(scores[['facility_id','score','high_likelihood','active_posting','lat','lon']], on='facility_id', how='left')
            return out
        return df

    # No input df — try to return scores file
    if os.path.exists(SCORES_PATH):
        return pd.read_csv(SCORES_PATH)
    raise FileNotFoundError("Scores file not found and no input DataFrame provided")
