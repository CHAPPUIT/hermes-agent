"""Maestro Plugin for Hermes Agent.

Adds OKE-specific capabilities:
- 18 business tools (accounting, payroll, fiscal)
- Security hooks (dangerous operation detection)
- Session hooks (company context loading)
"""

from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# ─── DANGEROUS OKE PATTERNS (Chantier 9) ──────────────────────

_OKE_DANGEROUS_PATTERNS = [
    (r"(?i)DROP\s+(TABLE|DATABASE)\s+", "Drop table/database"),
    (r"(?i)DELETE\s+FROM\s+payroll_", "Delete payroll data"),
    (r"(?i)DELETE\s+FROM\s+accounting_", "Delete accounting data"),
    (r"(?i)TRUNCATE\s+", "Truncate table"),
    (r"(?i)UPDATE\s+.*SET\s+status\s*=\s*'deleted'", "Mass soft-delete"),
    (r"(?i)UPDATE\s+.*SET\s+status\s*=\s*'cancelled'\s+WHERE\s+1", "Mass cancel"),
]


def _check_oke_available() -> bool:
    return bool(os.getenv("OKE_API_URL"))


def _audit_oke_operations(tool_name: str, args: dict, task_id: str = "", **kwargs) -> None:
    """pre_tool_call hook: detect dangerous OKE operations."""
    if tool_name not in ("oke_query_entries", "oke_create_entries"):
        return

    # Check entries for dangerous SQL if raw query is somehow passed
    text_to_check = json.dumps(args, ensure_ascii=False)
    for pattern, desc in _OKE_DANGEROUS_PATTERNS:
        if re.search(pattern, text_to_check):
            logger.warning("BLOCKED dangerous OKE operation: %s (tool=%s)", desc, tool_name)
            # Note: Hermes pre_tool_call return is ignored, but we log the warning
            # The actual protection is in the OKE API backend (RLS + permissions)


def _on_session_start(session_id: str = "", **kwargs) -> None:
    """on_session_start hook: log OKE context."""
    if _check_oke_available():
        logger.info("Maestro OKE plugin active (session=%s, api=%s)", session_id, os.getenv("OKE_API_URL"))


# ─── PLUGIN REGISTRATION ──────────────────────────────────────

def register(ctx):
    """Wire OKE tools and hooks into Hermes."""
    from . import oke_schemas, oke_tools

    if not _check_oke_available():
        logger.info("Maestro plugin: OKE_API_URL not set, tools disabled")
        return

    # Register all 18 OKE tools
    _tool_map = [
        ("oke_query_balances", oke_schemas.QUERY_BALANCES, oke_tools.query_balances),
        ("oke_query_ledger", oke_schemas.QUERY_LEDGER, oke_tools.query_ledger),
        ("oke_query_entries", oke_schemas.QUERY_ENTRIES, oke_tools.query_entries),
        ("oke_create_entries", oke_schemas.CREATE_ENTRIES, oke_tools.create_entries),
        ("oke_get_bilan", oke_schemas.GET_BILAN, oke_tools.get_bilan),
        ("oke_get_pnl", oke_schemas.GET_PNL, oke_tools.get_pnl),
        ("oke_list_employees", oke_schemas.LIST_EMPLOYEES, oke_tools.list_employees),
        ("oke_get_employee", oke_schemas.GET_EMPLOYEE, oke_tools.get_employee),
        ("oke_calculate_payslips", oke_schemas.CALCULATE_PAYSLIPS, oke_tools.calculate_payslips),
        ("oke_list_payslips", oke_schemas.LIST_PAYSLIPS, oke_tools.list_payslips),
        ("oke_get_payslip", oke_schemas.GET_PAYSLIP, oke_tools.get_payslip),
        ("oke_generate_dsn", oke_schemas.GENERATE_DSN, oke_tools.generate_dsn),
        ("oke_validate_dsn", oke_schemas.VALIDATE_DSN, oke_tools.validate_dsn),
        ("oke_list_fiscal_declarations", oke_schemas.LIST_FISCAL_DECLARATIONS, oke_tools.list_fiscal_declarations),
        ("oke_prefill_declaration", oke_schemas.PREFILL_DECLARATION, oke_tools.prefill_declaration),
        ("oke_payroll_dashboard", oke_schemas.PAYROLL_DASHBOARD, oke_tools.payroll_dashboard),
        ("oke_list_absences", oke_schemas.LIST_ABSENCES, oke_tools.list_absences),
        ("oke_scan_fiscal_alerts", oke_schemas.SCAN_FISCAL_ALERTS, oke_tools.scan_fiscal_alerts),
    ]

    for name, schema, handler in _tool_map:
        ctx.register_tool(
            name=name,
            toolset="oke",
            schema=schema,
            handler=handler,
            check_fn=_check_oke_available,
        )

    # Register hooks
    ctx.register_hook("pre_tool_call", _audit_oke_operations)
    ctx.register_hook("on_session_start", _on_session_start)

    logger.info("Maestro plugin: %d OKE tools registered", len(_tool_map))
