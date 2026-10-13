"""
Command Line Interface for Hemodynamic Swan Ganz Agent.
"""
import argparse
import csv
import json
import os
import sys
from agents.models import SystemTaskPayload
from agents.supervisor import SystemSupervisor
from agents.base import AuditLogger

supervisor = SystemSupervisor(model_provider="mock")


def _safe_resolve_path(path_str: str, must_exist: bool = False) -> str:
    """Resolve a path safely, rejecting traversal outside the working directory."""
    resolved = os.path.realpath(os.path.abspath(path_str))
    cwd = os.path.realpath(os.getcwd())
    if not resolved.startswith(cwd + os.sep) and resolved != cwd:
        raise ValueError(f"Path '{path_str}' resolves outside the working directory (traversal rejected)")
    if must_exist and not os.path.isfile(resolved):
        raise FileNotFoundError(f"Input file not found: {path_str}")
    return resolved


def _parse_csv_bool(value):
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n", ""}:
        return False
    raise ValueError("Critical flag must be true/false, yes/no or 1/0")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hemodynamic-swan-ganz-agent", description="Hemodynamic Swan Ganz Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Audit
    p_audit = subparsers.add_parser("audit", help="Run single task evaluation")
    p_audit.add_argument("--task-id", default="TASK-2026-001")
    p_audit.add_argument("--target", default="KEY-TARGET-01")
    p_audit.add_argument("--primary", type=float, default=28.5)
    p_audit.add_argument("--secondary", type=float, default=14.2)
    p_audit.add_argument("--critical", action="store_true")
    p_audit.add_argument("--status", default="DISCORDANT")

    # Chat
    p_chat = subparsers.add_parser("chat", help="System configuration query")
    p_chat.add_argument("query", nargs="+")

    # Batch
    p_batch = subparsers.add_parser("batch", help="Batch process CSV records")
    p_batch.add_argument("-i", "--input", required=True)
    p_batch.add_argument("-o", "--output", default="results.csv")

    # Verify Audit
    subparsers.add_parser("verify-audit", help="Verify HMAC audit trail integrity")

    # Serve
    p_serve = subparsers.add_parser("serve", help="Launch FastAPI REST server")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)

    args = parser.parse_args(argv)

    if args.command == "audit":
        payload = SystemTaskPayload(
            task_id=args.task_id,
            target_identifier=args.target,
            primary_metric=args.primary,
            secondary_metric=args.secondary,
            status_descriptor=args.status,
            is_critical_flag=args.critical,
        )
        dossier = supervisor.process_task(payload)
        print("=" * 80)
        print(f"  HEMODYNAMIC SWAN GANZ AGENT")
        print(f"  Domain: Cardiology & Intensive Care Systems | Standard: AHA/ACC Guidelines / Surviving Sepsis Campaign")
        print(f"  Dossier ID: {dossier.dossier_id} | Urgency: [{dossier.overall_urgency.value}]")
        print("=" * 80)
        for a in dossier.alerts:
            print(f"\n  [{a.urgency.value}] from {a.origin_worker}:")
            print(f"  Summary: {a.summary}")
            print(f"  Details: {a.technical_details}")
            print(f"  Action:  {a.actionable_remediation}")
        print(f"\n  HMAC-SHA256 Audit Hash: {dossier.audit_hash}")
        print("=" * 80)
        return 0

    if args.command == "chat":
        ans = supervisor.query_supervisory_chat(" ".join(args.query))
        print(f"\n[Hemodynamic Swan Ganz Agent Supervisor]:\n{ans}\n")
        return 0

    if args.command == "verify-audit":
        trail = AuditLogger.get_trail()
        valid = AuditLogger.verify_integrity()
        print(f"Audit Trail Blocks: {len(trail)} | Cryptographic Integrity Verified: {valid}")
        return 0

    if args.command == "batch":
        safe_input = _safe_resolve_path(args.input, must_exist=True)
        safe_output = _safe_resolve_path(args.output, must_exist=False)
        with open(safe_input, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)

        out_fields = list(dict.fromkeys(fieldnames + ["overall_urgency", "integrity_status", "total_alerts", "audit_hash"]))
        out_rows = []
        for r in rows:
            try:
                payload = SystemTaskPayload(
                    task_id=r.get("task_id") or r.get("case_id") or "TASK-01",
                    target_identifier=r.get("target_identifier") or r.get("patient_synthetic_id") or "TARGET-01",
                    primary_metric=float(r.get("primary_metric") or r.get("metric_primary") or 15.0),
                    secondary_metric=float(r.get("secondary_metric") or r.get("metric_secondary") or 5.0),
                    status_descriptor=r.get("status_descriptor") or r.get("status_flag") or "NOMINAL",
                    is_critical_flag=_parse_csv_bool(r.get("is_critical_flag", r.get("is_stat", False))),
                )
            except (ValueError, TypeError) as e:
                print(f"Skipping invalid row: {type(e).__name__}: {e}")
                continue
            dossier = supervisor.process_task(payload)
            row_dict = dict(r)
            row_dict["overall_urgency"] = dossier.overall_urgency.value
            row_dict["integrity_status"] = dossier.integrity_status.value
            row_dict["total_alerts"] = dossier.total_alerts
            row_dict["audit_hash"] = dossier.audit_hash
            out_rows.append(row_dict)

        with open(safe_output, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"Processed {len(out_rows)} records -> {args.output}")
        return 0

    if args.command == "serve":
        import uvicorn
        from agents.api import app
        print(f"Starting Hemodynamic Swan Ganz Agent API server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
