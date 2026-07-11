import numpy as np
import pytest

from pin.collections import (
    LANDSAT_C2_L2,
    SENTINEL2_L2A,
    get_collection_spec,
)
from pin.pipeline import _indices_for_collection, compute_stats


def test_registry_lookup():
    s2 = get_collection_spec(SENTINEL2_L2A)
    assert s2.asset_for("red") == "B04"
    ls = get_collection_spec(LANDSAT_C2_L2)
    assert "lst" in ls.bands


def test_unknown_collection():
    with pytest.raises(KeyError):
        get_collection_spec("nope")


def test_indices_for_collection_sentinel_has_no_lst():
    s2 = get_collection_spec(SENTINEL2_L2A)
    usable = _indices_for_collection(s2.bands, ["ndvi", "ndmi", "ndwi", "lst"])
    assert "lst" not in usable
    assert "ndvi" in usable


def test_indices_for_collection_landsat_has_lst():
    ls = get_collection_spec(LANDSAT_C2_L2)
    usable = _indices_for_collection(ls.bands, ["ndvi", "lst"])
    assert "lst" in usable


class _FakeDA:
    """Minimal stand-in exposing a numpy ``.values`` like xarray.DataArray."""

    def __init__(self, values):
        self.values = np.asarray(values)


def test_compute_stats():
    da = _FakeDA([[0.2, 0.4], [np.nan, 0.6]])
    stats = compute_stats(da)
    assert stats["mean"] == pytest.approx(0.4)
    assert stats["min"] == pytest.approx(0.2)
    assert stats["max"] == pytest.approx(0.6)
    assert stats["valid_fraction"] == pytest.approx(0.75)


def test_compute_stats_all_nan():
    da = _FakeDA([np.nan, np.nan])
    stats = compute_stats(da)
    assert stats["mean"] is None
    assert stats["valid_fraction"] == 0.0
