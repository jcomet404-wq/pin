from pin.config import PinConfig, StorageConfig
from pin.storage import LocalStorage, StatRecord, get_storage


def test_write_and_read_stats(tmp_path):
    storage = LocalStorage(StorageConfig(root=str(tmp_path)))
    records = [
        StatRecord(
            collection="sentinel-2-l2a",
            item_id="item-a",
            index_name="ndvi",
            datetime="2023-01-05T00:00:00+00:00",
            mean=0.5,
            min=-0.1,
            max=0.9,
            std=0.2,
            valid_fraction=0.95,
            cloud_cover=3.2,
            raster_uri="a.tif",
        )
    ]
    storage.write_stats(records)
    df = storage.read_stats()
    assert len(df) == 1
    assert df.iloc[0]["index_name"] == "ndvi"
    assert df.iloc[0]["mean"] == 0.5


def test_upsert_replaces_existing(tmp_path):
    storage = LocalStorage(StorageConfig(root=str(tmp_path)))
    rec = StatRecord(collection="c", item_id="i", index_name="ndvi", mean=0.1)
    storage.write_stats([rec])
    rec2 = StatRecord(collection="c", item_id="i", index_name="ndvi", mean=0.9)
    storage.write_stats([rec2])
    df = storage.read_stats()
    assert len(df) == 1
    assert df.iloc[0]["mean"] == 0.9


def test_empty_write_is_noop(tmp_path):
    storage = LocalStorage(StorageConfig(root=str(tmp_path)))
    storage.write_stats([])
    assert storage.read_stats().empty


def test_get_storage_local(tmp_path):
    cfg = PinConfig(
        bbox=[32.5, 0.0, 33.0, 0.5],
        datetime="2023-01-01/2023-01-31",
        storage=StorageConfig(root=str(tmp_path)),
    )
    assert isinstance(get_storage(cfg), LocalStorage)
