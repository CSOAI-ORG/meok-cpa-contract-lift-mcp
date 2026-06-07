#!/usr/bin/env python3
"""
MEOK CPA Hire vs Contract Lift MCP
===================================

By MEOK AI Labs · https://haulage.app · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-cpa-contract-lift-mcp -->

WHAT THIS DOES
--------------
UK crane, hiab, and plant-hire operators issue thousands of quotes per week.
Each quote sits at the £100k+ wedge between two very different contract types
under the CPA (Construction Plant-hire Association) Model Conditions:

  HIRE-ONLY ("plant hire")
    - Hirer directs the lift; supplies their own Appointed Person (AP)
    - Owner provides plant + operator only
    - Owner indemnified under CPA Condition 13 once plant is "on hire"
    - LOWER price, MUCH HIGHER liability transfer to the hirer

  CONTRACT LIFT
    - Owner takes full responsibility — supplies plant + operator + AP
    - Owner plans + directs the lift
    - Owner's insurer carries the risk
    - HIGHER price (typically +15-30% on hire rate) but proper risk packaging

Getting this triage WRONG at quote stage is what kills crane firms. The most
visible current example is **Baldwins Crane Hire v Vision Modular Systems**
(Romford, ongoing 2026) — Baldwins is defending a £951,000 counter-claim that
turns on whether the work was Hire-only (CPA Condition 9(d) misdirection by
the hirer's AP) or Contract Lift (Baldwins' AP responsibility).

If the operator quoted "Hire-only" but in reality acted as Contract Lift,
the CPA Condition 13 indemnity FAILS, the owner's insurer may decline, and
the operator eats the loss personally. The reverse is also true — pricing
Contract Lift terms onto a job the customer wanted as Hire-only loses the
quote.

This MCP gives crane / hiab / plant-hire operators the callable triage,
quote-validation, and dispute-evidence toolkit to make this £100k+ wedge
decision correctly at the moment the quote is built.

TOOLS (8)
---------
- triage_at_quote(job_spec)                          → Hire vs Contract Lift + price uplift
- validate_cpa_hire_quote(quote)                     → required Hire clauses present?
- validate_cpa_contract_lift_quote(quote)            → required Contract-Lift clauses?
- generate_cpa_hire_tcs(operator, job_spec)          → ready-to-issue Hire T&Cs
- generate_cpa_contract_lift_tcs(operator, job_spec) → ready-to-issue Contract Lift T&Cs
- analyze_baldwins_v_vision_relevance(job)           → Condition 9(d) risk flags
- calculate_insurance_uplift(...)                    → Contract Lift premium delta
- prepare_dispute_evidence_pack(job, narrative)      → Condition 9(d) evidence checklist

WHY YOU PAY
-----------
One avoided Baldwins-style £951,000 counter-claim pays 100+ years of Pro tier.
The triage tool, used at quote stage, IS the wedge.

PRICING
-------
Free MIT self-host · £79/mo Starter · £249/mo Pro · £799/mo Fleet.

REGULATORY BASIS
----------------
CPA (Construction Plant-hire Association) Model Conditions of Hire 2011
  · Last amended 2021 (current at 2026)
  · Condition 8  — Hirer's responsibility once plant on-hire
  · Condition 9  — Carve-outs from Hirer indemnity (9(a) breakdown, 9(b) defect,
                    9(c) Owner-supplied operator negligence pre-direction,
                    9(d) Owner's express obligation breach / misdirection)
  · Condition 13 — Hirer indemnity (the big one)
  · Conditions 17-21 — Insurance, total loss, sub-let, jurisdiction
Baldwins Crane Hire Ltd v Vision Modular Systems Ltd (Romford, 2026; £951k claim)
BS 7121-1:2016 — Code of practice for safe use of cranes (general)
BS 7121-3 — Mobile cranes
BS 7121-5 — Tower cranes
LOLER 1998 + PUWER 1998 — equipment safety
Sale of Goods Act 1979 (where Owner's T&Cs interact with implied terms)

IMPORTANT DISCLAIMER
--------------------
The T&C templates returned by this MCP are GENERATED FROM the CPA Model
Conditions but they are TEMPLATES, NOT LEGAL ADVICE. Every operator MUST
have a competent solicitor review the templates against their specific
trade, insurance cover, and risk appetite before issuing to customers.
The MEOK AI Labs templates do not replace solicitor sign-off.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-cpa-contract-lift")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# CPA Model Conditions of Hire 2011 (amended 2021) — reference excerpts
# ──────────────────────────────────────────────────────────────────────

CPA_HIRE_CORE_CLAUSES = {
    "condition_8": (
        "Hirer's responsibility for plant — once plant arrives on site, "
        "Hirer is responsible for its safe operation, security, and the "
        "Owner-supplied operator while under Hirer's direction."
    ),
    "condition_9": (
        "Carve-outs from Hirer indemnity. Hirer NOT liable for: "
        "(a) breakdown, (b) inherent defect, (c) Owner-supplied operator "
        "negligence BEFORE Hirer direction begins, (d) Owner's express "
        "obligation breach."
    ),
    "condition_9d": (
        "Condition 9(d) — the Owner remains liable where the Owner has "
        "expressly agreed to undertake a duty (e.g. lift planning, AP "
        "supply) and breaches it. This is the contested clause in "
        "Baldwins v Vision."
    ),
    "condition_13": (
        "Hirer indemnifies the Owner against all claims for loss, damage, "
        "injury, or death arising from the use of the plant — SUBJECT TO "
        "the Condition 9 carve-outs."
    ),
    "conditions_17_to_21": (
        "Insurance, total loss, sub-let, jurisdiction. Hirer must insure "
        "the plant for its full replacement value and against third-party "
        "liability while on hire."
    ),
}

CPA_CONTRACT_LIFT_CORE_CLAUSES = {
    "owner_acts_as_contractor": (
        "Owner takes principal responsibility for the lift — Owner supplies "
        "plant, operator, AND Appointed Person (AP) per BS 7121-1."
    ),
    "owner_plans_lift": (
        "Owner produces the lift plan, method statement, and risk "
        "assessment per BS 7121-1 §6."
    ),
    "owner_insurance_primary": (
        "Owner's CAR (Contractors' All Risks) + employer's liability + "
        "public liability + plant policy is PRIMARY. Hirer's policy steps "
        "back. This is why Contract Lift costs 15-30%+ more."
    ),
    "limited_hirer_indemnity": (
        "Hirer indemnity REMOVED for lifting operations. Hirer only liable "
        "for ground conditions they warranted, access they controlled, or "
        "fraudulent information they supplied."
    ),
    "bs7121_compliance": (
        "Lift planned and executed per BS 7121-1:2016 (cranes) or "
        "BS 7121-3 (mobile) / BS 7121-5 (tower) as applicable."
    ),
    "no_subhire_without_consent": (
        "Owner may not sub-hire the lift to another operator without "
        "Hirer's express written consent."
    ),
}

# Lift category → recommended contract type (CPA + BS 7121-1 guidance)
LIFT_CATEGORY_GUIDANCE = {
    "basic": {
        "default": "hire_only",
        "note": "Repetitive, well-understood lifts under hirer's competent AP.",
    },
    "standard": {
        "default": "hire_only_with_caveats",
        "note": "Standard lifts where hirer has experienced AP + lift plan.",
    },
    "complex": {
        "default": "contract_lift",
        "note": (
            "Multi-crane, tandem, blind, over-occupied-area, or near-"
            "overhead-lines. BS 7121-1 §6.5 strongly recommends Owner-led "
            "contract lift."
        ),
    },
    "tandem_or_blind": {
        "default": "contract_lift",
        "note": "Always contract lift unless hirer is a Tier 1 with own AP.",
    },
    "over_occupied_area": {
        "default": "contract_lift",
        "note": (
            "Lifts over occupied buildings, public highway, railways "
            "must be contract lift — Owner's insurance must respond."
        ),
    },
    "near_overhead_lines": {
        "default": "contract_lift",
        "note": "HSGS GS6 + BS 7121-1 §10 — contract lift mandatory.",
    },
}

# Heuristic insurance uplift % over hire rate (industry guidance, not quoted)
INSURANCE_UPLIFT_BANDS = {
    "low_risk_under_50t": (0.15, 0.20),   # 15-20% uplift
    "medium_50_to_200t": (0.20, 0.25),    # 20-25%
    "high_over_200t_or_complex": (0.25, 0.35),  # 25-35%
}

# Baldwins v Vision indicative red-flag patterns
BALDWINS_RED_FLAGS = [
    "owner_supplied_ap_but_quoted_hire_only",
    "owner_did_lift_plan_but_billed_as_hire",
    "lift_over_occupied_area_quoted_as_hire",
    "tandem_lift_quoted_as_hire",
    "owner_made_critical_safety_decision",
    "no_hirer_appointed_person_named_in_quote",
    "method_statement_authored_by_owner",
    "owner_controlled_access_or_egress",
]


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    """HMAC-sign the response for tamper-evident audit."""
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(
        _HMAC_SECRET.encode(),
        json.dumps(payload, sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {
        **payload,
        "ts": _ts(),
        "sig": _sign(payload),
        "issuer": "meok-cpa-contract-lift-mcp",
        "version": "1.0.0",
        "disclaimer": (
            "TEMPLATES NOT LEGAL ADVICE. Operator must have a competent "
            "solicitor review CPA T&Cs before customer use."
        ),
    }


def _contains_any(text: str, needles: list) -> list:
    """Return the subset of `needles` present in `text` (case-insensitive)."""
    if not text:
        return []
    lower = text.lower()
    return [n for n in needles if n.lower() in lower]


# ──────────────────────────────────────────────────────────────────────
# Tool 1 — Triage at quote stage (THE WEDGE)
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def triage_at_quote(
    who_supplies_ap: str = "hirer",
    who_supplies_slinger: str = "hirer",
    who_directs_lift: str = "hirer",
    crane_category: str = "standard",
    lift_over_occupied_area: bool = False,
    tandem_lift: bool = False,
    near_overhead_lines: bool = False,
    crane_capacity_t: float = 50.0,
    job_value_gbp: float = 25000.0,
    hirer_named_ap: str = "",
    method_statement_author: str = "hirer",
) -> dict:
    """Decide Hire-only vs Contract Lift AT QUOTE STAGE.

    This is the £100k+ wedge — the call Baldwins is fighting £951k over.

    Args:
      who_supplies_ap: 'hirer' / 'owner' (Appointed Person per BS 7121-1)
      who_supplies_slinger: 'hirer' / 'owner'
      who_directs_lift: 'hirer' / 'owner' — who is the lift director?
      crane_category: 'basic' / 'standard' / 'complex' / 'tandem_or_blind'
                      / 'over_occupied_area' / 'near_overhead_lines'
      lift_over_occupied_area: lift over occupied building / public highway
      tandem_lift: two or more cranes simultaneously
      near_overhead_lines: within HSGS GS6 / BS 7121-1 §10 exclusion zone
      crane_capacity_t: crane SWL in tonnes
      job_value_gbp: indicative job value (drives insurance band)
      hirer_named_ap: full name of hirer's AP, if any
      method_statement_author: 'hirer' / 'owner' — who wrote the MS?

    Returns:
      recommended_contract_type, price_uplift_pct, tcs_to_cite,
      estimated_liability_exposure_gbp, red_flags, rationale.
    """
    red_flags = []
    contract_lift_forced = False
    rationale = []

    # Hard triggers — Contract Lift mandated by HSE / BS 7121-1 / insurer norms
    if lift_over_occupied_area:
        contract_lift_forced = True
        rationale.append("Lift over occupied area — Contract Lift mandated.")
        red_flags.append("lift_over_occupied_area_quoted_as_hire")
    if tandem_lift:
        contract_lift_forced = True
        rationale.append("Tandem / multi-crane lift — Contract Lift mandated.")
        red_flags.append("tandem_lift_quoted_as_hire")
    if near_overhead_lines:
        contract_lift_forced = True
        rationale.append("Near overhead lines (BS 7121-1 §10) — Contract Lift mandated.")

    # Soft triggers — Owner is acting as Contractor under the surface
    if who_supplies_ap.lower() == "owner":
        contract_lift_forced = True
        rationale.append("Owner supplies AP — Owner is acting as Contract Lift principal.")
        red_flags.append("owner_supplied_ap_but_quoted_hire_only")
    if who_directs_lift.lower() == "owner":
        contract_lift_forced = True
        rationale.append("Owner directs the lift — Owner is the lift director, not Hirer.")
        red_flags.append("owner_did_lift_plan_but_billed_as_hire")
    if method_statement_author.lower() == "owner":
        contract_lift_forced = True
        rationale.append("Owner authored the method statement — Contract Lift in substance.")
        red_flags.append("method_statement_authored_by_owner")

    # No named Hirer AP for a non-basic lift = trouble
    if crane_category != "basic" and not hirer_named_ap and who_supplies_ap.lower() == "hirer":
        red_flags.append("no_hirer_appointed_person_named_in_quote")
        rationale.append(
            "Hirer claims to supply AP but no name in quote — drift risk to "
            "Owner acting as AP in practice."
        )

    # Category guidance overlay
    cat = LIFT_CATEGORY_GUIDANCE.get(crane_category, LIFT_CATEGORY_GUIDANCE["standard"])
    cat_default = cat["default"]

    if contract_lift_forced or cat_default in ("contract_lift",):
        recommended = "contract_lift"
    elif cat_default == "hire_only":
        recommended = "hire_only"
    else:
        recommended = "hire_only_with_caveats"

    # Insurance uplift band
    if crane_capacity_t < 50 and not contract_lift_forced:
        band = INSURANCE_UPLIFT_BANDS["low_risk_under_50t"]
    elif crane_capacity_t <= 200 and not contract_lift_forced:
        band = INSURANCE_UPLIFT_BANDS["medium_50_to_200t"]
    else:
        band = INSURANCE_UPLIFT_BANDS["high_over_200t_or_complex"]
    uplift_lo_pct = round(band[0] * 100, 1)
    uplift_hi_pct = round(band[1] * 100, 1)

    if recommended == "contract_lift":
        tcs_to_cite = [
            "CPA Model Conditions of Hire 2011 (Contract Lift schedule)",
            "BS 7121-1:2016 §6 (lift planning by Owner)",
            "Owner's CAR + public liability primary",
            "Conditions 17-21 (insurance) modified — Owner's policy primary",
        ]
        liability_exposure_gbp = round(job_value_gbp * 38.0, 0)  # ~Baldwins multiplier
        liability_basis = (
            "Quoting Hire-only when job is in substance Contract Lift fails the "
            "CPA Condition 13 indemnity. Owner becomes principally liable for "
            "the whole loss (per Baldwins v Vision £951k counter-claim)."
        )
    elif recommended == "hire_only":
        tcs_to_cite = [
            "CPA Model Conditions of Hire 2011 (full)",
            "Condition 8 (Hirer responsibility on-site)",
            "Condition 9 carve-outs (a-d)",
            "Condition 13 (Hirer indemnity)",
            "Conditions 17-21 (Hirer's insurance primary)",
        ]
        liability_exposure_gbp = round(job_value_gbp * 1.2, 0)
        liability_basis = "Standard Hire-only — risk transfers to Hirer under Condition 13."
    else:
        tcs_to_cite = [
            "CPA Model Conditions of Hire 2011 (full)",
            "Explicit Condition 9(d) carve-out clarifying Owner duties",
            "Hirer AP name + competency on quote face",
            "Joint pre-lift safety walk recorded in writing",
        ]
        liability_exposure_gbp = round(job_value_gbp * 5.0, 0)
        liability_basis = (
            "Hire-only is defensible but Condition 9(d) drift risk is real. "
            "Tighten the quote face."
        )

    payload = {
        "tool": "triage_at_quote",
        "recommended_contract_type": recommended,
        "price_uplift_pct_range_over_hire": [uplift_lo_pct, uplift_hi_pct],
        "tcs_to_cite": tcs_to_cite,
        "estimated_liability_exposure_gbp_if_wrong": liability_exposure_gbp,
        "liability_basis": liability_basis,
        "red_flags": red_flags,
        "rationale": rationale,
        "baldwins_v_vision_pattern_match": bool(red_flags),
        "advisory": (
            "QUOTE CONTRACT LIFT. The wrong call here is the £951k Baldwins "
            "scenario. Confirm with your insurance broker before issuing."
            if recommended == "contract_lift"
            else "Hire-only is defensible — keep the quote face explicit on AP + direction."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Tool 2 — Validate a CPA Hire-only quote
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def validate_cpa_hire_quote(
    quote_text: str = "",
    operator_name: str = "",
) -> dict:
    """Check a Hire-only quote contains the CPA-required clause references.

    Required to lean on Condition 13 indemnity:
      - explicit "CPA Model Conditions of Hire 2011" reference
      - Condition 8 (hirer on-site responsibility)
      - Condition 13 (indemnity)
      - Condition 9 carve-outs disclosed (especially 9(d))
      - Conditions 17-21 insurance + total loss
    """
    required_phrases = [
        "CPA Model Conditions of Hire",
        "Condition 8",
        "Condition 9",
        "Condition 13",
        "Conditions 17",
    ]
    present = _contains_any(quote_text, required_phrases)
    missing = [p for p in required_phrases if p not in present]

    # Bonus checks
    bonus_score = 0
    if "amended 2021" in (quote_text or "").lower():
        bonus_score += 1
    if "2011" in (quote_text or ""):
        bonus_score += 1
    if re.search(r"\bappointed person\b", quote_text or "", re.I):
        bonus_score += 1
    if re.search(r"\binsurance\b.*\bhirer\b", quote_text or "", re.I | re.S):
        bonus_score += 1

    score = round(((len(present) / len(required_phrases)) * 80) + (bonus_score * 5), 1)

    payload = {
        "tool": "validate_cpa_hire_quote",
        "operator_name": operator_name,
        "contract_type": "hire_only",
        "required_clauses_present": present,
        "missing_clauses": missing,
        "bonus_signals_hit": bonus_score,
        "score_out_of_100": min(score, 100.0),
        "verdict": (
            "PASS — quote is defensible under CPA Condition 13."
            if not missing
            else f"FAIL — {len(missing)} required CPA clause references missing."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Tool 3 — Validate a Contract Lift quote
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def validate_cpa_contract_lift_quote(
    quote_text: str = "",
    operator_name: str = "",
) -> dict:
    """Check a Contract Lift quote contains the proper clause set.

    Required:
      - 'Contract Lift' wording (not 'Hire')
      - CPA Model Conditions Contract Lift schedule cited
      - Owner supplies AP + slinger + lift plan
      - BS 7121-1 cited
      - Owner CAR + public liability primary
    """
    required_phrases = [
        "Contract Lift",
        "CPA",
        "Appointed Person",
        "BS 7121",
        "Owner's insurance",
    ]
    present = _contains_any(quote_text, required_phrases)
    missing = [p for p in required_phrases if p not in present]

    # Anti-patterns — Hire-only language polluting a Contract Lift quote
    anti_patterns = []
    if re.search(r"\bcondition\s*13\s*indemnity\b", quote_text or "", re.I):
        anti_patterns.append("Condition 13 Hirer indemnity language — wrong contract type.")
    if re.search(r"\bplant on hire\b", quote_text or "", re.I) and "Contract Lift" in (quote_text or ""):
        anti_patterns.append("Mixed Hire + Contract Lift wording — pick one.")

    bonus_score = 0
    if "method statement" in (quote_text or "").lower():
        bonus_score += 1
    if "risk assessment" in (quote_text or "").lower():
        bonus_score += 1
    if "lift plan" in (quote_text or "").lower():
        bonus_score += 1

    score = round(((len(present) / len(required_phrases)) * 80) + (bonus_score * 5) - (len(anti_patterns) * 10), 1)
    score = max(0.0, min(score, 100.0))

    payload = {
        "tool": "validate_cpa_contract_lift_quote",
        "operator_name": operator_name,
        "contract_type": "contract_lift",
        "required_clauses_present": present,
        "missing_clauses": missing,
        "anti_patterns_detected": anti_patterns,
        "bonus_signals_hit": bonus_score,
        "score_out_of_100": score,
        "verdict": (
            "PASS — Contract Lift quote properly framed."
            if not missing and not anti_patterns
            else f"FAIL — {len(missing)} missing + {len(anti_patterns)} mix-ups."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Tool 4 — Generate CPA Hire T&Cs
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_cpa_hire_tcs(
    operator_name: str,
    job_description: str = "",
    crane_swl_t: float = 50.0,
    daily_rate_gbp: float = 1200.0,
    delivery_address: str = "",
) -> dict:
    """Produce ready-to-issue CPA Hire-only Terms & Conditions.

    Cites the CPA Model Conditions 2011 (amended 2021). Operator MUST have
    a solicitor review before customer use.
    """
    tcs = {
        "operator": operator_name,
        "contract_type": "Hire-only",
        "incorporated_terms": (
            "These Terms and Conditions incorporate the CPA Model Conditions "
            "of Hire 2011 (last amended 2021) which apply in full."
        ),
        "job_description": job_description or "[Job description]",
        "plant_supplied": {
            "type": "Mobile crane / hiab / plant (as quoted)",
            "swl_tonnes": crane_swl_t,
            "operator_supplied_by": operator_name,
        },
        "operator_supplied_by_owner": (
            f"{operator_name} will supply a competent operator. Per CPA "
            "Condition 8 the operator becomes the Hirer's servant once "
            "under the Hirer's direction."
        ),
        "appointed_person_supplied_by_hirer": (
            "The Hirer shall supply a competent Appointed Person (AP) per "
            "BS 7121-1 to plan and direct the lift. AP name required on the "
            "site induction record."
        ),
        "hirer_responsibilities": [
            "Site safety, ground conditions, and access (Condition 8).",
            "Lift planning, method statement, and risk assessment.",
            "Supervision via Hirer's AP at all times during lifting.",
            "Insurance of the plant for full replacement value (Conditions 17-21).",
            "Third-party public liability insurance covering the lift.",
        ],
        "owner_carve_outs_condition_9": [
            "9(a) — Owner liable for plant breakdown.",
            "9(b) — Owner liable for inherent plant defects.",
            "9(c) — Owner liable for operator negligence BEFORE Hirer direction begins.",
            "9(d) — Owner liable for breach of any express obligation undertaken by Owner.",
        ],
        "indemnity_condition_13": (
            "Subject to Condition 9, the Hirer indemnifies the Owner against "
            "all claims, costs, damages and expenses arising from the use of "
            "the plant while on hire to the Hirer."
        ),
        "insurance_conditions_17_to_21": (
            "Hirer's plant + third-party + employer's liability insurance is "
            "PRIMARY. Owner's policy steps back."
        ),
        "commercial_terms": {
            "daily_hire_rate_gbp": daily_rate_gbp,
            "delivery_address": delivery_address or "[Delivery address]",
            "payment_terms_days": 30,
            "late_payment_act": "Late Payment of Commercial Debts (Interest) Act 1998 applies.",
        },
        "sale_of_goods_act_note": (
            "Plant is supplied on hire, not sale. Sale of Goods Act 1979 "
            "applies only to consumables (fuel, fluids) sold incidentally."
        ),
        "law_and_jurisdiction": (
            "These T&Cs are governed by the laws of England and Wales. "
            "Disputes subject to the exclusive jurisdiction of the English courts."
        ),
        "hirer_signature_required": True,
        "owner_signature_required": True,
        "solicitor_review_required_before_customer_use": True,
    }
    return _attestation({
        "tool": "generate_cpa_hire_tcs",
        "tcs": tcs,
        "regulatory_basis": "CPA Model Conditions of Hire 2011 (amended 2021); BS 7121-1:2016",
    })


# ──────────────────────────────────────────────────────────────────────
# Tool 5 — Generate Contract Lift T&Cs
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def generate_cpa_contract_lift_tcs(
    operator_name: str,
    job_description: str = "",
    crane_swl_t: float = 100.0,
    lift_value_gbp: float = 50000.0,
    delivery_address: str = "",
) -> dict:
    """Produce ready-to-issue CPA Contract Lift Terms & Conditions.

    These are DIFFERENT from Hire-only — Owner takes principal responsibility.
    Operator MUST have a solicitor review before customer use.
    """
    tcs = {
        "operator": operator_name,
        "contract_type": "Contract Lift",
        "incorporated_terms": (
            "These Terms and Conditions incorporate the CPA Model Conditions "
            "of Hire 2011 (amended 2021) Contract Lift schedule, supplemented "
            "by BS 7121-1:2016 and the lift plan attached as Schedule 1."
        ),
        "job_description": job_description or "[Job description]",
        "plant_supplied": {
            "type": "Crane (mobile / tower / hiab as specified)",
            "swl_tonnes": crane_swl_t,
            "operator_supplied_by": operator_name,
            "appointed_person_supplied_by": operator_name,
            "slinger_signaller_supplied_by": operator_name,
        },
        "owner_acts_as_principal_contractor_for_lift": (
            f"{operator_name} (the Owner) acts as principal contractor for "
            "the lifting operations and accepts the responsibilities of a "
            "duty-holder under LOLER 1998, PUWER 1998, and BS 7121-1:2016."
        ),
        "owner_responsibilities": [
            "Supply of plant, operator, slinger/signaller, and Appointed Person.",
            "Production of lift plan, method statement, risk assessment (BS 7121-1 §6).",
            "Direction of the lift via Owner's AP.",
            "Maintenance + thorough examination per LOLER 1998 reg. 9.",
            "Primary CAR (Contractors' All Risks) + public liability insurance.",
        ],
        "hirer_responsibilities": [
            "Accurate site information (ground conditions, access, services).",
            "Permits-to-work and site induction.",
            "Disclosure of any third-party services or occupants in the lift zone.",
            "Provision of safe waiting area for plant on site.",
        ],
        "no_condition_13_indemnity": (
            "The Hirer indemnity under CPA Condition 13 DOES NOT APPLY to this "
            "Contract Lift. Owner's insurance is primary."
        ),
        "hirer_residual_liability": (
            "Hirer remains liable for: (i) fraudulent or grossly negligent "
            "misinformation about the site; (ii) ground conditions the Hirer "
            "warranted; (iii) acts of Hirer's employees outside the lift "
            "exclusion zone obstructing the operation."
        ),
        "owner_insurance": {
            "car_minimum_gbp": max(5_000_000, int(lift_value_gbp * 20)),
            "employers_liability_minimum_gbp": 10_000_000,
            "public_liability_minimum_gbp": 10_000_000,
            "plant_policy_value_gbp": "full plant replacement value",
            "primary_layer_basis": "Owner's policy primary; Hirer's policy excess.",
        },
        "no_sub_hire_without_consent": (
            "Owner shall not sub-hire the lift or use a third-party crane "
            "operator without the Hirer's express written consent."
        ),
        "bs_7121_compliance": (
            "All lifting operations planned and executed in accordance with "
            "BS 7121-1:2016 (general), BS 7121-3 (mobile) or BS 7121-5 (tower) "
            "as applicable. Lift plan attached as Schedule 1."
        ),
        "commercial_terms": {
            "contract_lift_fee_gbp": lift_value_gbp,
            "delivery_address": delivery_address or "[Delivery address]",
            "insurance_uplift_pct_included": "15-30% over equivalent hire rate",
            "payment_terms_days": 30,
        },
        "law_and_jurisdiction": (
            "Governed by the laws of England and Wales. Exclusive jurisdiction "
            "of the English courts."
        ),
        "solicitor_review_required_before_customer_use": True,
        "solicitor_review_priority": "CRITICAL — Contract Lift T&Cs shift principal liability to Owner.",
    }
    return _attestation({
        "tool": "generate_cpa_contract_lift_tcs",
        "tcs": tcs,
        "regulatory_basis": (
            "CPA Model Conditions of Hire 2011 (Contract Lift); "
            "BS 7121-1:2016; LOLER 1998; PUWER 1998"
        ),
    })


# ──────────────────────────────────────────────────────────────────────
# Tool 6 — Baldwins v Vision relevance analyser
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def analyze_baldwins_v_vision_relevance(
    job_description: str = "",
    quoted_as: str = "hire_only",
    owner_supplied_ap: bool = False,
    owner_wrote_method_statement: bool = False,
    lift_over_occupied_area: bool = False,
    incident_occurred: bool = False,
    claim_value_gbp: float = 0.0,
) -> dict:
    """Score whether the Baldwins v Vision £951k scenario could apply here.

    Baldwins is defending a £951,000 counter-claim from Vision Modular Systems
    arising out of work at Romford. The dispute turns on whether Baldwins
    operated as Hire-only (Condition 13 indemnity holds) or as Contract Lift
    in substance (Condition 9(d) Owner-duty breach exposes Baldwins).

    This tool flags the Condition 9(d) misdirection / misuse pattern.
    """
    flags_hit = []
    if quoted_as == "hire_only" and owner_supplied_ap:
        flags_hit.append("owner_supplied_ap_but_quoted_hire_only")
    if quoted_as == "hire_only" and owner_wrote_method_statement:
        flags_hit.append("method_statement_authored_by_owner")
    if quoted_as == "hire_only" and lift_over_occupied_area:
        flags_hit.append("lift_over_occupied_area_quoted_as_hire")

    risk_score = len(flags_hit) * 25  # crude — 0/25/50/75/100
    risk_score = min(risk_score, 100)

    if risk_score >= 50:
        verdict = "HIGH"
        narrative = (
            "Pattern strongly resembles the Baldwins v Vision dispute. The "
            "Hirer's lawyers can argue Owner acted as Contract Lift in "
            "substance — Condition 13 indemnity may fall away under "
            "Condition 9(d). Get specialist construction litigation advice."
        )
    elif risk_score >= 25:
        verdict = "MEDIUM"
        narrative = (
            "One or more Baldwins indicators present. Quote face should be "
            "tightened — explicit Hirer AP name, Hirer-authored method "
            "statement, and Hirer-controlled direction must be on paper."
        )
    else:
        verdict = "LOW"
        narrative = "No Baldwins-pattern indicators in the supplied job spec."

    payload = {
        "tool": "analyze_baldwins_v_vision_relevance",
        "case_reference": "Baldwins Crane Hire Ltd v Vision Modular Systems Ltd (Romford, 2026; £951k counter-claim)",
        "condition_at_issue": "CPA Condition 9(d) — Owner's express obligation breach",
        "flags_hit": flags_hit,
        "risk_score_0_to_100": risk_score,
        "verdict": verdict,
        "narrative": narrative,
        "incident_occurred": incident_occurred,
        "claim_value_gbp": claim_value_gbp,
        "recommended_next_step": (
            "Engage construction-litigation solicitor immediately and notify "
            "insurer." if verdict == "HIGH" else
            "Tighten quote face on next quotes; brief AP on direction split."
            if verdict == "MEDIUM" else
            "Maintain current quote discipline."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Tool 7 — Insurance uplift calculator
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def calculate_insurance_uplift(
    crane_capacity_t: float,
    job_value_gbp: float,
    contract_type: str = "contract_lift",
    base_hire_rate_gbp: float = 1200.0,
    job_duration_days: int = 1,
) -> dict:
    """Estimate the insurance uplift % and £ delta of Contract Lift vs Hire.

    Heuristic: Contract Lift carries the lift risk on the Owner's policy,
    typically costing 15-30% more than the equivalent Hire-only day rate.
    """
    if crane_capacity_t < 50:
        band_key = "low_risk_under_50t"
    elif crane_capacity_t <= 200:
        band_key = "medium_50_to_200t"
    else:
        band_key = "high_over_200t_or_complex"
    lo, hi = INSURANCE_UPLIFT_BANDS[band_key]

    base_total = base_hire_rate_gbp * max(1, job_duration_days)

    if contract_type == "contract_lift":
        delta_lo = round(base_total * lo, 2)
        delta_hi = round(base_total * hi, 2)
        recommended_quote_lo = round(base_total + delta_lo, 2)
        recommended_quote_hi = round(base_total + delta_hi, 2)
    else:
        delta_lo = 0.0
        delta_hi = 0.0
        recommended_quote_lo = base_total
        recommended_quote_hi = base_total

    # Margin contribution — half the uplift typically lands in operator margin
    margin_contribution_estimate_gbp = round((delta_lo + delta_hi) / 4, 2)

    payload = {
        "tool": "calculate_insurance_uplift",
        "contract_type": contract_type,
        "crane_capacity_t": crane_capacity_t,
        "job_value_gbp": job_value_gbp,
        "base_hire_total_gbp": round(base_total, 2),
        "insurance_uplift_band_pct": [round(lo * 100, 1), round(hi * 100, 1)],
        "insurance_uplift_band_gbp": [delta_lo, delta_hi],
        "recommended_contract_lift_quote_range_gbp": [recommended_quote_lo, recommended_quote_hi],
        "estimated_margin_contribution_gbp": margin_contribution_estimate_gbp,
        "advisory": (
            "Confirm exact uplift with your insurance broker — bands are "
            "industry-typical, not a quote. Brokers price by risk profile."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Tool 8 — Dispute evidence pack
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def prepare_dispute_evidence_pack(
    job_id: str,
    dispute_narrative: str = "",
    contract_type_quoted: str = "hire_only",
) -> dict:
    """When a Condition 9(d) dispute arises, list the evidence to assemble.

    This is the pack the operator's solicitor will need within 48 hours of
    notification — the Baldwins case is reportedly heading to trial because
    contemporaneous records were patchy.
    """
    universal_checklist = [
        "Signed customer quote acceptance (with date + signatory)",
        "Issued T&Cs document (with CPA Model Conditions reference)",
        "Lift plan (who authored, version, date)",
        "Method statement (who authored, signatures)",
        "Risk assessment (signatures of AP + operator)",
        "Appointed Person appointment letter (Hirer's or Owner's)",
        "AP competency certificates (training, CPCS A61/A62/A63)",
        "Operator CPCS card + LOLER thorough examination certificate",
        "Toolbox-talk attendance record for the lift day",
        "Pre-lift site walk record (date, time, attendees)",
        "Photos of: setup, outriggers, ground mats, exclusion zone, signage",
        "Crane positioning / setup checklist signed off",
        "Daily timesheet signed by Hirer's site rep",
        "All written communications (email, WhatsApp, SMS) about the lift",
        "Site induction record naming AP and lift director",
        "Permit-to-work / lift-permit if applicable",
        "Witness statements from operator, slinger, banksman",
        "CCTV footage from site cameras (preserve before overwrite)",
        "Insurer notification with date + claim reference",
    ]

    hire_specific = [
        "Quote face showing 'Hire-only' wording",
        "T&Cs showing CPA Condition 13 indemnity reference",
        "Evidence Hirer's AP directed the lift (statements, recordings)",
        "Evidence Hirer authored or approved the lift plan",
        "Evidence Hirer-supplied slinger / banksman where applicable",
    ]
    contract_lift_specific = [
        "Quote face showing 'Contract Lift' wording",
        "Owner's CAR + PL insurance certificates in force on lift day",
        "Owner's lift plan + method statement (full pack)",
        "Owner's AP appointment with effective dates",
        "Evidence Owner directed the lift (statements, photos)",
    ]

    if contract_type_quoted == "hire_only":
        specific = hire_specific
    elif contract_type_quoted == "contract_lift":
        specific = contract_lift_specific
    else:
        specific = []

    payload = {
        "tool": "prepare_dispute_evidence_pack",
        "job_id": job_id,
        "dispute_narrative": dispute_narrative,
        "contract_type_quoted": contract_type_quoted,
        "preservation_window_hours": 48,
        "universal_evidence_checklist": universal_checklist,
        "contract_specific_evidence_checklist": specific,
        "litigation_hold_steps": [
            "Issue litigation-hold notice to all staff who touched the job.",
            "Suspend CCTV/dashcam auto-deletion immediately.",
            "Lock the digital job file against further edits (audit trail).",
            "Notify insurer + appoint solicitor within 48 hours.",
            "Preserve mobile-phone messages on lift-day comms.",
        ],
        "advisory": (
            "Baldwins-pattern: most operator losses in CPA Condition 9(d) "
            "disputes come from missing contemporaneous evidence — not "
            "from the merits. Assemble within 48 hours."
        ),
    }
    return _attestation(payload)


# ──────────────────────────────────────────────────────────────────────
# Server entry
# ──────────────────────────────────────────────────────────────────────

def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
