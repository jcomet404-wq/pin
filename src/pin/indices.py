"""Spectral index calculations.

The functions here are deliberately array-library agnostic: they operate on
anything that supports element-wise arithmetic, so they work with plain NumPy
arrays (handy for unit tests) as well as :class:`xarray.DataArray` objects
(which carry geospatial coordinates through the computation).

Inputs are expected to be in physical units (surface reflectance in ``0..1``
for the optical bands, Kelvin for thermal), i.e. any scale/offset has already
been applied by the loader.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

import numpy as np


class ArrayLike(Protocol):
    """Anything supporting the element-wise arithmetic used below.

    Satisfied by both :class:`numpy.ndarray` and :class:`xarray.DataArray`, so
    the same functions serve unit tests (NumPy) and the pipeline (xarray).
    """

    def __add__(self, other: Any) -> ArrayLike: ...
    def __sub__(self, other: Any) -> ArrayLike: ...
    def __truediv__(self, other: Any) -> ArrayLike: ...


KELVIN_TO_CELSIUS = 273.15


def _mask_zero_denominator(result: Any, denominator: Any) -> ArrayLike:
    """Set positions where ``denominator == 0`` to NaN, preserving array type."""
    if hasattr(result, "where"):  # xarray.DataArray
        return result.where(denominator != 0)
    return np.where(denominator != 0, result, np.nan)


def normalized_difference(a: ArrayLike, b: ArrayLike) -> ArrayLike:
    """Generic normalized difference ``(a - b) / (a + b)``.

    Positions where ``a + b == 0`` are returned as NaN rather than raising or
    producing infinities.
    """
    denominator = a + b
    with np.errstate(divide="ignore", invalid="ignore"):
        result = (a - b) / denominator
    return _mask_zero_denominator(result, denominator)


def ndvi(nir: ArrayLike, red: ArrayLike) -> ArrayLike:
    """Normalized Difference Vegetation Index — vegetation density/greenness."""
    return normalized_difference(nir, red)


def ndmi(nir: ArrayLike, swir: ArrayLike) -> ArrayLike:
    """Normalized Difference Moisture Index — vegetation/canopy water content."""
    return normalized_difference(nir, swir)


def ndwi(green: ArrayLike, nir: ArrayLike) -> ArrayLike:
    """McFeeters Normalized Difference Water Index — open-water extent."""
    return normalized_difference(green, nir)


def lst_celsius(thermal_kelvin: ArrayLike) -> ArrayLike:
    """Convert a land-surface-temperature band from Kelvin to Celsius."""
    return thermal_kelvin - KELVIN_TO_CELSIUS


#: Which logical bands each index consumes, in call order.
INDEX_INPUTS: dict[str, tuple[str, ...]] = {
    "ndvi": ("nir", "red"),
    "ndmi": ("nir", "swir"),
    "ndwi": ("green", "nir"),
    "lst": ("lst",),
}

#: Mapping from index name to the function implementing it.
INDEX_FUNCS: dict[str, Callable[..., ArrayLike]] = {
    "ndvi": ndvi,
    "ndmi": ndmi,
    "ndwi": ndwi,
    "lst": lst_celsius,
}


def available_indices() -> list[str]:
    return list(INDEX_FUNCS)


def compute_index(name: str, bands: dict[str, Any]) -> ArrayLike:
    """Compute a named index from a mapping of logical band role -> array."""
    if name not in INDEX_FUNCS:
        raise KeyError(f"Unknown index {name!r}. Available: {available_indices()}")
    required = INDEX_INPUTS[name]
    missing = [r for r in required if r not in bands]
    if missing:
        raise KeyError(f"Index {name!r} needs band(s) {missing} which are not available")
    args = [bands[r] for r in required]
    return INDEX_FUNCS[name](*args)
