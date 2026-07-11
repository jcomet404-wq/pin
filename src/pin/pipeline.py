"""End-to-end orchestration: search → load → index → store."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pin.collections import get_collection_spec
from pin.config import PinConfig
from pin.indices import INDEX_INPUTS, compute_index
from pin.load import load_scene
from pin.search import CLOUD_COVER_PROP, search_collection
from pin.storage import StatRecord, Storage, get_storage

if TYPE_CHECKING:  # pragma: no cover - typing only
    import xarray as xr
    from pystac import Item

logger = logging.getLogger(__name__)


def compute_stats(da: xr.DataArray) -> dict[str, float | None]:
    """Reduce a 2-D index raster to scalar summary statistics."""
    import numpy as np

    values = np.asarray(da.values, dtype="float64")
    total = values.size
    finite = np.isfinite(values)
    n_valid = int(finite.sum())
    if n_valid == 0:
        return {
            "mean": None, "min": None, "max": None, "std": None, "valid_fraction": 0.0
        }
    valid = values[finite]
    return {
        "mean": float(valid.mean()),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "std": float(valid.std()),
        "valid_fraction": n_valid / total if total else 0.0,
    }


def _indices_for_collection(spec_bands: dict[str, Any], requested: list[str]) -> list[str]:
    usable = []
    for name in requested:
        needed = INDEX_INPUTS.get(name)
        if needed is None:
            logger.warning("Ignoring unknown index %r", name)
            continue
        if all(role in spec_bands for role in needed):
            usable.append(name)
        else:
            logger.info("Collection lacks bands for index %r; skipping", name)
    return usable


def process_item(
    item: Item,
    collection: str,
    config: PinConfig,
    storage: Storage,
) -> list[StatRecord]:
    """Compute and persist every applicable index for a single scene."""
    spec = get_collection_spec(collection)
    indices = _indices_for_collection(spec.bands, config.indices)
    if not indices:
        return []

    roles = sorted({r for name in indices for r in INDEX_INPUTS[name]})
    ds = load_scene(
        item, spec, roles, bbox=config.bbox, resolution=config.resolution
    )
    bands = {role: ds[role] for role in roles}

    dt = item.datetime.isoformat() if item.datetime else None
    cloud = item.properties.get(CLOUD_COVER_PROP)

    records: list[StatRecord] = []
    for name in indices:
        result: Any = compute_index(name, bands)
        result = result.rio.write_crs(ds[roles[0]].rio.crs, inplace=False)
        relpath = f"{collection}/{name}/{item.id}_{name}.tif"
        uri = storage.write_raster(result, relpath)
        stats = compute_stats(result)
        records.append(
            StatRecord(
                collection=collection,
                item_id=item.id,
                index_name=name,
                datetime=dt,
                cloud_cover=float(cloud) if cloud is not None else None,
                raster_uri=uri,
                mean=stats["mean"],
                min=stats["min"],
                max=stats["max"],
                std=stats["std"],
                valid_fraction=stats["valid_fraction"],
            )
        )
    logger.info("Processed %s: %d index raster(s)", item.id, len(records))
    return records


def run(config: PinConfig, *, sign: bool = True) -> list[StatRecord]:
    """Run the full pipeline for every collection and return all stat records."""
    storage = get_storage(config)
    all_records: list[StatRecord] = []
    for collection in config.collections:
        items = search_collection(config, collection, sign=sign)
        for item in items:
            try:
                records = process_item(item, collection, config, storage)
            except Exception:  # noqa: BLE001 - keep going on a bad scene
                logger.exception("Failed to process %s", item.id)
                continue
            storage.write_stats(records)
            all_records.extend(records)

    if config.population is not None:
        from pin.population import run_population

        all_records.extend(run_population(config, storage))

    logger.info("Run complete: %d record(s)", len(all_records))
    return all_records
