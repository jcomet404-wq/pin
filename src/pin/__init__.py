"""PIN — Planetary Intelligence Network.

A small toolkit for computing vegetation, moisture and thermal analytics from
Microsoft Planetary Computer imagery (Sentinel-2 L2A and Landsat C2 L2) and
persisting the results for retrospective, over-time analysis.
"""

from pin.config import PinConfig, PopulationConfig
from pin.indices import (
    lst_celsius,
    ndmi,
    ndvi,
    ndwi,
    normalized_difference,
)

__version__ = "0.1.0"

__all__ = [
    "PinConfig",
    "PopulationConfig",
    "ndvi",
    "ndmi",
    "ndwi",
    "lst_celsius",
    "normalized_difference",
    "__version__",
]
