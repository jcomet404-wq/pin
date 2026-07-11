"""Retrospective, over-time analysis of stored index statistics.

These helpers operate on the tidy stats table produced by the storage layer
(one row per collection/scene/index) and turn it into time series and
temporally-aggregated summaries — the "view of maps over time" for an area.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd


def _prepare(df: pd.DataFrame) -> pd.DataFrame:
    import pandas as pd

    out = df.copy()
    out["datetime"] = pd.to_datetime(out["datetime"], utc=True, errors="coerce")
    return out.dropna(subset=["datetime"]).sort_values("datetime")


def time_series(df: pd.DataFrame, index_name: str | None = None) -> pd.DataFrame:
    """Return per-scene mean values ordered in time.

    If ``index_name`` is given the result is filtered to that index.
    """
    out = _prepare(df)
    if index_name is not None:
        out = out[out["index_name"] == index_name]
    cols = ["datetime", "collection", "index_name", "mean", "cloud_cover"]
    return out[cols].reset_index(drop=True)


def aggregate(df: pd.DataFrame, freq: str = "MS") -> pd.DataFrame:
    """Temporally aggregate mean values per collection/index at ``freq``.

    ``freq`` is any pandas offset alias (``"MS"`` month-start, ``"W"`` weekly,
    ``"YS"`` yearly …). Returns mean and standard deviation of scene means in
    each bucket.
    """
    out = _prepare(df)
    grouped = (
        out.set_index("datetime")
        .groupby(["collection", "index_name"])["mean"]
        .resample(freq)
        .agg(["mean", "std", "count"])
        .reset_index()
    )
    return grouped.dropna(subset=["mean"]).reset_index(drop=True)


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Overall average of each index across the whole period, per collection."""
    out = _prepare(df)
    return (
        out.groupby(["collection", "index_name"])["mean"]
        .agg(["mean", "min", "max", "std", "count"])
        .reset_index()
    )
