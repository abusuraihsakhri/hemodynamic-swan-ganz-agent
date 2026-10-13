"""Deterministic Swan–Ganz hemodynamic calculations.

All inputs are measurements, not inferred observations. These equations do not
diagnose a shock phenotype or prescribe treatment. Units are explicit.
"""
import math
from typing import Optional


def _finite(name: str, value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if (positive and number <= 0) or (not positive and number < 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'}")
    return number


def calculate_hemodynamics(
    cardiac_output_l_min: float,
    body_surface_area_m2: float,
    map_mm_hg: float,
    rap_mm_hg: float,
    mean_pap_mm_hg: float,
    pcwp_mm_hg: float,
    oxygen_consumption_ml_min: Optional[float] = None,
    arterial_oxygen_content_ml_dl: Optional[float] = None,
    mixed_venous_oxygen_content_ml_dl: Optional[float] = None,
) -> dict:
    """Compute CI, SVR, PVR and TPG; optionally calculate direct Fick CO.

    CO and oxygen contents must be supplied independently. Fick values use
    VO2 [mL/min] / (10 * (CaO2 - CvO2) [mL/dL]) = L/min.
    Resistances in dyn·s/cm^5 use the conventional factor 80.
    """
    co = _finite("cardiac_output_l_min", cardiac_output_l_min, positive=True)
    bsa = _finite("body_surface_area_m2", body_surface_area_m2, positive=True)
    map_value = _finite("map_mm_hg", map_mm_hg)
    rap = _finite("rap_mm_hg", rap_mm_hg)
    pap = _finite("mean_pap_mm_hg", mean_pap_mm_hg)
    pcwp = _finite("pcwp_mm_hg", pcwp_mm_hg)
    if map_value < rap:
        raise ValueError("MAP must be at least RAP for this resistance calculation")
    if pap < pcwp:
        raise ValueError("Mean PAP must be at least PCWP for this resistance calculation")

    optional = (
        oxygen_consumption_ml_min,
        arterial_oxygen_content_ml_dl,
        mixed_venous_oxygen_content_ml_dl,
    )
    if any(value is not None for value in optional) and not all(value is not None for value in optional):
        raise ValueError("Direct Fick calculation requires VO2, CaO2 and CvO2 together")

    fick_co = None
    if all(value is not None for value in optional):
        vo2 = _finite("oxygen_consumption_ml_min", oxygen_consumption_ml_min, positive=True)
        cao2 = _finite("arterial_oxygen_content_ml_dl", arterial_oxygen_content_ml_dl, positive=True)
        cvo2 = _finite("mixed_venous_oxygen_content_ml_dl", mixed_venous_oxygen_content_ml_dl)
        if cao2 <= cvo2:
            raise ValueError("Arterial oxygen content must exceed mixed venous oxygen content")
        fick_co = vo2 / (10 * (cao2 - cvo2))

    systemic_gradient = map_value - rap
    transpulmonary_gradient = pap - pcwp
    return {
        "cardiac_index_l_min_m2": co / bsa,
        "svr_dyn_s_cm5": 80 * systemic_gradient / co,
        "svr_wood_units": systemic_gradient / co,
        "pvr_dyn_s_cm5": 80 * transpulmonary_gradient / co,
        "pvr_wood_units": transpulmonary_gradient / co,
        "transpulmonary_gradient_mm_hg": transpulmonary_gradient,
        "fick_cardiac_output_l_min": fick_co,
    }
