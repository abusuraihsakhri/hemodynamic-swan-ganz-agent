# Hemodynamic Swan Ganz Agent

An educational Swan–Ganz hemodynamics calculator and a separate Python multi-worker auditing API. The calculator implements established arithmetic formulas; the legacy auditing workers apply **generic demonstration thresholds**, not validated clinical shock-classification criteria.

## What works

- **Browser calculator** in `web/` computes cardiac index (CI), systemic vascular resistance (SVR), pulmonary vascular resistance (PVR), transpulmonary gradient (TPG), and optional direct Fick cardiac output.
- **Python calculator** in `hemodynamic_swan_ganz_agent/hemodynamics.py` implements the same equations and rejects nonfinite/inconsistent inputs.
- **Python API** provides `POST /api/hemodynamics`, a separate legacy `POST /api/audit`, `POST /api/chat`, `GET /metrics`, `GET /api/audit/logs`, and `GET /health`.
- **CLI** supports single audits, CSV batch processing, the mock chat endpoint, integrity checks, and local server operation.
- **Regression tests** exercise arithmetic, direct Fick units, invalid inputs, HMAC verification, batch flags, and legacy paths.

### Hemodynamic equations

| Quantity | Formula | Units |
| --- | --- | --- |
| CI | CO / BSA | L/min/m² |
| SVR | 80 × (MAP − RAP) / CO | dyn·s/cm⁵ |
| PVR | 80 × (mPAP − PCWP) / CO | dyn·s/cm⁵ |
| PVR (Wood units) | (mPAP − PCWP) / CO | Wood units |
| TPG | mPAP − PCWP | mmHg |
| Direct Fick CO | VO₂ / [10 × (CaO₂ − CvO₂)] | L/min |

CO is in L/min, pressures in mmHg, VO₂ in mL/min, and oxygen contents in mL O₂/dL blood. The optional direct Fick calculation is reported independently and does **not** replace the measured CO input.

**Clinical limitations:** These are deterministic equations, not a diagnostic or decision-support validation study. There is no automatic reliable differentiation of cardiogenic, distributive, or hypovolemic shock. In particular, results depend on correct catheter positioning, waveforms, measurement technique and clinical context. Do not use to guide individual patient treatment.

## Run the browser app

From a repository checkout:

```bash
python -m http.server 8001 -d web
```

Open `http://127.0.0.1:8001/`. No Python runtime, backend, installation, account, uploads or network APIs are needed for browser calculations. A GitHub Pages workflow is provided; a public site URL should only be linked once deployment is verified.

## Python installation and usage

Requires Python 3.9+; the server and test dependencies are optional extras.

```bash
python -m pip install -e ".[server,test]"
python -m pytest -q
python cli.py audit --task-id EXAMPLE-001 --target SYNTH-001 --primary 28.5 --secondary 14.2
python cli.py batch -i sample.csv -o results.csv
python cli.py serve --host 127.0.0.1 --port 8000
```

Both API implementations (`agents.api:app` and the legacy package server) expose `/api/hemodynamics`. For numeric hemodynamics through the API:

```bash
curl -s http://127.0.0.1:8000/api/hemodynamics \
  -H 'Content-Type: application/json' \
  -d '{"cardiac_output_l_min":5,"body_surface_area_m2":2,"map_mm_hg":90,"rap_mm_hg":10,"mean_pap_mm_hg":25,"pcwp_mm_hg":15}'
```

The legacy audit API is separate: its generic `primary_metric` / `secondary_metric` thresholds must **not** be interpreted as specific physiologic thresholds or guideline recommendations. The chat endpoint is a deterministic mock, not a working external language-model service. The API also exposes automatically generated documentation at `/docs`.

To run in Docker: `docker compose up --build` (the API binds to local loopback by default). If audit records must be verifiable after process restarts, provide a stable `AUDIT_SECRET_KEY` through your deployment environment; no default static key is included.

## Privacy and security

The browser calculator uses local JavaScript without uploads, remote fonts, analytics or API requests. **Do not enter personal identifiers or PHI.** Python's PHI regex guard can catch several common identifiers, but is not comprehensive de-identification and does not establish HIPAA compliance. The server has **no authentication**; bind it to loopback or place it behind an appropriately secured reverse proxy before any network exposure. Audit records and keys are held in process memory by default, and cannot be recovered after restart. HMAC-SHA256 verifies recorded entry signatures and the chain; it is not an immutable external audit store.

## Testing and compatibility

Run `python -m pytest -q` and, with Node.js 20+, `node --test tests/web.test.mjs`. CI covers Python 3.10–3.12 and tests the JavaScript calculator. The browser interface uses standard ES modules supported by current Chrome, Firefox, Safari, and Edge. Legacy modules under `agents/`, `enrichment.py`, and `swan_ganz_sentinel.py` are retained for compatibility.

## License

MIT — see [LICENSE](LICENSE).
