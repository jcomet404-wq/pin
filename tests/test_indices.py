import numpy as np
import pytest

from pin.indices import (
    available_indices,
    compute_index,
    lst_celsius,
    ndmi,
    ndvi,
    ndwi,
    normalized_difference,
)


def test_normalized_difference_basic():
    a = np.array([1.0, 2.0, 0.0])
    b = np.array([0.0, 2.0, 0.0])
    result = normalized_difference(a, b)
    assert result[0] == pytest.approx(1.0)
    assert result[1] == pytest.approx(0.0)
    # 0/0 -> NaN, not inf
    assert np.isnan(result[2])


def test_ndvi_range():
    nir = np.array([0.4, 0.5])
    red = np.array([0.1, 0.5])
    result = ndvi(nir, red)
    assert result[0] == pytest.approx((0.4 - 0.1) / (0.4 + 0.1))
    assert result[1] == pytest.approx(0.0)
    assert np.all((result >= -1) & (result <= 1))


def test_ndmi_and_ndwi_are_normalized_differences():
    nir = np.array([0.4])
    swir = np.array([0.2])
    green = np.array([0.3])
    assert ndmi(nir, swir)[0] == pytest.approx(normalized_difference(nir, swir)[0])
    assert ndwi(green, nir)[0] == pytest.approx(normalized_difference(green, nir)[0])


def test_lst_celsius():
    kelvin = np.array([273.15, 300.0])
    c = lst_celsius(kelvin)
    assert c[0] == pytest.approx(0.0)
    assert c[1] == pytest.approx(26.85)


def test_compute_index_dispatch():
    bands = {"nir": np.array([0.4]), "red": np.array([0.1])}
    assert compute_index("ndvi", bands)[0] == pytest.approx(0.6)


def test_compute_index_missing_band():
    with pytest.raises(KeyError):
        compute_index("ndvi", {"nir": np.array([0.4])})


def test_compute_index_unknown():
    with pytest.raises(KeyError):
        compute_index("nope", {})


def test_available_indices():
    assert set(available_indices()) == {"ndvi", "ndmi", "ndwi", "lst"}
