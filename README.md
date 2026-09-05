# Hemodynamic Swan Ganz Agent

> **Domain:** Cardiovascular Medicine & Hemodynamic Analytics
> **Reference Guidelines:** AHA/ACC Practice Guidelines & ESC Clinical Standards / Surviving Sepsis Campaign 2021 & Sepsis-3

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

---

## What It Does

**Hemodynamic Swan Ganz Agent** is an analytical platform implementing Fick Cardiac Index calculations, SVR computation, and shock profile classification for critical care environments. It uses a multi-worker agent architecture to evaluate hemodynamic parameters against clinical guidelines.

---

## Architecture

### Core Components

| Module | Description |
|:-------|:------------|
| `agents/` | Core agent orchestrator with PHI guard, HMAC-SHA256 audit trail, and specialized workers |
| `hemodynamic_swan_ganz_agent/` | Clinical sub-package with domain engine and REST server |
| `enrichment.py` | Feature enrichment engines (Dynamic, Vasopressor, Right Heart, Pulmonary, Weaning, Cardiac, Hemodynamic) |
| `cli.py` | Main CLI entry point (audit, chat, batch, serve commands) |
| `simulator.py` | High-throughput stress testing and adversarial PHI audit tool |

### Specialized Workers

- **InvariantQCWorker** — Primary metric threshold and boundary auditor
- **SafetyEscalationWorker** — Safety interlock and STAT escalation detector
- **ProtocolConformanceWorker** — Status descriptor concordance checker

---

## Quickstart

### Installation

```bash
pip install fastapi uvicorn pydantic pytest
```

### Run CLI Audit

```bash
python cli.py audit --task-id CASE-001 --primary 28.5 --secondary 14.2 --critical --status DISCORDANT
```

### Interactive Chat

```bash
python cli.py chat "Explain hemodynamic parameters"
```

### Batch CSV Processing

```bash
python cli.py batch -i sample.csv -o results.csv
```

### Start REST API Server

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

### Run Simulation

```bash
python simulator.py 1000
```

---

## API Endpoints

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/health` | GET | Health and service metadata |
| `/metrics` | GET | Prometheus operational metrics |
| `/api/audit` | POST | Submit task payload for multi-worker evaluation |
| `/api/chat` | POST | Query air-gapped supervisory assistant |
| `/api/audit/logs` | GET | Retrieve HMAC-signed audit trail with integrity verification |

---

## Security Features

- **Zero-PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, emails, DOBs, and patient names
- **HMAC-SHA256 Tamper-Evident Audit Trail:** Cryptographically chained log entries for every evaluation
- **Path Traversal Protection:** Batch CLI validates all file paths stay within working directory
- **Input Validation:** All metrics validated as finite numbers; identifiers sanitized and non-empty

### Audit Key Configuration

The HMAC audit key resolves in priority order:
1. Explicit `secret_key` argument to `AuditTrail()`
2. `AUDIT_SECRET_KEY` environment variable
3. Auto-generated cryptographically secure random key (per session)

For production deployments, always set `AUDIT_SECRET_KEY`:
```bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

---

## Testing

```bash
pytest -v
```

The test suite covers:
- PHI guard enforcement (SSN, MRN, phone, email patterns)
- Specialized worker threshold detection
- Supervisor consensus and audit integrity
- CLI command execution
- Enrichment engine behavior

---

## Docker Deployment

```bash
docker compose up --build
# Or manually:
docker build -t hemodynamic-swan-ganz-agent .
docker run -p 8000:8000 -e AUDIT_SECRET_KEY=your-secret hemodynamic-swan-ganz-agent
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
