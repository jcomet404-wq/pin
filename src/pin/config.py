"""Configuration for a PIN analysis run."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from pin.collections import LANDSAT_C2_L2, SENTINEL2_L2A

DEFAULT_INDICES = ("ndvi", "ndmi", "ndwi", "lst")


@dataclass
class StorageConfig:
    """Where and how results are written."""

    backend: str = "local"  # "local" | "azure" | "s3"
    root: str = "./pin_output"
    # SQLite database (relative to ``root`` unless absolute).
    stats_db: str = "stats.sqlite"
    # Optionally also dump the stats table to Parquet.
    write_parquet: bool = False
    # Remote options (only used by cloud backends).
    container: str | None = None
    prefix: str = ""


@dataclass
class PinConfig:
    """Everything needed to run an analysis over an area and time window.

    ``bbox`` is ``[min_lon, min_lat, max_lon, max_lat]`` (WGS84).
    ``datetime`` is a STAC datetime string, e.g. ``"2023-01-01/2023-01-31"``.
    """

    bbox: list[float]
    datetime: str
    collections: list[str] = field(default_factory=lambda: [SENTINEL2_L2A, LANDSAT_C2_L2])
    indices: list[str] = field(default_factory=lambda: list(DEFAULT_INDICES))
    max_cloud_cover: float = 20.0
    resolution: float = 10.0  # metres; native pixel spacing of the output grid
    max_items_per_collection: int | None = None
    stac_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1"
    storage: StorageConfig = field(default_factory=StorageConfig)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if len(self.bbox) != 4:
            raise ValueError("bbox must be [min_lon, min_lat, max_lon, max_lat]")
        min_lon, min_lat, max_lon, max_lat = self.bbox
        if not (min_lon < max_lon and min_lat < max_lat):
            raise ValueError("bbox min values must be strictly less than max values")
        if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
            raise ValueError("longitude out of range [-180, 180]")
        if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
            raise ValueError("latitude out of range [-90, 90]")
        if "/" not in self.datetime:
            raise ValueError("datetime must be a STAC range like 'START/END'")
        if not (0 <= self.max_cloud_cover <= 100):
            raise ValueError("max_cloud_cover must be in [0, 100]")
        if self.resolution <= 0:
            raise ValueError("resolution must be positive")
        if not self.collections:
            raise ValueError("at least one collection is required")

    # ---- (de)serialisation ------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PinConfig:
        data = dict(data)
        storage = data.pop("storage", None)
        cfg = cls(**data)
        if storage is not None:
            cfg.storage = StorageConfig(**storage)
            cfg.validate()
        return cfg

    @classmethod
    def from_file(cls, path: str | Path) -> PinConfig:
        path = Path(path)
        text = path.read_text()
        if path.suffix.lower() in {".yaml", ".yml"}:
            data = yaml.safe_load(text)
        elif path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")
        if not isinstance(data, dict):
            raise ValueError("Config file must contain a mapping at the top level")
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
