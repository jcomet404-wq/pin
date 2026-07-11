import pytest

from pin.config import PinConfig, PopulationConfig
from pin.population import (
    WORLDPOP_MAX_YEAR,
    bbox_area_km2,
    build_url,
    resolve_years,
    years_from_datetime,
)


def make_config(**overrides):
    base = dict(bbox=[32.5, 0.0, 33.0, 0.5], datetime="2015-01-01/2018-12-31")
    base.update(overrides)
    return PinConfig(**base)


def test_years_from_datetime_range():
    assert years_from_datetime("2015-01-01/2018-06-30") == [2015, 2016, 2017, 2018]


def test_years_from_datetime_single():
    assert years_from_datetime("2019-03-01/2019-09-30") == [2019]


def test_population_config_normalizes_iso3():
    pop = PopulationConfig(iso3="uga")
    assert pop.iso3 == "UGA"


def test_population_config_bad_resolution():
    with pytest.raises(ValueError):
        PopulationConfig(iso3="UGA", resolution="500m")


def test_resolve_years_defaults_to_datetime():
    cfg = make_config(population=PopulationConfig(iso3="UGA"))
    assert resolve_years(cfg.population, cfg) == [2015, 2016, 2017, 2018]


def test_resolve_years_clamped_to_coverage():
    cfg = make_config(
        datetime="2018-01-01/2025-12-31",
        population=PopulationConfig(iso3="UGA"),
    )
    years = resolve_years(cfg.population, cfg)
    assert max(years) == WORLDPOP_MAX_YEAR
    assert 2025 not in years


def test_build_url_1km_and_100m():
    pop_1km = PopulationConfig(iso3="UGA", resolution="1km")
    url = build_url(pop_1km, 2020)
    assert url.endswith("2020/UGA/uga_ppp_2020_1km_Aggregated.tif")
    pop_100m = PopulationConfig(iso3="UGA", resolution="100m")
    assert build_url(pop_100m, 2010).endswith("2010/UGA/uga_ppp_2010.tif")


def test_build_url_custom_template():
    pop = PopulationConfig(iso3="ken", url_template="https://x/{iso3_lower}/{year}.tif")
    assert build_url(pop, 2020) == "https://x/ken/2020.tif"


def test_bbox_area_km2_positive():
    area = bbox_area_km2([32.5, 0.0, 33.0, 0.5])
    # ~0.5deg x 0.5deg near the equator -> roughly 3000 km^2
    assert 2500 < area < 3500


def test_config_roundtrip_with_population():
    cfg = make_config(population=PopulationConfig(iso3="UGA", years=[2019, 2020]))
    restored = PinConfig.from_dict(cfg.to_dict())
    assert restored.population is not None
    assert restored.population.iso3 == "UGA"
    assert restored.population.years == [2019, 2020]
