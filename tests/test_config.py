import pytest

from pin.collections import LANDSAT_C2_L2, SENTINEL2_L2A
from pin.config import PinConfig, StorageConfig


def make_config(**overrides):
    base = dict(bbox=[32.5, 0.0, 33.0, 0.5], datetime="2023-01-01/2023-01-31")
    base.update(overrides)
    return PinConfig(**base)


def test_defaults():
    cfg = make_config()
    assert cfg.collections == [SENTINEL2_L2A, LANDSAT_C2_L2]
    assert "ndvi" in cfg.indices
    assert isinstance(cfg.storage, StorageConfig)


def test_bad_bbox_length():
    with pytest.raises(ValueError):
        make_config(bbox=[1, 2, 3])


def test_bbox_min_max_order():
    with pytest.raises(ValueError):
        make_config(bbox=[33.0, 0.5, 32.5, 0.0])


def test_bbox_out_of_range():
    with pytest.raises(ValueError):
        make_config(bbox=[-200, 0.0, 33.0, 0.5])


def test_datetime_requires_range():
    with pytest.raises(ValueError):
        make_config(datetime="2023-01-01")


def test_cloud_cover_bounds():
    with pytest.raises(ValueError):
        make_config(max_cloud_cover=150)


def test_resolution_positive():
    with pytest.raises(ValueError):
        make_config(resolution=0)


def test_roundtrip_dict():
    cfg = make_config(max_cloud_cover=5.0)
    data = cfg.to_dict()
    restored = PinConfig.from_dict(data)
    assert restored.max_cloud_cover == 5.0
    assert restored.bbox == cfg.bbox


def test_from_file_yaml(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "bbox: [32.5, 0.0, 33.0, 0.5]\n"
        "datetime: '2023-01-01/2023-01-31'\n"
        "max_cloud_cover: 8\n"
        "storage:\n  root: /tmp/out\n"
    )
    cfg = PinConfig.from_file(p)
    assert cfg.max_cloud_cover == 8
    assert cfg.storage.root == "/tmp/out"
