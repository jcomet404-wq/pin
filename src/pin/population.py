"""Population tracking over time from WorldPop gridded population counts.

WorldPop (https://www.worldpop.org) publishes open, global, annual gridded
population estimates for 2000-2020. They are *not* hosted on Planetary Computer,
so PIN downloads the per-country GeoTIFFs directly. For a bounding box we clip
the national raster and record the total population (sum of counts) and areal
density per year, which then flows into the same retrospective time series as
the spectral indices.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING

from pin.config import PinConfig, PopulationConfig
from pin.storage import StatRecord, Storage

if TYPE_CHECKING:  # pragma: no cover - typing only
    import xarray as xr

logger = logging.getLogger(__name__)

WORLDPOP_MIN_YEAR = 2000
WORLDPOP_MAX_YEAR = 2020

_URL_100M = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020/"
    "{year}/{iso3}/{iso3_lower}_ppp_{year}.tif"
)
_URL_1KM = (
    "https://data.worldpop.org/GIS/Population/Global_2000_2020_1km/"
    "{year}/{iso3}/{iso3_lower}_ppp_{year}_1km_Aggregated.tif"
)


def years_from_datetime(datetime_range: str) -> list[int]:
    """Extract the inclusive span of calendar years from a STAC datetime range."""
    start, _, end = datetime_range.partition("/")
    start_year = int(start[:4])
    end_year = int((end or start)[:4])
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    return list(range(start_year, end_year + 1))


def resolve_years(pop: PopulationConfig, config: PinConfig) -> list[int]:
    """Determine which years to fetch, clamped to WorldPop's coverage."""
    years = pop.years if pop.years else years_from_datetime(config.datetime)
    clamped = [y for y in years if WORLDPOP_MIN_YEAR <= y <= WORLDPOP_MAX_YEAR]
    dropped = sorted(set(years) - set(clamped))
    if dropped:
        logger.warning(
            "WorldPop covers %d-%d; skipping out-of-range year(s): %s",
            WORLDPOP_MIN_YEAR, WORLDPOP_MAX_YEAR, dropped,
        )
    return sorted(set(clamped))


def build_url(pop: PopulationConfig, year: int) -> str:
    template = pop.url_template or (_URL_1KM if pop.resolution == "1km" else _URL_100M)
    return template.format(iso3=pop.iso3, iso3_lower=pop.iso3.lower(), year=year)


def download(url: str, cache_dir: str | Path) -> Path:
    """Download ``url`` into ``cache_dir`` (skipping if already cached)."""
    import requests

    cache = Path(cache_dir).expanduser()
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / url.rsplit("/", 1)[-1]
    if dest.exists() and dest.stat().st_size > 0:
        logger.debug("Using cached %s", dest)
        return dest
    logger.info("Downloading %s", url)
    with requests.get(url, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        tmp.rename(dest)
    return dest


def bbox_area_km2(bbox: list[float]) -> float:
    """Approximate the area of a lon/lat bounding box in square kilometres."""
    min_lon, min_lat, max_lon, max_lat = bbox
    mean_lat = math.radians((min_lat + max_lat) / 2)
    height_km = (max_lat - min_lat) * 111.32
    width_km = (max_lon - min_lon) * 111.32 * math.cos(mean_lat)
    return abs(height_km * width_km)


def clip_population(path: str | Path, bbox: list[float]) -> xr.DataArray:
    """Open a WorldPop raster and clip it to ``bbox`` (masked nodata)."""
    import rioxarray
    import xarray as xr

    da = rioxarray.open_rasterio(path, masked=True)
    if not isinstance(da, xr.DataArray):
        raise TypeError(f"Expected a single-band raster at {path}")
    clipped = da.rio.clip_box(
        minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3]
    )
    return clipped.squeeze()


def run_population(config: PinConfig, storage: Storage) -> list[StatRecord]:
    """Fetch, clip and summarise WorldPop population for each requested year."""
    import numpy as np

    pop = config.population
    if pop is None:
        return []
    if pop.source != "worldpop":
        raise ValueError(f"Unsupported population source: {pop.source!r}")

    area_km2 = bbox_area_km2(config.bbox)
    collection = f"worldpop-{pop.resolution}"
    records: list[StatRecord] = []
    for year in resolve_years(pop, config):
        url = build_url(pop, year)
        try:
            path = download(url, pop.cache_dir)
            da = clip_population(path, config.bbox)
        except Exception:  # noqa: BLE001 - keep going on a bad year
            logger.exception("Failed to fetch population for %s %d", pop.iso3, year)
            continue

        values = np.asarray(da.values, dtype="float64")
        finite = np.isfinite(values)
        total = float(values[finite].sum()) if finite.any() else 0.0
        uri = storage.write_raster(da, f"{collection}/population/{pop.iso3}_{year}.tif")
        records.append(
            StatRecord(
                collection=collection,
                item_id=f"{pop.iso3}_{year}",
                index_name="population",
                datetime=f"{year}-01-01T00:00:00+00:00",
                total=total,
                mean=total / area_km2 if area_km2 else None,  # people / km^2
                min=float(values[finite].min()) if finite.any() else None,
                max=float(values[finite].max()) if finite.any() else None,
                std=float(values[finite].std()) if finite.any() else None,
                valid_fraction=(int(finite.sum()) / values.size) if values.size else 0.0,
                raster_uri=uri,
            )
        )
        logger.info("Population %s %d: total=%.0f", pop.iso3, year, total)
    storage.write_stats(records)
    return records
