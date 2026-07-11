"""Persistence for rasters and computed statistics.

The default :class:`LocalStorage` writes cloud-optimized GeoTIFFs to disk and
records scalar statistics in a SQLite table (optionally mirrored to Parquet).
Cloud backends share the same :class:`Storage` interface; a stub is provided as
a starting point for Azure Blob / S3 implementations.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pin.config import PinConfig, StorageConfig

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd
    import xarray as xr

logger = logging.getLogger(__name__)

STATS_TABLE = "index_stats"

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {STATS_TABLE} (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    collection    TEXT    NOT NULL,
    item_id       TEXT    NOT NULL,
    datetime      TEXT,
    index_name    TEXT    NOT NULL,
    mean          REAL,
    min           REAL,
    max           REAL,
    std           REAL,
    valid_fraction REAL,
    cloud_cover   REAL,
    raster_uri    TEXT,
    created_at    TEXT    NOT NULL,
    UNIQUE(collection, item_id, index_name)
);
"""

STATS_COLUMNS = (
    "collection",
    "item_id",
    "datetime",
    "index_name",
    "mean",
    "min",
    "max",
    "std",
    "valid_fraction",
    "cloud_cover",
    "raster_uri",
    "created_at",
)


@dataclass
class StatRecord:
    """One computed index over one scene."""

    collection: str
    item_id: str
    index_name: str
    datetime: str | None = None
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    std: float | None = None
    valid_fraction: float | None = None
    cloud_cover: float | None = None
    raster_uri: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_row(self) -> tuple[Any, ...]:
        return tuple(getattr(self, c) for c in STATS_COLUMNS)


class Storage:
    """Abstract persistence interface."""

    def write_raster(self, data: xr.DataArray, relpath: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def write_stats(self, records: list[StatRecord]) -> None:  # pragma: no cover
        raise NotImplementedError

    def read_stats(self) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError


class LocalStorage(Storage):
    """Filesystem-backed storage: COG GeoTIFFs plus a SQLite stats table."""

    def __init__(self, cfg: StorageConfig):
        self.cfg = cfg
        self.root = Path(cfg.root).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        db = Path(cfg.stats_db)
        self.db_path = db if db.is_absolute() else self.root / db
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)

    def write_raster(self, data: xr.DataArray, relpath: str) -> str:
        path = self.root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        # Cloud-optimized GeoTIFF for fast partial reads later.
        data.rio.to_raster(path, driver="COG", compress="deflate")
        logger.debug("Wrote raster %s", path)
        return str(path)

    def write_stats(self, records: list[StatRecord]) -> None:
        if not records:
            return
        placeholders = ", ".join(["?"] * len(STATS_COLUMNS))
        columns = ", ".join(STATS_COLUMNS)
        sql = (
            f"INSERT INTO {STATS_TABLE} ({columns}) VALUES ({placeholders}) "
            f"ON CONFLICT(collection, item_id, index_name) DO UPDATE SET "
            + ", ".join(
                f"{c}=excluded.{c}"
                for c in STATS_COLUMNS
                if c not in ("collection", "item_id", "index_name")
            )
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(sql, [r.as_row() for r in records])
        if self.cfg.write_parquet:
            self._dump_parquet()

    def read_stats(self) -> pd.DataFrame:
        import pandas as pd

        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(f"SELECT * FROM {STATS_TABLE}", conn)

    def _dump_parquet(self) -> None:
        df = self.read_stats()
        out = self.root / "stats.parquet"
        df.to_parquet(out, index=False)
        logger.debug("Wrote stats parquet %s", out)


class CloudStorage(Storage):
    """Placeholder for object-store backends (Azure Blob, S3).

    Implement :meth:`write_raster`/:meth:`write_stats` using ``fsspec``
    (``adlfs`` for Azure, ``s3fs`` for AWS). The install extras ``pin[azure]``
    and ``pin[s3]`` pull in the needed drivers.
    """

    def __init__(self, cfg: StorageConfig):
        self.cfg = cfg

    def _not_ready(self) -> NotImplementedError:
        return NotImplementedError(
            f"Cloud backend {self.cfg.backend!r} is not implemented yet. "
            "Use backend='local', or implement CloudStorage with fsspec."
        )

    def write_raster(self, data: xr.DataArray, relpath: str) -> str:
        raise self._not_ready()

    def write_stats(self, records: list[StatRecord]) -> None:
        raise self._not_ready()

    def read_stats(self) -> pd.DataFrame:
        raise self._not_ready()


def get_storage(config: PinConfig) -> Storage:
    backend = config.storage.backend.lower()
    if backend == "local":
        return LocalStorage(config.storage)
    if backend in {"azure", "s3"}:
        return CloudStorage(config.storage)
    raise ValueError(f"Unknown storage backend: {config.storage.backend!r}")
