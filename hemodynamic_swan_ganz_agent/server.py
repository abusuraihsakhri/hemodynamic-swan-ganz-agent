"""
FastAPI REST Application & Webhooks for SwanGanz Sentinel: Pulmonary Artery Catheter Hemodynamic & Shock Classifier.
"""
from typing import Dict, Any, Optional
import json
import math
from agents.base import PHIGuard, SecurityException
from .models import ClinicalCasePayload
from .agents import PACatheterCoordinator
from .hemodynamics import calculate_hemodynamics

coordinator = PACatheterCoordinator()

def create_app():
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, field_validator

        app = FastAPI(
            title="SwanGanz Sentinel: Pulmonary Artery Catheter Hemodynamic & Shock Classifier",
            description="Educational Swan–Ganz hemodynamics and separate legacy generic case audit. No diagnostic shock classification.",
            version="2.0.0-PRO",
        )

        class AuditRequest(BaseModel):
            case_id: str = "CASE-2026-001"
            patient_synthetic_id: str = "SYNTH-PT-881"
            primary_metric: float = 24.5
            secondary_metric: float = 14.0
            status_flag: str = "DISCORDANT"
            is_stat: bool = True
            clinical_notes: str = ""
            biomarkers: Dict[str, Any] = {}

            @field_validator("primary_metric", "secondary_metric")
            @classmethod
            def finite_metrics(cls, value: float) -> float:
                if not math.isfinite(value):
                    raise ValueError("Measurement must be finite")
                return value

        class ChatRequest(BaseModel):
            query: str

        class HemodynamicRequest(BaseModel):
            cardiac_output_l_min: float
            body_surface_area_m2: float
            map_mm_hg: float
            rap_mm_hg: float
            mean_pap_mm_hg: float
            pcwp_mm_hg: float
            oxygen_consumption_ml_min: Optional[float] = None
            arterial_oxygen_content_ml_dl: Optional[float] = None
            mixed_venous_oxygen_content_ml_dl: Optional[float] = None

        @app.post("/api/hemodynamics")
        def api_hemodynamics(payload: HemodynamicRequest):
            try:
                return calculate_hemodynamics(**payload.model_dump())
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "hemodynamic-swan-ganz-agent", "domain": "Critical Care", "version": "2.0.0-PRO"}

        @app.post("/api/audit")
        def api_audit(req: AuditRequest):
            try:
                for text in (req.case_id, req.patient_synthetic_id, req.status_flag, req.clinical_notes):
                    PHIGuard.assert_no_phi(text)
                PHIGuard.assert_no_phi(json.dumps(req.biomarkers, ensure_ascii=False))
            except SecurityException as exc:
                raise HTTPException(status_code=400, detail="Sensitive identifier detected; use synthetic data") from exc
            payload = ClinicalCasePayload(
                case_id=req.case_id,
                patient_synthetic_id=req.patient_synthetic_id,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_flag=req.status_flag,
                is_stat=req.is_stat,
                clinical_notes=req.clinical_notes,
                biomarkers=req.biomarkers,
            )
            return coordinator.process_case(payload)

        @app.post("/api/chat")
        def api_chat(req: ChatRequest):
            try:
                PHIGuard.assert_no_phi(req.query)
            except SecurityException as exc:
                raise HTTPException(status_code=400, detail="Sensitive identifier detected; use synthetic data") from exc
            return {"response": coordinator.query_supervisory_chat(req.query)}

        return app
    except ImportError:
        return None
