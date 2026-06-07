"""Tests for meok-cpa-contract-lift-mcp.

≥15 tests covering:
  - The £100k+ wedge: triage right vs wrong on the Baldwins-pattern job
  - Hire-only vs Contract Lift T&Cs MUST differ
  - HMAC chain attestation
  - Each of the 8 tools at least once
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    triage_at_quote,
    validate_cpa_hire_quote,
    validate_cpa_contract_lift_quote,
    generate_cpa_hire_tcs,
    generate_cpa_contract_lift_tcs,
    analyze_baldwins_v_vision_relevance,
    calculate_insurance_uplift,
    prepare_dispute_evidence_pack,
    CPA_HIRE_CORE_CLAUSES,
    CPA_CONTRACT_LIFT_CORE_CLAUSES,
    LIFT_CATEGORY_GUIDANCE,
    INSURANCE_UPLIFT_BANDS,
    BALDWINS_RED_FLAGS,
)


def _call(tool, **kwargs):
    """FastMCP wraps tools as Tool objects — extract the callable."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    return fn(**kwargs)


# ──────────────────────────────────────────────────────────────────────
# Tool 1 — triage_at_quote (THE £100k+ WEDGE)
# ──────────────────────────────────────────────────────────────────────

def test_triage_baldwins_pattern_forces_contract_lift():
    """The £100k+ wedge — the EXACT Baldwins-pattern job MUST trigger Contract Lift."""
    r = _call(
        triage_at_quote,
        who_supplies_ap="owner",
        who_directs_lift="owner",
        crane_category="complex",
        lift_over_occupied_area=True,
        method_statement_author="owner",
        crane_capacity_t=130.0,
        job_value_gbp=25_000.0,
    )
    assert r["recommended_contract_type"] == "contract_lift"
    assert r["baldwins_v_vision_pattern_match"] is True
    assert "owner_supplied_ap_but_quoted_hire_only" in r["red_flags"]
    assert "lift_over_occupied_area_quoted_as_hire" in r["red_flags"]
    # Liability exposure on a wrong call should be ≥ £100k (the wedge)
    assert r["estimated_liability_exposure_gbp_if_wrong"] >= 100_000


def test_triage_clean_basic_job_is_hire_only():
    """Healthy basic job: Hirer AP, Hirer directs, normal yard lift = Hire-only."""
    r = _call(
        triage_at_quote,
        who_supplies_ap="hirer",
        who_directs_lift="hirer",
        crane_category="basic",
        lift_over_occupied_area=False,
        tandem_lift=False,
        crane_capacity_t=30.0,
        job_value_gbp=2_500.0,
        hirer_named_ap="J. Hirer (CPCS A61)",
        method_statement_author="hirer",
    )
    assert r["recommended_contract_type"] == "hire_only"
    assert r["red_flags"] == []
    # Low exposure
    assert r["estimated_liability_exposure_gbp_if_wrong"] < 10_000


def test_triage_tandem_lift_always_contract_lift():
    r = _call(
        triage_at_quote,
        who_supplies_ap="hirer",
        who_directs_lift="hirer",
        crane_category="standard",
        tandem_lift=True,
        crane_capacity_t=80.0,
    )
    assert r["recommended_contract_type"] == "contract_lift"
    assert "tandem_lift_quoted_as_hire" in r["red_flags"]


def test_triage_near_overhead_lines_forces_contract_lift():
    r = _call(
        triage_at_quote,
        who_supplies_ap="hirer",
        who_directs_lift="hirer",
        crane_category="standard",
        near_overhead_lines=True,
    )
    assert r["recommended_contract_type"] == "contract_lift"


def test_triage_wedge_value_differs_dramatically_on_wrong_call():
    """The whole reason this MCP exists — wrong-call exposure ≥ £100k vs right-call < £10k."""
    wrong_call = _call(
        triage_at_quote,
        who_supplies_ap="owner",
        who_directs_lift="owner",
        lift_over_occupied_area=True,
        crane_category="over_occupied_area",
        crane_capacity_t=200.0,
        job_value_gbp=30_000.0,
    )
    right_call = _call(
        triage_at_quote,
        who_supplies_ap="hirer",
        who_directs_lift="hirer",
        crane_category="basic",
        crane_capacity_t=25.0,
        job_value_gbp=2_000.0,
        hirer_named_ap="K. Smith",
    )
    diff = (
        wrong_call["estimated_liability_exposure_gbp_if_wrong"]
        - right_call["estimated_liability_exposure_gbp_if_wrong"]
    )
    assert diff >= 100_000  # the £100k+ wedge stated in the brief


# ──────────────────────────────────────────────────────────────────────
# Tool 2 — validate_cpa_hire_quote
# ──────────────────────────────────────────────────────────────────────

def test_validate_hire_quote_pass_when_all_clauses_present():
    quote = (
        "Quote ref Q-2026-001. These T&Cs incorporate the CPA Model Conditions "
        "of Hire 2011 (amended 2021) in full. Condition 8 applies — Hirer "
        "responsible on-site. Condition 9 carve-outs disclosed. Condition 13 "
        "Hirer indemnity. Conditions 17-21 insurance. Hirer's Appointed Person."
    )
    r = _call(validate_cpa_hire_quote, quote_text=quote, operator_name="Test Cranes Ltd")
    assert r["verdict"].startswith("PASS")
    assert r["missing_clauses"] == []
    assert r["score_out_of_100"] >= 80


def test_validate_hire_quote_fails_on_missing_clauses():
    quote = "Quote ref Q-2026-002. Day rate £1000. Pay 30 days."
    r = _call(validate_cpa_hire_quote, quote_text=quote, operator_name="Bad Quote Ltd")
    assert r["verdict"].startswith("FAIL")
    assert len(r["missing_clauses"]) >= 3


# ──────────────────────────────────────────────────────────────────────
# Tool 3 — validate_cpa_contract_lift_quote
# ──────────────────────────────────────────────────────────────────────

def test_validate_contract_lift_quote_pass():
    quote = (
        "Contract Lift quote. CPA Model Conditions of Hire Contract Lift "
        "schedule applies. Owner supplies Appointed Person + slinger. "
        "BS 7121-1:2016 lift plan attached. Owner's insurance primary. "
        "Lift plan, method statement, risk assessment included."
    )
    r = _call(validate_cpa_contract_lift_quote, quote_text=quote, operator_name="Good CL Ltd")
    assert r["verdict"].startswith("PASS")
    assert r["missing_clauses"] == []


def test_validate_contract_lift_detects_anti_pattern():
    """A Contract Lift quote that still references Condition 13 indemnity = wrong type mixed in."""
    quote = (
        "Contract Lift quote. CPA conditions. BS 7121-1 lift plan. Appointed "
        "Person by Owner. Owner's insurance primary. Condition 13 indemnity applies."
    )
    r = _call(validate_cpa_contract_lift_quote, quote_text=quote, operator_name="Mixed Up Ltd")
    assert len(r["anti_patterns_detected"]) >= 1


# ──────────────────────────────────────────────────────────────────────
# Tool 4 + 5 — Hire T&Cs MUST DIFFER from Contract Lift T&Cs
# ──────────────────────────────────────────────────────────────────────

def test_hire_tcs_and_contract_lift_tcs_differ_materially():
    """The whole point — the two contract types produce DIFFERENT documents."""
    hire = _call(
        generate_cpa_hire_tcs,
        operator_name="Acme Cranes Ltd",
        job_description="50t crane day-hire",
        crane_swl_t=50.0,
        daily_rate_gbp=1200.0,
    )
    contract_lift = _call(
        generate_cpa_contract_lift_tcs,
        operator_name="Acme Cranes Ltd",
        job_description="Contract lift over occupied flats",
        crane_swl_t=130.0,
        lift_value_gbp=50_000.0,
    )

    hire_tcs = hire["tcs"]
    cl_tcs = contract_lift["tcs"]

    # Different contract types
    assert hire_tcs["contract_type"] == "Hire-only"
    assert cl_tcs["contract_type"] == "Contract Lift"

    # Hire: AP supplied by HIRER. Contract Lift: AP supplied by OWNER.
    assert "Hirer shall supply a competent Appointed Person" in hire_tcs["appointed_person_supplied_by_hirer"]
    assert cl_tcs["plant_supplied"]["appointed_person_supplied_by"] == "Acme Cranes Ltd"

    # Hire keeps Condition 13 indemnity (field exists + Hirer indemnifies Owner).
    # Contract Lift explicitly removes it.
    assert "indemnity_condition_13" in hire_tcs
    assert "Hirer indemnifies the Owner" in hire_tcs["indemnity_condition_13"]
    assert "indemnity_condition_13" not in cl_tcs
    assert "DOES NOT APPLY" in cl_tcs["no_condition_13_indemnity"]

    # Contract Lift has BS 7121 compliance section. Hire doesn't (it's the Hirer's job).
    assert "bs_7121_compliance" in cl_tcs
    assert "bs_7121_compliance" not in hire_tcs

    # Contract Lift has Owner's insurance section. Hire has Hirer's primary.
    assert cl_tcs["owner_insurance"]["primary_layer_basis"].startswith("Owner's policy primary")
    assert "Hirer's plant + third-party" in hire_tcs["insurance_conditions_17_to_21"]


def test_hire_tcs_cites_cpa_2011_amended_2021():
    r = _call(generate_cpa_hire_tcs, operator_name="Test Ltd")
    assert "2011" in r["tcs"]["incorporated_terms"]
    assert "2021" in r["tcs"]["incorporated_terms"]
    assert r["tcs"]["solicitor_review_required_before_customer_use"] is True


def test_contract_lift_tcs_includes_loler_puwer():
    r = _call(
        generate_cpa_contract_lift_tcs,
        operator_name="Test Ltd",
        lift_value_gbp=75_000.0,
    )
    txt = json.dumps(r["tcs"], default=str)
    assert "LOLER 1998" in txt
    assert "PUWER 1998" in txt
    assert "BS 7121-1" in txt
    assert r["tcs"]["solicitor_review_priority"].startswith("CRITICAL")


# ──────────────────────────────────────────────────────────────────────
# Tool 6 — analyze_baldwins_v_vision_relevance
# ──────────────────────────────────────────────────────────────────────

def test_baldwins_high_when_three_red_flags():
    r = _call(
        analyze_baldwins_v_vision_relevance,
        job_description="Modular lift to 3rd floor",
        quoted_as="hire_only",
        owner_supplied_ap=True,
        owner_wrote_method_statement=True,
        lift_over_occupied_area=True,
        incident_occurred=True,
        claim_value_gbp=951_000.0,
    )
    assert r["verdict"] == "HIGH"
    assert r["risk_score_0_to_100"] >= 50
    assert "951" in r["case_reference"] or "951" in str(r.get("claim_value_gbp", ""))
    assert "9(d)" in r["condition_at_issue"]


def test_baldwins_low_when_no_red_flags():
    r = _call(
        analyze_baldwins_v_vision_relevance,
        job_description="Yard lift, Hirer AP, Hirer MS, basic site",
        quoted_as="hire_only",
        owner_supplied_ap=False,
        owner_wrote_method_statement=False,
        lift_over_occupied_area=False,
    )
    assert r["verdict"] == "LOW"
    assert r["risk_score_0_to_100"] == 0


# ──────────────────────────────────────────────────────────────────────
# Tool 7 — calculate_insurance_uplift
# ──────────────────────────────────────────────────────────────────────

def test_insurance_uplift_contract_lift_50t_is_15_to_20_pct():
    r = _call(
        calculate_insurance_uplift,
        crane_capacity_t=45.0,
        job_value_gbp=20_000.0,
        contract_type="contract_lift",
        base_hire_rate_gbp=1000.0,
        job_duration_days=1,
    )
    lo_pct, hi_pct = r["insurance_uplift_band_pct"]
    assert lo_pct == 15.0
    assert hi_pct == 20.0
    # On £1000 base, uplift should be £150-£200
    assert r["insurance_uplift_band_gbp"][0] == 150.0
    assert r["insurance_uplift_band_gbp"][1] == 200.0


def test_insurance_uplift_high_capacity_higher_band():
    r = _call(
        calculate_insurance_uplift,
        crane_capacity_t=350.0,
        job_value_gbp=100_000.0,
        contract_type="contract_lift",
        base_hire_rate_gbp=5000.0,
        job_duration_days=3,
    )
    lo_pct, hi_pct = r["insurance_uplift_band_pct"]
    assert lo_pct >= 25.0  # high-band starts at 25%
    assert hi_pct <= 35.0


def test_insurance_uplift_hire_only_returns_zero_delta():
    r = _call(
        calculate_insurance_uplift,
        crane_capacity_t=50.0,
        job_value_gbp=10_000.0,
        contract_type="hire_only",
        base_hire_rate_gbp=1000.0,
    )
    assert r["insurance_uplift_band_gbp"] == [0.0, 0.0]


# ──────────────────────────────────────────────────────────────────────
# Tool 8 — prepare_dispute_evidence_pack
# ──────────────────────────────────────────────────────────────────────

def test_dispute_evidence_pack_has_baldwins_essentials():
    r = _call(
        prepare_dispute_evidence_pack,
        job_id="JOB-2026-001",
        dispute_narrative="Modular panel dropped, structural damage to fitted-out flats.",
        contract_type_quoted="hire_only",
    )
    universal = r["universal_evidence_checklist"]
    specific = r["contract_specific_evidence_checklist"]

    # Must include the Baldwins-relevant items
    assert any("Lift plan" in item for item in universal)
    assert any("Method statement" in item for item in universal)
    assert any("Appointed Person" in item for item in universal)
    assert any("Hire-only" in item for item in specific)
    assert r["preservation_window_hours"] == 48
    assert any("litigation-hold" in step.lower() for step in r["litigation_hold_steps"])


def test_dispute_evidence_pack_specifics_differ_by_contract_type():
    hire_pack = _call(
        prepare_dispute_evidence_pack,
        job_id="J1",
        contract_type_quoted="hire_only",
    )
    cl_pack = _call(
        prepare_dispute_evidence_pack,
        job_id="J2",
        contract_type_quoted="contract_lift",
    )
    assert hire_pack["contract_specific_evidence_checklist"] != cl_pack["contract_specific_evidence_checklist"]
    # Hire pack should reference Hirer-led evidence
    assert any("Hirer's AP" in i or "Hirer" in i for i in hire_pack["contract_specific_evidence_checklist"])
    # Contract lift pack should reference Owner-led evidence
    assert any("Owner" in i for i in cl_pack["contract_specific_evidence_checklist"])


# ──────────────────────────────────────────────────────────────────────
# HMAC chain / attestation integrity
# ──────────────────────────────────────────────────────────────────────

def test_attestation_present_on_every_tool():
    """All 8 tools must return ts, sig, issuer, version, disclaimer."""
    calls = [
        _call(triage_at_quote, lift_over_occupied_area=True),
        _call(validate_cpa_hire_quote, quote_text="CPA"),
        _call(validate_cpa_contract_lift_quote, quote_text="Contract Lift"),
        _call(generate_cpa_hire_tcs, operator_name="X"),
        _call(generate_cpa_contract_lift_tcs, operator_name="X"),
        _call(analyze_baldwins_v_vision_relevance),
        _call(calculate_insurance_uplift, crane_capacity_t=100, job_value_gbp=50_000),
        _call(prepare_dispute_evidence_pack, job_id="J-1"),
    ]
    for r in calls:
        assert "ts" in r
        assert "sig" in r
        assert r["issuer"] == "meok-cpa-contract-lift-mcp"
        assert r["version"] == "1.0.0"
        assert "disclaimer" in r
        assert "TEMPLATES NOT LEGAL ADVICE" in r["disclaimer"]


def test_hmac_chain_changes_with_payload():
    """HMAC signatures with a configured secret must differ when payload differs."""
    import importlib

    import server as srv

    # Re-import with a secret
    os.environ["MEOK_HMAC_SECRET"] = "test-secret-for-chain"
    importlib.reload(srv)

    r1 = (srv.triage_at_quote.fn if hasattr(srv.triage_at_quote, "fn") else srv.triage_at_quote)(
        crane_capacity_t=50.0,
        lift_over_occupied_area=False,
    )
    r2 = (srv.triage_at_quote.fn if hasattr(srv.triage_at_quote, "fn") else srv.triage_at_quote)(
        crane_capacity_t=200.0,
        lift_over_occupied_area=True,
    )
    assert r1["sig"] != r2["sig"]
    assert r1["sig"] != "unsigned-no-key-configured"
    assert r2["sig"] != "unsigned-no-key-configured"

    # Clean up
    del os.environ["MEOK_HMAC_SECRET"]
    importlib.reload(srv)


# ──────────────────────────────────────────────────────────────────────
# Reference-data sanity
# ──────────────────────────────────────────────────────────────────────

def test_reference_tables_populated():
    assert "condition_9d" in CPA_HIRE_CORE_CLAUSES
    assert "condition_13" in CPA_HIRE_CORE_CLAUSES
    assert "owner_acts_as_contractor" in CPA_CONTRACT_LIFT_CORE_CLAUSES
    assert "no_condition_13_indemnity" not in CPA_HIRE_CORE_CLAUSES
    assert "complex" in LIFT_CATEGORY_GUIDANCE
    assert LIFT_CATEGORY_GUIDANCE["over_occupied_area"]["default"] == "contract_lift"
    assert len(BALDWINS_RED_FLAGS) >= 5
    # Uplift band sanity — 15-30% range overall
    bands = list(INSURANCE_UPLIFT_BANDS.values())
    assert min(b[0] for b in bands) >= 0.15
    assert max(b[1] for b in bands) <= 0.35


def test_disclaimer_warns_solicitor_review_required():
    """Operator MUST be told to get solicitor review — this is non-negotiable."""
    r = _call(generate_cpa_contract_lift_tcs, operator_name="X Ltd", lift_value_gbp=100_000.0)
    assert r["tcs"]["solicitor_review_required_before_customer_use"] is True
    assert "CRITICAL" in r["tcs"]["solicitor_review_priority"]


import json  # noqa: E402  (used in test_contract_lift_tcs_includes_loler_puwer)


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
