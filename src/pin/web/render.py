"""Render colorized index overlays for the web map.

Takes a region of interest (lon/lat bbox) plus an index name, runs the PIN
pipeline for the least-cloudy scene, reprojects the result to EPSG:4326 (what
Leaflet's image overlay expects) and colorizes it to a PNG with a matplotlib
colormap. Also renders standalone colorbar legends.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pin.collections import get_collection_spec
from pin.config import PinConfig, PopulationConfig
from pin.indices import INDEX_INPUTS, compute_index

if TYPE_CHECKING:  # pragma: no cover - typing only
    import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexStyle:
    """Colormap + fixed value range used to render an index consistently."""

    cmap: str
    vmin: float
    vmax: float
    label: str
    collection: str


# Fixed styling so the same colours mean the same thing across regions/dates.
STYLES: dict[str, IndexStyle] = {
    "ndvi": IndexStyle("RdYlGn", -0.2, 0.9, "NDVI (vegetation)", "sentinel-2-l2a"),
    "ndmi": IndexStyle("BrBG", -0.5, 0.5, "NDMI (moisture)", "sentinel-2-l2a"),
    "ndwi": IndexStyle("RdBu", -0.5, 0.6, "NDWI (water)", "sentinel-2-l2a"),
    "lst": IndexStyle("inferno", 0.0, 50.0, "LST (°C)", "landsat-c2-l2"),
    "population": IndexStyle("magma", 0.0, 500.0, "Population (people/pixel)", "worldpop-1km"),
}


def available_styles() -> dict[str, dict[str, object]]:
    return {
        name: {"cmap": s.cmap, "vmin": s.vmin, "vmax": s.vmax, "label": s.label}
        for name, s in STYLES.items()
    }


def _colorize(arr: np.ndarray, style: IndexStyle) -> bytes:
    import matplotlib
    import numpy as np
    from PIL import Image

    norm = matplotlib.colors.Normalize(vmin=style.vmin, vmax=style.vmax, clip=True)
    cmap = matplotlib.colormaps[style.cmap]
    rgba = cmap(norm(np.ma.masked_invalid(arr)))
    rgba[..., 3] = np.where(np.isfinite(arr), 1.0, 0.0)  # transparent nodata
    img = (rgba * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(img, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()


def _reproject_4326(da):
    if str(da.rio.crs).upper() != "EPSG:4326":
        da = da.rio.reproject("EPSG:4326")
    return da


def _bounds_latlon(da) -> list[list[float]]:
    minx, miny, maxx, maxy = da.rio.bounds()
    return [[float(miny), float(minx)], [float(maxy), float(maxx)]]


def _finite_stats(arr: np.ndarray) -> dict[str, float | None]:
    import numpy as np

    finite = np.isfinite(arr)
    if not finite.any():
        return {"mean": None, "min": None, "max": None}
    v = arr[finite]
    return {"mean": float(v.mean()), "min": float(v.min()), "max": float(v.max())}


def render_index(
    index: str,
    bbox: list[float],
    datetime: str,
    *,
    resolution: float = 60.0,
    max_cloud_cover: float = 30.0,
    iso3: str | None = None,
    year: int | None = None,
) -> dict:
    """Compute and colorize ``index`` over ``bbox``; return PNG + overlay metadata."""
    import numpy as np

    if index not in STYLES:
        raise KeyError(f"Unknown index {index!r}. Available: {sorted(STYLES)}")
    style = STYLES[index]

    if index == "population":
        da = _render_population(bbox, datetime, iso3, year, resolution)
    else:
        da = _render_spectral(index, bbox, datetime, resolution, max_cloud_cover)

    da = _reproject_4326(da).squeeze()
    arr = np.asarray(da.values, dtype="float64")
    png = _colorize(arr, style)
    return {
        "index": index,
        "png": png,
        "bounds": _bounds_latlon(da),
        "stats": _finite_stats(arr),
        "cmap": style.cmap,
        "vmin": style.vmin,
        "vmax": style.vmax,
        "label": style.label,
    }


def _render_spectral(index, bbox, datetime, resolution, max_cloud_cover):
    from pin.load import load_scene
    from pin.search import search_collection

    style = STYLES[index]
    cfg = PinConfig(
        bbox=bbox,
        datetime=datetime,
        collections=[style.collection],
        indices=[index],
        max_cloud_cover=max_cloud_cover,
        resolution=resolution,
        max_items_per_collection=1,
    )
    items = search_collection(cfg, style.collection, sign=True)
    if not items:
        raise LookupError("No imagery found for this area/date/cloud filter.")
    spec = get_collection_spec(style.collection)
    roles = list(INDEX_INPUTS[index])
    ds = load_scene(items[0], spec, roles, bbox=bbox, resolution=resolution)
    result = compute_index(index, {r: ds[r] for r in roles})
    return result.rio.write_crs(ds[roles[0]].rio.crs, inplace=False)


def _render_population(bbox, datetime, iso3, year, resolution):
    from pin.population import build_url, clip_population, download, resolve_years

    if not iso3:
        raise ValueError("population overlay requires an ISO3 country code")
    pop = PopulationConfig(iso3=iso3, years=[year] if year else None)
    cfg = PinConfig(bbox=bbox, datetime=datetime, population=pop)
    chosen = year if year else resolve_years(pop, cfg)[-1]
    path = download(build_url(pop, chosen), pop.cache_dir)
    return clip_population(path, bbox)


def render_legend(index: str, width: int = 320, height: int = 42) -> bytes:
    """Render a horizontal colorbar PNG for ``index``."""
    import matplotlib
    import numpy as np
    from PIL import Image

    if index not in STYLES:
        raise KeyError(f"Unknown index {index!r}")
    style = STYLES[index]
    gradient = np.linspace(0, 1, width)
    gradient = np.tile(gradient, (height, 1))
    rgba = matplotlib.colormaps[style.cmap](gradient)
    img = (rgba * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(img, mode="RGBA").save(buf, format="PNG")
    return buf.getvalue()
