"""OKE Tool Handlers — business logic for each OKE tool."""

from __future__ import annotations

import json
import logging
from typing import Any

from .oke_client import get_client

logger = logging.getLogger(__name__)


def _ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False)


def _call(fn, args: dict, **kwargs) -> str:
    try:
        return fn(args, **kwargs)
    except Exception as e:
        logger.exception("OKE tool error: %s", e)
        return _err(f"OKE API error: {type(e).__name__}: {e}")


# ─── ACCOUNTING ────────────────────────────────────────────────

def query_balances(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid = a["company_id"]
        atype = a.get("account_type", "all")
        if atype == "clients":
            return _ok(c.get(f"/accounting/balances/{cid}/clients"))
        elif atype == "fournisseurs":
            return _ok(c.get(f"/accounting/balances/{cid}/fournisseurs"))
        params = {}
        if a.get("fiscal_year_id"):
            params["fiscal_year_id"] = a["fiscal_year_id"]
        return _ok(c.get(f"/accounting/balances/{cid}", params=params))
    return _call(_run, args, **kwargs)


def query_ledger(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid, acct = a["company_id"], a["account_num"]
        params = {}
        if a.get("date_from"):
            params["date_from"] = a["date_from"]
        if a.get("date_to"):
            params["date_to"] = a["date_to"]
        return _ok(c.get(f"/accounting/ledger/{cid}/{acct}", params=params))
    return _call(_run, args, **kwargs)


def query_entries(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid = a["company_id"]
        params = {k: v for k, v in a.items() if k != "company_id" and v is not None}
        return _ok(c.get(f"/accounting/entries/{cid}", params=params))
    return _call(_run, args, **kwargs)


def create_entries(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid = a["company_id"]
        preview = a.get("preview", True)
        endpoint = "batch-post/preview" if preview else "batch-post"
        return _ok(c.post(f"/accounting/companies/{cid}/entries/{endpoint}", body={"entries": a["entries"]}))
    return _call(_run, args, **kwargs)


def get_bilan(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid = a["company_id"]
        section = a.get("section", "full")
        params = {}
        if a.get("fiscal_year_id"):
            params["fiscal_year_id"] = a["fiscal_year_id"]
        if section == "actif":
            return _ok(c.get(f"/accounting/bilan/{cid}/actif", params=params))
        elif section == "passif":
            return _ok(c.get(f"/accounting/bilan/{cid}/passif", params=params))
        return _ok(c.get(f"/accounting/bilan/{cid}", params=params))
    return _call(_run, args, **kwargs)


def get_pnl(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        cid = a["company_id"]
        params = {}
        if a.get("fiscal_year_id"):
            params["fiscal_year_id"] = a["fiscal_year_id"]
        return _ok(c.get(f"/accounting/profit-loss/{cid}", params=params))
    return _call(_run, args, **kwargs)


# ─── PAYROLL ───────────────────────────────────────────────────

def list_employees(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        params = {k: v for k, v in a.items() if v is not None}
        return _ok(c.get("/payroll/employees", params=params))
    return _call(_run, args, **kwargs)


def get_employee(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        eid = a["employee_id"]
        result = c.get(f"/payroll/employees/{eid}")
        includes = a.get("include", [])
        if "contracts" in includes:
            result["contracts"] = c.get(f"/payroll/employees/{eid}/contracts")
        if "leave_balance" in includes:
            result["leave_balance"] = c.get(f"/payroll/employees/{eid}/leave-balance")
        if "documents" in includes:
            result["documents"] = c.get(f"/payroll/employees/{eid}/documents")
        return _ok(result)
    return _call(_run, args, **kwargs)


def calculate_payslips(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        body = {"company_id": a["company_id"], "period": a["period"]}
        if a.get("employee_ids"):
            body["employee_ids"] = a["employee_ids"]
        return _ok(c.post("/payroll/payslips/calculate/bulk", body=body))
    return _call(_run, args, **kwargs)


def list_payslips(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        params = {k: v for k, v in a.items() if v is not None}
        return _ok(c.get("/payroll/payslips", params=params))
    return _call(_run, args, **kwargs)


def get_payslip(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        return _ok(c.get(f"/payroll/payslips/{a['payslip_id']}"))
    return _call(_run, args, **kwargs)


def generate_dsn(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        body = {
            "company_id": a["company_id"],
            "period": a["period"],
            "type": a.get("dsn_type", "monthly"),
        }
        return _ok(c.post("/payroll/dsn/generate", body=body))
    return _call(_run, args, **kwargs)


def validate_dsn(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        return _ok(c.post("/payroll/dsn/validate", body={"declaration_id": a["declaration_id"]}))
    return _call(_run, args, **kwargs)


# ─── FISCAL ────────────────────────────────────────────────────

def list_fiscal_declarations(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        params = {k: v for k, v in a.items() if v is not None}
        return _ok(c.get("/fiscal/declarations", params=params))
    return _call(_run, args, **kwargs)


def prefill_declaration(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        return _ok(c.post("/fiscal/declarations/prefill", body=a))
    return _call(_run, args, **kwargs)


# ─── DASHBOARD & ALERTS ───────────────────────────────────────

def payroll_dashboard(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        return _ok(c.get(f"/payroll/dashboard/{a['company_id']}"))
    return _call(_run, args, **kwargs)


def list_absences(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        params = {k: v for k, v in a.items() if v is not None}
        return _ok(c.get("/payroll/absences", params=params))
    return _call(_run, args, **kwargs)


def scan_fiscal_alerts(args: dict, **kwargs) -> str:
    def _run(a, **kw):
        c = get_client()
        return _ok(c.post(f"/fiscal/alerts/company/{a['company_id']}/scan"))
    return _call(_run, args, **kwargs)
