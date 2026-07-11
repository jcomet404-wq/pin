"""STAC search against the Planetary Computer catalog.

Wraps :mod:`pystac_client` with cloud-cover filtering and Planetary Computer
asset signing so downstream code receives ready-to-read items.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pin.config import PinConfig

if TYPE_CHECKING:  # pragma: no cover - typing only
    from pystac import Item

logger = logging.getLogger(__name__)

CLOUD_COVER_PROP = "eo:cloud_cover"


def _open_catalog(stac_url: str, sign: bool):
    from pystac_client import Client

    if sign:
        import planetary_computer as pc

        return Client.open(stac_url, modifier=pc.sign_inplace)
    return Client.open(stac_url)


def search_collection(
    config: PinConfig,
    collection: str,
    *,
    sign: bool = True,
) -> list[Item]:
    """Search a single collection and return items sorted by cloud cover (asc).

    When ``sign`` is True the returned items have their asset hrefs signed for
    direct reads from Planetary Computer storage.
    """
    catalog = _open_catalog(config.stac_url, sign=sign)
    search = catalog.search(
        collections=[collection],
        bbox=config.bbox,
        datetime=config.datetime,
        query={CLOUD_COVER_PROP: {"lt": config.max_cloud_cover}},
    )
    items = list(search.items())
    items.sort(key=lambda it: it.properties.get(CLOUD_COVER_PROP, 100.0))
    if config.max_items_per_collection is not None:
        items = items[: config.max_items_per_collection]
    logger.info("Found %d item(s) for collection %s", len(items), collection)
    return items


def search_all(config: PinConfig, *, sign: bool = True) -> dict[str, list[Item]]:
    """Search every collection listed in the config."""
    return {c: search_collection(config, c, sign=sign) for c in config.collections}
