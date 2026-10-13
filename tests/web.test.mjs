import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateHemodynamics } from '../web/calculator.mjs';

const input = {
  cardiac_output_l_min: 5, body_surface_area_m2: 2,
  map_mm_hg: 90, rap_mm_hg: 10, mean_pap_mm_hg: 25, pcwp_mm_hg: 15
};

test('hemodynamic equations and units', () => {
  const value = calculateHemodynamics(input);
  assert.equal(value.cardiac_index_l_min_m2, 2.5);
  assert.equal(value.svr_dyn_s_cm5, 1280);
  assert.equal(value.pvr_dyn_s_cm5, 160);
  assert.equal(value.pvr_wood_units, 2);
  assert.equal(value.transpulmonary_gradient_mm_hg, 10);
  assert.equal(value.fick_cardiac_output_l_min, null);
});

test('direct Fick calculation', () => {
  const value = calculateHemodynamics({
    ...input, oxygen_consumption_ml_min: 250,
    arterial_oxygen_content_ml_dl: 20,
    mixed_venous_oxygen_content_ml_dl: 15
  });
  assert.equal(value.fick_cardiac_output_l_min, 5);
});

for (const changes of [
  { cardiac_output_l_min: 0 }, { body_surface_area_m2: -1 },
  { map_mm_hg: 2 }, { mean_pap_mm_hg: 8 },
  { rap_mm_hg: Number.NaN }, { pcwp_mm_hg: Infinity },
  { oxygen_consumption_ml_min: 250 },
  { oxygen_consumption_ml_min: 250, arterial_oxygen_content_ml_dl: 15,
    mixed_venous_oxygen_content_ml_dl: 20 }
]) {
  test('reject invalid values ' + JSON.stringify(changes), () => {
    assert.throws(() => calculateHemodynamics({...input, ...changes}), RangeError);
  });
}
