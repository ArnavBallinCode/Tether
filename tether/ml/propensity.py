"""
models/propensity_model.py — load/predict wrapper (module-interfaces
contract: "models exposes PropensityModel.predict_proba(feature_vector) ->
float. Pure function, no DB access.").
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import joblib
import pandas as pd

DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "propensity_model.joblib"


class PropensityModel:
    """Loads a trained LightGBM S-learner (models/train.py) and scores a
    single feature vector. No DB access anywhere in this class -- the
    artifact bundles everything needed (model, categorical-column
    categories captured at training time, expected column order).
    """

    def __init__(self, artifact_path: Optional[Path] = None):
        artifact = joblib.load(artifact_path or DEFAULT_ARTIFACT_PATH)
        if isinstance(artifact, dict):
            self.model = artifact["model"]
            self.categories: dict[str, list] = artifact.get("categories", {})
            self.feature_columns: list[str] = artifact.get("feature_columns", [])
            self._used_fallback = False
        else:
            self.model = artifact
            self._used_fallback = True
            self.categories = {
                "segment": ["SMB", "Mid-Market", "Enterprise", "unknown"],
                "intervention_type": ["none", "soft_reminder", "firm_reminder", "channel_escalation", "plan_proposal", "human_escalation", "link_resend"]
            }
            # Fallback based on typical feature engine columns if not provided
            self.feature_columns = [
                "relative_lateness",
                "prs_score",
                "prs_trend",
                "dispute_rate",
                "response_rate",
                "partial_payment_rate",
                "amount_tier",
                "days_since_last_contact",
                "active_promise_flag",
                "days_until_promised_date",
                "broken_promise_streak",
                "segment",
                "intervention_type",
            ]

    def predict_proba(self, feature_vector: dict) -> float:
        """feature_vector must contain (at least) every key in
        FEATURE_COLUMNS (features/feature_engine.py). Extra keys are
        ignored; categorical columns are re-encoded against the exact
        category set seen at training time so an unseen category becomes a
        missing value to LightGBM rather than erroring.
        """
        row = {col: feature_vector[col] for col in self.feature_columns}
        df = pd.DataFrame([row])
        for col, cats in self.categories.items():
            cat_series = pd.Categorical(df[col], categories=cats)
            # If the artifact is just a raw model, it likely wants integers for categoricals
            # due to a lightgbm version mismatch or training setup.
            if getattr(self, "_used_fallback", False):
                df[col] = cat_series.codes
            else:
                df[col] = cat_series
        if "active_promise_flag" in df.columns:
            df["active_promise_flag"] = df["active_promise_flag"].astype(int)
        proba = self.model.predict_proba(df)[:, 1][0]
        return float(proba)
