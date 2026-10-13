"""Independent equation-based regression tests with unit-aware inputs."""
import math
import pytest
from hemodynamic_swan_ganz_agent.hemodynamics import calculate_hemodynamics


BASE = dict(
    cardiac_output_l_min=5.0,
    body_surface_area_m2=2.0,
    map_mm_hg=90.0,
    rap_mm_hg=10.0,
    mean_pap_mm_hg=25.0,
    pcwp_mm_hg=15.0,
)


def test_reference_arithmetic():
    result = calculate_hemodynamics(**BASE)
    assert result["cardiac_index_l_min_m2"] == pytest.approx(2.5)
    assert result["svr_dyn_s_cm5"] == pytest.approx(1280)
    assert result["svr_wood_units"] == pytest.approx(16)
    assert result["pvr_dyn_s_cm5"] == pytest.approx(160)
    assert result["pvr_wood_units"] == pytest.approx(2)
    assert result["transpulmonary_gradient_mm_hg"] == pytest.approx(10)
    assert result["fick_cardiac_output_l_min"] is None


def test_direct_fick_unit_conversion():
    result = calculate_hemodynamics(
        **BASE,
        oxygen_consumption_ml_min=250,
        arterial_oxygen_content_ml_dl=20,
        mixed_venous_oxygen_content_ml_dl=15,
    )
    assert result["fick_cardiac_output_l_min"] == pytest.approx(5)


@pytest.mark.parametrize("changes", [
    {"cardiac_output_l_min": 0},
    {"cardiac_output_l_min": -1},
    {"body_surface_area_m2": 0},
    {"map_mm_hg": 3},
    {"mean_pap_mm_hg": 8},
    {"rap_mm_hg": float("nan")},
    {"pcwp_mm_hg": float("inf")},
    {"cardiac_output_l_min": True},
    {"oxygen_consumption_ml_min": 250},
    {
        "oxygen_consumption_ml_min": 250,
        "arterial_oxygen_content_ml_dl": 14,
        "mixed_venous_oxygen_content_ml_dl": 15,
    },
])
def test_invalid_inputs(changes):
    with pytest.raises(ValueError):
        calculate_hemodynamics(**(BASE | changes))


def test_api_contract():
    from fastapi.testclient import TestClient
    from agents.api import app
    client = TestClient(app)
    response = client.post("/api/hemodynamics", json=BASE)
    assert response.status_code == 200
    assert response.json()["pvr_wood_units"] == pytest.approx(2)
    assert client.post("/api/hemodynamics", json={**BASE, "cardiac_output_l_min": 0}).status_code == 422


def test_alternate_package_api_exposes_same_equations():
    from fastapi.testclient import TestClient
    from hemodynamic_swan_ganz_agent.server import create_app
    client = TestClient(create_app())
    response = client.post("/api/hemodynamics", json=BASE)
    assert response.status_code == 200
    assert response.json()["svr_dyn_s_cm5"] == pytest.approx(1280)
    bad = client.post("/api/hemodynamics", json={**BASE, "mean_pap_mm_hg": 10})
    assert bad.status_code == 422
