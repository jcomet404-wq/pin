"""Collection and band metadata for the data sources PIN understands.

Keeping the asset/band names in one place lets the rest of the code refer to
logical band roles (``red``, ``nir``, ``swir``, ``lst``) instead of the
collection-specific asset keys used by the STAC catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SENTINEL2_L2A = "sentinel-2-l2a"
LANDSAT_C2_L2 = "landsat-c2-l2"

# Logical band roles used across the codebase.
RED = "red"
GREEN = "green"
BLUE = "blue"
NIR = "nir"
SWIR = "swir"
LST = "lst"


@dataclass(frozen=True)
class BandSpec:
    """How to turn a raw asset into physical units.

    ``scale`` and ``offset`` follow the STAC ``raster:bands`` convention:
    ``physical = raw * scale + offset``. ``None`` means values are used as-is.
    """

    asset: str
    scale: float | None = None
    offset: float | None = None


@dataclass(frozen=True)
class CollectionSpec:
    """Describes a supported collection and its logical band mapping."""

    name: str
    bands: dict[str, BandSpec] = field(default_factory=dict)

    def asset_for(self, role: str) -> str:
        return self.bands[role].asset

    def assets_for(self, roles: list[str]) -> list[str]:
        return [self.bands[r].asset for r in roles]


# Sentinel-2 L2A surface reflectance. Digital numbers are scaled by 1/10000 to
# reach reflectance in the 0..1 range (the L2A "quantification value").
SENTINEL2_SPEC = CollectionSpec(
    name=SENTINEL2_L2A,
    bands={
        BLUE: BandSpec(asset="B02", scale=1e-4),
        GREEN: BandSpec(asset="B03", scale=1e-4),
        RED: BandSpec(asset="B04", scale=1e-4),
        NIR: BandSpec(asset="B08", scale=1e-4),
        SWIR: BandSpec(asset="B11", scale=1e-4),
    },
)

# Landsat Collection 2 Level-2. Surface temperature band ST_B10 is stored as a
# scaled integer in Kelvin (physical = DN * 0.00341802 + 149.0).
LANDSAT_SPEC = CollectionSpec(
    name=LANDSAT_C2_L2,
    bands={
        RED: BandSpec(asset="red", scale=2.75e-5, offset=-0.2),
        GREEN: BandSpec(asset="green", scale=2.75e-5, offset=-0.2),
        BLUE: BandSpec(asset="blue", scale=2.75e-5, offset=-0.2),
        NIR: BandSpec(asset="nir08", scale=2.75e-5, offset=-0.2),
        SWIR: BandSpec(asset="swir16", scale=2.75e-5, offset=-0.2),
        LST: BandSpec(asset="lwir11", scale=0.00341802, offset=149.0),
    },
)

REGISTRY: dict[str, CollectionSpec] = {
    SENTINEL2_L2A: SENTINEL2_SPEC,
    LANDSAT_C2_L2: LANDSAT_SPEC,
}


def get_collection_spec(name: str) -> CollectionSpec:
    try:
        return REGISTRY[name]
    except KeyError as exc:
        supported = ", ".join(sorted(REGISTRY))
        raise KeyError(f"Unsupported collection {name!r}. Supported: {supported}") from exc
