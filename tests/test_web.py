import pytest

pytest.importorskip("fastapi")
pytest.importorskip("matplotlib")
pytest.importorskip("PIL")

from fastapi.testclient import TestClient  # noqa: E402

from pin.web.app import app  # noqa: E402
from pin.web.render import available_styles, render_legend  # noqa: E402

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_available_styles_has_indices():
    styles = available_styles()
    assert {"ndvi", "ndmi", "ndwi", "lst", "population"} <= set(styles)
    assert styles["ndvi"]["cmap"] == "RdYlGn"


def test_render_legend_is_png():
    png = render_legend("ndvi")
    assert png.startswith(PNG_MAGIC)


def test_render_legend_unknown():
    with pytest.raises(KeyError):
        render_legend("nope")


def test_api_styles():
    client = TestClient(app)
    res = client.get("/api/styles")
    assert res.status_code == 200
    assert "ndvi" in res.json()


def test_api_legend():
    client = TestClient(app)
    res = client.get("/api/legend/lst")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert res.content.startswith(PNG_MAGIC)


def test_api_legend_404():
    client = TestClient(app)
    assert client.get("/api/legend/nope").status_code == 404


def test_index_html_served():
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    assert "PIN" in res.text


def test_compute_unknown_index_400():
    client = TestClient(app)
    res = client.post(
        "/api/compute",
        json={"index": "nope", "bbox": [0, 0, 1, 1], "datetime": "2023-01-01/2023-01-31"},
    )
    assert res.status_code == 400
