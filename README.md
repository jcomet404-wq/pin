# PIN — Planetary Intelligence Network

PIN turns [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
imagery into vegetation, moisture and thermal analytics for any area, and stores
the results so you can look at how a place changes **over time**.

For a given bounding box and date range it will:

1. **Search** the STAC catalog (Sentinel-2 L2A and/or Landsat C2 L2), filtering by cloud cover.
2. **Load** the needed bands into analysis-ready rasters in physical units.
3. **Compute** spectral indices per scene:
   - `ndvi` — vegetation density / greenness
   - `ndmi` — canopy/soil moisture
   - `ndwi` — open-water extent
   - `lst`  — land surface temperature in °C (Landsat only)
4. **Store** each index as a cloud-optimized GeoTIFF plus per-scene statistics in SQLite.
5. **Aggregate** those statistics into retrospective time series.

> **Note on thermal:** Sentinel-2 has no thermal band, so land surface
> temperature (`lst`) is derived from Landsat Collection 2 Level-2 (`ST_B10`).
> Optical indices (`ndvi`/`ndmi`/`ndwi`) are computed from Sentinel-2 by default.

It can also track **population** over time. WorldPop gridded population counts
are *not* on Planetary Computer, so PIN downloads the open annual country
rasters from `data.worldpop.org` (2000-2020), clips them to the bbox, and records
total population and areal density per year alongside the spectral indices.

## Install

```bash
pip install -e ".[dev]"          # local development
# optional storage backends:
pip install -e ".[parquet]"      # dump stats to Parquet
pip install -e ".[azure]"        # Azure Blob (stub)
pip install -e ".[s3]"           # S3 (stub)
```

## Quickstart (CLI)

```bash
# From a config file (see examples/uganda_config.yaml)
pin run --config examples/uganda_config.yaml

# Or fully inline
pin run \
  --bbox 32.5,0.0,33.0,0.5 \
  --datetime 2023-01-01/2023-01-31 \
  --indices ndvi,ndmi,ndwi,lst \
  --max-cloud-cover 10 --resolution 20 --max-items 3 \
  --output ./pin_output

# Track population over time (WorldPop), on its own or alongside imagery
pin run \
  --datetime 2015-01-01/2020-12-31 --collections "" \
  --population-iso3 UGA --population-years 2015,2020 --population-resolution 1km \
  --bbox 32.5,0.0,33.0,0.5 --output ./pin_output

# Inspect results
pin summary --output ./pin_output
pin timeseries ndvi --output ./pin_output --freq MS
pin timeseries population --output ./pin_output   # total + density per year
pin indices        # list supported indices
```

## Web map (draw a region, visualize a layer)

An interactive Leaflet map lets you draw a region of interest, pick a layer
(NDVI / NDMI / NDWI / LST / population) and a date range, and see a color-coded
overlay with a legend.

```bash
pip install -e ".[web]"
pin serve                 # -> http://127.0.0.1:8000
```

Draw a rectangle with the toolbar, choose a layer, then **Compute layer**. The
backend runs the pipeline for the least-cloudy scene in the region and returns a
colorized EPSG:4326 PNG overlaid on the map; adjust overlay opacity with the
slider. For the population layer, enter a country ISO3 (e.g. `UGA`) and a year.

## Quickstart (Python)

```python
from pin import PinConfig
from pin.pipeline import run
from pin.storage import get_storage
from pin.timeseries import summary

config = PinConfig(
    bbox=[32.5, 0.0, 33.0, 0.5],
    datetime="2023-01-01/2023-01-31",
    indices=["ndvi", "ndmi", "ndwi", "lst"],
    max_cloud_cover=10.0,
    resolution=20.0,
    max_items_per_collection=3,
)
run(config)
print(summary(get_storage(config).read_stats()))
```

## Data storage layout

```
pin_output/
├── stats.sqlite                       # per-scene index statistics (tidy table)
├── sentinel-2-l2a/ndvi/<item>_ndvi.tif
├── sentinel-2-l2a/ndmi/<item>_ndmi.tif
├── landsat-c2-l2/lst/<item>_lst.tif
├── worldpop-1km/population/<ISO3>_<year>.tif
└── ...
```

The `index_stats` table has one row per `(collection, item_id, index)` with
`mean/min/max/std/total/valid_fraction/cloud_cover/datetime/raster_uri`, which is
what the `timeseries` helpers read for over-time analysis. For population rows,
`total` is the absolute headcount and `mean` is people/km².

## Project layout

| Module | Responsibility |
| --- | --- |
| `pin.config` | Run configuration + validation, YAML/JSON loading |
| `pin.collections` | Collection/band metadata (logical roles → STAC assets, scale/offset) |
| `pin.search` | STAC query, cloud filtering, Planetary Computer signing |
| `pin.load` | STAC items → xarray in physical units (via `odc-stac`) |
| `pin.indices` | NDVI / NDMI / NDWI / LST (array-library agnostic) |
| `pin.population` | WorldPop population download, clip & per-year totals |
| `pin.storage` | COG GeoTIFF + SQLite stats; cloud backend interface |
| `pin.timeseries` | Retrospective time series & temporal aggregation |
| `pin.pipeline` | Orchestration tying it all together |
| `pin.web` | FastAPI + Leaflet web map (ROI drawing, colorized overlays) |
| `pin.cli` | `pin` command-line interface |

## Development

```bash
pytest          # unit tests (no network required)
ruff check .    # lint
mypy src        # type check
```

The unit tests exercise the pure logic (indices, config, storage, time series)
and do not hit the network. The end-to-end pipeline (`pin run` /
`examples/quickstart.py`) does require internet access to Planetary Computer.
