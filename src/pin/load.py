"""Turn STAC items into analysis-ready xarray data in physical units."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import rioxarray  # noqa: F401  # registers the .rio accessor used downstream

from pin.collections import CollectionSpec

if TYPE_CHECKING:  # pragma: no cover - typing only
    import xarray as xr
    from pystac import Item

logger = logging.getLogger(__name__)


def _apply_scale_offset(da: xr.DataArray, scale: float | None, offset: float | None):
    if scale is not None:
        da = da * scale
    if offset is not None:
        da = da + offset
    return da


def load_scene(
    item: Item,
    spec: CollectionSpec,
    roles: list[str],
    *,
    bbox: list[float],
    resolution: float,
) -> xr.Dataset:
    """Load the requested logical bands for a single item in physical units.

    Returns a :class:`xarray.Dataset` whose variables are the logical band
    roles (``red``, ``nir`` …) with scale/offset applied and nodata masked.
    """
    from odc.stac import stac_load

    assets = spec.assets_for(roles)
    ds = stac_load(
        [item],
        bands=assets,
        bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
        resolution=resolution,
        chunks={},  # dask-backed lazy load
        groupby=None,
    )
    # Collapse the singleton time dimension introduced by stac_load.
    if "time" in ds.dims:
        ds = ds.isel(time=0, drop=True)

    out = {}
    for role in roles:
        band = spec.bands[role]
        da = ds[band.asset]
        da = da.where(da != 0) if band.asset.startswith("B") else da
        da = _apply_scale_offset(da.astype("float32"), band.scale, band.offset)
        da.attrs["role"] = role
        out[role] = da

    import xarray as xr

    dataset = xr.Dataset(out)
    dataset.attrs["item_id"] = item.id
    dataset.attrs["collection"] = spec.name
    return dataset
