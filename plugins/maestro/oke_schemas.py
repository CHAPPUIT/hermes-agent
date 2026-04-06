"""OKE Tool Schemas — OpenAI function-calling format for Hermes Agent."""

# ─── ACCOUNTING ────────────────────────────────────────────────

QUERY_BALANCES = {
    "name": "oke_query_balances",
    "description": (
        "Get account balances for a company. Returns balance per account with "
        "debit/credit totals. Use for balance verification, revision, and financial analysis. "
        "Filter by account type: 'clients' (411), 'fournisseurs' (401), or all."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "account_type": {
                "type": "string",
                "enum": ["all", "clients", "fournisseurs"],
                "description": "Filter by account type (default: all)",
            },
            "fiscal_year_id": {"type": "string", "description": "Fiscal year UUID (optional, defaults to current)"},
        },
        "required": ["company_id"],
    },
}

QUERY_LEDGER = {
    "name": "oke_query_ledger",
    "description": (
        "Get detailed general ledger for a specific account. Returns all entries "
        "with dates, amounts, labels. Use for account revision and audit trail."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "account_num": {"type": "string", "description": "Account number (e.g. '401000', '512000')"},
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD (optional)"},
            "date_to": {"type": "string", "description": "End date YYYY-MM-DD (optional)"},
        },
        "required": ["company_id", "account_num"],
    },
}

QUERY_ENTRIES = {
    "name": "oke_query_entries",
    "description": (
        "Search and list accounting entries with filters. Use to find specific entries, "
        "check journal content, or audit entries by status/date/amount."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "journal_code": {"type": "string", "description": "Journal code (AC, VE, BQ, OD, etc.)"},
            "status": {"type": "string", "enum": ["draft", "validated", "posted", "cancelled"]},
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to": {"type": "string", "description": "End date YYYY-MM-DD"},
            "search": {"type": "string", "description": "Free text search in labels"},
            "limit": {"type": "integer", "description": "Max results (default 50)"},
        },
        "required": ["company_id"],
    },
}

CREATE_ENTRIES = {
    "name": "oke_create_entries",
    "description": (
        "Post a batch of accounting entries. Each entry has a journal, date, and lines "
        "with account/debit/credit. Use for bank fee entries, payroll integration, adjustments. "
        "CAUTION: this writes to the accounting database. Always preview first."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "entries": {
                "type": "array",
                "description": "List of entries to post",
                "items": {
                    "type": "object",
                    "properties": {
                        "journal_code": {"type": "string"},
                        "entry_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "description": {"type": "string"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "account_num": {"type": "string"},
                                    "label": {"type": "string"},
                                    "debit": {"type": "number"},
                                    "credit": {"type": "number"},
                                },
                                "required": ["account_num", "label"],
                            },
                        },
                    },
                    "required": ["journal_code", "entry_date", "lines"],
                },
            },
            "preview": {"type": "boolean", "description": "If true, preview only without posting (default: true)"},
        },
        "required": ["company_id", "entries"],
    },
}

GET_BILAN = {
    "name": "oke_get_bilan",
    "description": (
        "Get the balance sheet (bilan) for a company. Returns actif and passif sections "
        "with totals. Use for financial analysis, closing procedures, and audits."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "fiscal_year_id": {"type": "string", "description": "Fiscal year UUID (optional)"},
            "section": {"type": "string", "enum": ["full", "actif", "passif"], "description": "Section (default: full)"},
        },
        "required": ["company_id"],
    },
}

GET_PNL = {
    "name": "oke_get_pnl",
    "description": (
        "Get profit & loss statement (compte de resultat) for a company. Returns revenue, "
        "expenses, and net result. Use for performance analysis and fiscal preparation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "fiscal_year_id": {"type": "string", "description": "Fiscal year UUID (optional)"},
        },
        "required": ["company_id"],
    },
}

# ─── PAYROLL ───────────────────────────────────────────────────

LIST_EMPLOYEES = {
    "name": "oke_list_employees",
    "description": (
        "List employees for a company with status filter. Returns matricule, name, "
        "contract info, and status. Use before payroll operations."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "status": {"type": "string", "enum": ["active", "inactive", "suspended", "terminated"]},
            "search": {"type": "string", "description": "Search by name or matricule"},
        },
        "required": ["company_id"],
    },
}

GET_EMPLOYEE = {
    "name": "oke_get_employee",
    "description": (
        "Get detailed employee information including contracts, absences, and leave balance. "
        "Use for payroll verification, HR operations, and DSN preparation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "employee_id": {"type": "string", "description": "Employee UUID"},
            "include": {
                "type": "array",
                "items": {"type": "string", "enum": ["contracts", "absences", "leave_balance", "documents"]},
                "description": "Additional data to include",
            },
        },
        "required": ["employee_id"],
    },
}

CALCULATE_PAYSLIPS = {
    "name": "oke_calculate_payslips",
    "description": (
        "Calculate payslips for one or all employees of a company for a given period. "
        "Returns gross, cotisations, and net for each. Use for monthly payroll processing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "period": {"type": "string", "description": "Period YYYY-MM"},
            "employee_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific employee UUIDs (optional, all if omitted)",
            },
        },
        "required": ["company_id", "period"],
    },
}

LIST_PAYSLIPS = {
    "name": "oke_list_payslips",
    "description": (
        "List payslips with filters. Returns summary (gross, net, status) per employee. "
        "Use to check payroll status and identify missing/draft payslips."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "period": {"type": "string", "description": "Period YYYY-MM"},
            "status": {"type": "string", "enum": ["draft", "calculated", "validated", "posted", "sent"]},
        },
        "required": ["company_id"],
    },
}

GET_PAYSLIP = {
    "name": "oke_get_payslip",
    "description": (
        "Get full payslip detail with all lines (gains, deductions, employer charges). "
        "Use for verification, comparison with previous month, or anomaly detection."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "payslip_id": {"type": "string", "description": "Payslip UUID"},
        },
        "required": ["payslip_id"],
    },
}

GENERATE_DSN = {
    "name": "oke_generate_dsn",
    "description": (
        "Generate DSN (Declaration Sociale Nominative) for a company and period. "
        "Creates the NEODeS file for submission to net-entreprises.fr. "
        "Requires validated payslips for the period."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "period": {"type": "string", "description": "Period YYYY-MM"},
            "dsn_type": {"type": "string", "enum": ["monthly", "event"], "description": "DSN type (default: monthly)"},
        },
        "required": ["company_id", "period"],
    },
}

VALIDATE_DSN = {
    "name": "oke_validate_dsn",
    "description": (
        "Validate a generated DSN file before submission. Checks NIR consistency, "
        "amount coherence, CTP codes, and format compliance."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "declaration_id": {"type": "string", "description": "DSN declaration UUID"},
        },
        "required": ["declaration_id"],
    },
}

# ─── FISCAL ────────────────────────────────────────────────────

LIST_FISCAL_DECLARATIONS = {
    "name": "oke_list_fiscal_declarations",
    "description": (
        "List fiscal declarations for a company (TVA, liasse fiscale, IS, IR). "
        "Returns status, dates, and amounts. Use to track declaration deadlines."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "declaration_type": {"type": "string", "enum": ["TVA", "TDFC", "IR", "PAIEMENT"]},
            "status": {"type": "string", "enum": ["draft", "validated", "submitted", "accepted", "rejected"]},
        },
        "required": ["company_id"],
    },
}

PREFILL_DECLARATION = {
    "name": "oke_prefill_declaration",
    "description": (
        "Prefill a fiscal declaration from accounting data. Automatically calculates "
        "TVA bases, deductible amounts, or liasse fiscale cells from the balance."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "declaration_type": {"type": "string", "enum": ["TVA", "TDFC"], "description": "Type to prefill"},
            "period_start": {"type": "string", "description": "Period start YYYY-MM-DD"},
            "period_end": {"type": "string", "description": "Period end YYYY-MM-DD"},
        },
        "required": ["company_id", "declaration_type", "period_start", "period_end"],
    },
}

# ─── DASHBOARD & ALERTS ───────────────────────────────────────

PAYROLL_DASHBOARD = {
    "name": "oke_payroll_dashboard",
    "description": (
        "Get payroll dashboard for a company. Returns summary of current period: "
        "employee count, mass salariale, payslip status breakdown, pending actions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
        },
        "required": ["company_id"],
    },
}

LIST_ABSENCES = {
    "name": "oke_list_absences",
    "description": (
        "List absences for a company or employee. Returns dates, type, status. "
        "Use before payroll to verify absence integration."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
            "employee_id": {"type": "string", "description": "Employee UUID (optional)"},
            "period": {"type": "string", "description": "Period YYYY-MM (optional)"},
            "status": {"type": "string", "enum": ["pending", "approved", "rejected"]},
        },
        "required": ["company_id"],
    },
}

SCAN_FISCAL_ALERTS = {
    "name": "oke_scan_fiscal_alerts",
    "description": (
        "Scan for fiscal alerts and anomalies for a company. Detects: missing declarations, "
        "approaching deadlines, coherence issues, unusual amounts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "company_id": {"type": "string", "description": "Company UUID"},
        },
        "required": ["company_id"],
    },
}

# ─── ALL SCHEMAS ───────────────────────────────────────────────

ALL_SCHEMAS = [
    QUERY_BALANCES,
    QUERY_LEDGER,
    QUERY_ENTRIES,
    CREATE_ENTRIES,
    GET_BILAN,
    GET_PNL,
    LIST_EMPLOYEES,
    GET_EMPLOYEE,
    CALCULATE_PAYSLIPS,
    LIST_PAYSLIPS,
    GET_PAYSLIP,
    GENERATE_DSN,
    VALIDATE_DSN,
    LIST_FISCAL_DECLARATIONS,
    PREFILL_DECLARATION,
    PAYROLL_DASHBOARD,
    LIST_ABSENCES,
    SCAN_FISCAL_ALERTS,
]
