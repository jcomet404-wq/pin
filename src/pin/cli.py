"""Command-line interface for PIN."""

from __future__ import annotations

import logging
from pathlib import Path

import typer

from pin.config import PinConfig, StorageConfig
from pin.indices import available_indices

app = typer.Typer(add_completion=False, help="Planetary Intelligence Network CLI.")


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _config_from_options(
    config: Path | None,
    bbox: str | None,
    datetime: str | None,
    collections: str | None,
    indices: str | None,
    max_cloud_cover: float,
    resolution: float,
    max_items: int | None,
    output: str,
) -> PinConfig:
    if config is not None:
        cfg = PinConfig.from_file(config)
    else:
        if bbox is None or datetime is None:
            raise typer.BadParameter("Provide --config, or both --bbox and --datetime")
        cfg = PinConfig(
            bbox=[float(x) for x in bbox.split(",")],
            datetime=datetime,
            storage=StorageConfig(root=output),
        )
    # Inline flags override file values when supplied.
    if collections:
        cfg.collections = [c.strip() for c in collections.split(",") if c.strip()]
    if indices:
        cfg.indices = [i.strip() for i in indices.split(",") if i.strip()]
    if max_cloud_cover is not None:
        cfg.max_cloud_cover = max_cloud_cover
    if resolution is not None:
        cfg.resolution = resolution
    if max_items is not None:
        cfg.max_items_per_collection = max_items
    cfg.validate()
    return cfg


@app.command()
def run(
    config: Path | None = typer.Option(None, "--config", "-c", help="YAML/JSON config file."),
    bbox: str | None = typer.Option(None, help="min_lon,min_lat,max_lon,max_lat"),
    datetime: str | None = typer.Option(None, help="STAC datetime range START/END."),
    collections: str | None = typer.Option(None, help="Comma-separated collection ids."),
    indices: str | None = typer.Option(None, help="Comma-separated indices to compute."),
    max_cloud_cover: float = typer.Option(20.0, help="Max eo:cloud_cover percent."),
    resolution: float = typer.Option(10.0, help="Output pixel size in metres."),
    max_items: int | None = typer.Option(None, help="Cap items per collection."),
    output: str = typer.Option("./pin_output", help="Output directory (local backend)."),
    no_sign: bool = typer.Option(False, "--no-sign", help="Do not sign Planetary Computer assets."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Search imagery, compute indices, and store rasters + statistics."""
    _setup_logging(verbose)
    from pin.pipeline import run as run_pipeline

    cfg = _config_from_options(
        config, bbox, datetime, collections, indices, max_cloud_cover,
        resolution, max_items, output,
    )
    records = run_pipeline(cfg, sign=not no_sign)
    typer.echo(f"Stored {len(records)} index record(s) under {cfg.storage.root}")


@app.command()
def summary(
    output: str = typer.Option("./pin_output", help="Output directory used by `run`."),
    stats_db: str = typer.Option("stats.sqlite", help="SQLite file name/path."),
) -> None:
    """Print the average of each index across the whole stored period."""
    from pin.storage import LocalStorage
    from pin.timeseries import summary as build_summary

    storage = LocalStorage(StorageConfig(root=output, stats_db=stats_db))
    df = storage.read_stats()
    if df.empty:
        typer.echo("No stats found. Run `pin run` first.")
        raise typer.Exit(code=0)
    typer.echo(build_summary(df).to_string(index=False))


@app.command()
def timeseries(
    index: str = typer.Argument(..., help="Index name, e.g. ndvi."),
    output: str = typer.Option("./pin_output", help="Output directory used by `run`."),
    stats_db: str = typer.Option("stats.sqlite", help="SQLite file name/path."),
    freq: str | None = typer.Option(None, help="Aggregate at a pandas freq, e.g. MS."),
) -> None:
    """Show a per-scene (or aggregated) time series for one index."""
    from pin.storage import LocalStorage
    from pin.timeseries import aggregate
    from pin.timeseries import time_series as build_ts

    storage = LocalStorage(StorageConfig(root=output, stats_db=stats_db))
    df = storage.read_stats()
    if df.empty:
        typer.echo("No stats found. Run `pin run` first.")
        raise typer.Exit(code=0)
    ts = build_ts(df, index_name=index)
    if freq:
        ts = aggregate(ts if not ts.empty else df, freq=freq)
    typer.echo(ts.to_string(index=False))


@app.command(name="indices")
def list_indices() -> None:
    """List the spectral indices PIN can compute."""
    for name in available_indices():
        typer.echo(name)


if __name__ == "__main__":  # pragma: no cover
    app()
