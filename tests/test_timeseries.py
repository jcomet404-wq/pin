import pandas as pd

from pin.timeseries import aggregate, summary, time_series


def sample_df():
    return pd.DataFrame(
        [
            {"collection": "s2", "index_name": "ndvi", "datetime": "2023-01-05T00:00:00Z",
             "mean": 0.5, "cloud_cover": 3.0},
            {"collection": "s2", "index_name": "ndvi", "datetime": "2023-01-20T00:00:00Z",
             "mean": 0.7, "cloud_cover": 5.0},
            {"collection": "s2", "index_name": "ndvi", "datetime": "2023-02-10T00:00:00Z",
             "mean": 0.6, "cloud_cover": 2.0},
            {"collection": "s2", "index_name": "ndmi", "datetime": "2023-01-05T00:00:00Z",
             "mean": 0.1, "cloud_cover": 3.0},
        ]
    )


def test_time_series_filter_and_order():
    ts = time_series(sample_df(), index_name="ndvi")
    assert list(ts["index_name"].unique()) == ["ndvi"]
    assert ts["datetime"].is_monotonic_increasing
    assert len(ts) == 3


def test_aggregate_monthly():
    agg = aggregate(sample_df(), freq="MS")
    ndvi_rows = agg[agg["index_name"] == "ndvi"]
    assert len(ndvi_rows) == 2  # Jan and Feb
    jan = ndvi_rows.iloc[0]
    assert jan["count"] == 2
    assert jan["mean"] == 0.6  # (0.5 + 0.7) / 2


def test_summary():
    s = summary(sample_df())
    ndvi = s[s["index_name"] == "ndvi"].iloc[0]
    assert ndvi["count"] == 3
    assert ndvi["min"] == 0.5
    assert ndvi["max"] == 0.7


def test_invalid_datetime_dropped():
    df = sample_df()
    df.loc[0, "datetime"] = "not-a-date"
    ts = time_series(df, index_name="ndvi")
    assert len(ts) == 2
