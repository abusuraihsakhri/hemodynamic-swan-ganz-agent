"""
FastAPI REST API Server for Hemodynamic Swan Ganz Agent.
"""
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from fastapi.responses import FileResponse
from .base import SecurityException
from hemodynamic_swan_ganz_agent.hemodynamics import calculate_hemodynamics
from .base import AuditLogger, PHIGuard
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Hemodynamic Swan Ganz Agent API",
    description="Enterprise Distributed Component Platform (Cardiology & Intensive Care Systems)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


class HemodynamicRequest(BaseModel):
    cardiac_output_l_min: float
    body_surface_area_m2: float
    map_mm_hg: float
    rap_mm_hg: float
    mean_pap_mm_hg: float
    pcwp_mm_hg: float
    oxygen_consumption_ml_min: float | None = None
    arterial_oxygen_content_ml_dl: float | None = None
    mixed_venous_oxygen_content_ml_dl: float | None = None


WEB_DIR = Path(__file__).resolve().parents[1] / "web"


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/calculator.mjs", include_in_schema=False)
def calculator_script():
    return FileResponse(WEB_DIR / "calculator.mjs", media_type="text/javascript")


@app.post("/api/hemodynamics")
def hemodynamic_calculations(payload: HemodynamicRequest):
    try:
        return calculate_hemodynamics(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "hemodynamic-swan-ganz-agent", "domain": "Cardiology & Intensive Care Systems", "standard": "AHA/ACC Guidelines / Surviving Sepsis Campaign", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    try:
        dossier = supervisor.process_task(payload)
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifier detected; use synthetic data") from exc
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException as exc:
        raise HTTPException(status_code=400, detail="Sensitive identifier detected; use synthetic data") from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}
