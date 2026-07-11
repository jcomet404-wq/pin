"""Quickstart mirroring the original PIN starter script, using the pin package.

Run with:  python examples/quickstart.py
(requires network access to the Planetary Computer STAC API).
"""

from __future__ import annotations

from pin import PinConfig
from pin.pipeline import run
from pin.timeseries import summary


def main() -> None:
    config = PinConfig(
        bbox=[32.5, 0.0, 33.0, 0.5],
        datetime="2023-01-01/2023-01-31",
        collections=["sentinel-2-l2a", "landsat-c2-l2"],
        indices=["ndvi", "ndmi", "ndwi", "lst"],
        max_cloud_cover=10.0,
        resolution=20.0,
        max_items_per_collection=2,
    )
    records = run(config)
    print(f"Stored {len(records)} index record(s) under {config.storage.root}")

    from pin.storage import get_storage

    df = get_storage(config).read_stats()
    print(summary(df).to_string(index=False))


if __name__ == "__main__":
    main()
