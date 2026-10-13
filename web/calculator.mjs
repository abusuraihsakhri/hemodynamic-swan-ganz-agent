/** Numerical equations for educational Swan–Ganz calculations. No diagnosis. */
function finite(name, value, positive = false) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new RangeError(name + ' must be a finite number');
  }
  if (positive ? value <= 0 : value < 0) {
    throw new RangeError(name + (positive ? ' must be > 0' : ' must be >= 0'));
  }
  return value;
}

export function calculateHemodynamics(input) {
  const co = finite('Cardiac output', input.cardiac_output_l_min, true);
  const bsa = finite('Body surface area', input.body_surface_area_m2, true);
  const map = finite('MAP', input.map_mm_hg);
  const rap = finite('RAP', input.rap_mm_hg);
  const pap = finite('Mean PAP', input.mean_pap_mm_hg);
  const pcwp = finite('PCWP', input.pcwp_mm_hg);
  if (map < rap) throw new RangeError('MAP must be at least RAP');
  if (pap < pcwp) throw new RangeError('Mean PAP must be at least PCWP');

  const opt = [
    input.oxygen_consumption_ml_min,
    input.arterial_oxygen_content_ml_dl,
    input.mixed_venous_oxygen_content_ml_dl
  ];
  if (opt.some(v => v !== null && v !== undefined) &&
      !opt.every(v => v !== null && v !== undefined)) {
    throw new RangeError('Direct Fick CO requires all three oxygen measurements');
  }
  let fick = null;
  if (opt.every(v => v !== null && v !== undefined)) {
    const vo2 = finite('VO₂', opt[0], true);
    const ca = finite('CaO₂', opt[1], true);
    const cv = finite('CvO₂', opt[2]);
    if (ca <= cv) throw new RangeError('CaO₂ must exceed CvO₂');
    fick = vo2 / (10 * (ca - cv));
  }
  const systemic = map - rap;
  const tpg = pap - pcwp;
  return {
    cardiac_index_l_min_m2: co / bsa,
    svr_dyn_s_cm5: 80 * systemic / co,
    svr_wood_units: systemic / co,
    pvr_dyn_s_cm5: 80 * tpg / co,
    pvr_wood_units: tpg / co,
    transpulmonary_gradient_mm_hg: tpg,
    fick_cardiac_output_l_min: fick
  };
}

if (typeof document !== 'undefined') {
  const form = document.getElementById('calculator-form');
  const results = document.getElementById('results');
  const error = document.getElementById('error');
  const count = document.getElementById('count');
  let calculations = 0;

  function read(id, optional = false) {
    const el = document.getElementById(id);
    const raw = el.value.trim();
    if (optional && !raw) return null;
    if (!raw) throw new RangeError(el.dataset.label + ' is required');
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new RangeError(el.dataset.label + ' must be a finite number');
    return value;
  }

  const descriptors = [
    ['cardiac_index_l_min_m2', 'Cardiac index', 'L/min/m²'],
    ['svr_dyn_s_cm5', 'Systemic vascular resistance', 'dyn·s/cm⁵'],
    ['svr_wood_units', 'Systemic resistance', 'Wood units'],
    ['pvr_dyn_s_cm5', 'Pulmonary vascular resistance', 'dyn·s/cm⁵'],
    ['pvr_wood_units', 'Pulmonary resistance', 'Wood units'],
    ['transpulmonary_gradient_mm_hg', 'Transpulmonary gradient', 'mmHg'],
    ['fick_cardiac_output_l_min', 'Direct Fick cardiac output', 'L/min']
  ];

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    error.textContent = '';
    results.replaceChildren();
    try {
      const values = calculateHemodynamics({
        cardiac_output_l_min: read('co'),
        body_surface_area_m2: read('bsa'),
        map_mm_hg: read('map'),
        rap_mm_hg: read('rap'),
        mean_pap_mm_hg: read('pap'),
        pcwp_mm_hg: read('pcwp'),
        oxygen_consumption_ml_min: read('vo2', true),
        arterial_oxygen_content_ml_dl: read('cao2', true),
        mixed_venous_oxygen_content_ml_dl: read('cvo2', true)
      });
      for (const [key, label, unit] of descriptors) {
        if (values[key] === null) continue;
        const row = document.createElement('div');
        row.className = 'result';
        const caption = document.createElement('span');
        caption.textContent = label;
        const value = document.createElement('strong');
        value.textContent = values[key].toLocaleString('en-US', {maximumFractionDigits: 2}) + ' ' + unit;
        row.append(caption, value);
        results.append(row);
      }
      count.textContent = String(++calculations);
    } catch (exc) {
      error.textContent = exc.message;
    }
  });

  document.getElementById('clear').addEventListener('click', () => {
    form.reset();
    error.textContent = '';
    results.replaceChildren();
  });
}
