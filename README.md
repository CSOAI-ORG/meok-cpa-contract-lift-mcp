<!-- mcp-name: io.github.CSOAI-ORG/meok-cpa-contract-lift-mcp -->
[![MCP Scorecard: 84/100](https://img.shields.io/badge/proofof.ai-84%2F100-5b21b6)](https://proofof.ai/scorecard/meok-cpa-contract-lift-mcp.html)

# meok-cpa-contract-lift-mcp

[![PyPI](https://img.shields.io/badge/PyPI-1.0.0-blue)](https://pypi.org/project/meok-cpa-contract-lift-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-1.3.0+-green)](https://modelcontextprotocol.io)

> CPA Hire-only vs Contract Lift triage at quote stage — the £100k+ wedge per **Baldwins v Vision Modular Systems** £951k claim. By **MEOK AI Labs**.

## Why this exists

Every UK crane, hiab, and plant-hire quote sits at one of the most expensive forks in B2B contracting:

- **Hire-only** under CPA Model Conditions — Hirer directs the lift + Hirer's AP + Condition 13 indemnity = lower price, risk on Hirer.
- **Contract Lift** under CPA — Owner supplies AP + lift plan + insurance = +15-30% price, risk on Owner.

Get the call wrong and you end up in the **Baldwins Crane Hire v Vision Modular Systems** scenario — Baldwins is defending a £951,000 counter-claim turning on whether the work was Hire-only (Condition 13 indemnity holds) or Contract Lift in substance (Condition 9(d) Owner-duty breach).

This MCP gives the operator the callable triage, quote validation, ready-to-issue T&C templates, and dispute-evidence checklist at the point the quote is built.

> **One avoided Baldwins-style £951k counter-claim pays 100+ years of Pro tier.**

## Install

```bash
pip install meok-cpa-contract-lift-mcp
```

## Claude Desktop config

```json
{
  "mcpServers": {
    "cpa-contract-lift": {
      "command": "meok-cpa-contract-lift-mcp"
    }
  }
}
```

## Tools (8)

| Tool | Use case |
|------|----------|
| `triage_at_quote` | Decide Hire-only vs Contract Lift at quote stage — THE WEDGE. |
| `validate_cpa_hire_quote` | Score a Hire-only quote against required CPA clause references. |
| `validate_cpa_contract_lift_quote` | Score a Contract Lift quote (different clauses, anti-pattern detection). |
| `generate_cpa_hire_tcs` | Ready-to-issue CPA Hire T&Cs (Conditions 8, 9, 13, 17-21). |
| `generate_cpa_contract_lift_tcs` | Ready-to-issue Contract Lift T&Cs (Owner principal, BS 7121-1). |
| `analyze_baldwins_v_vision_relevance` | Score a job against the £951k Baldwins Condition 9(d) pattern. |
| `calculate_insurance_uplift` | 15-30% Contract Lift uplift estimate + margin contribution. |
| `prepare_dispute_evidence_pack` | 48-hour Condition 9(d) evidence checklist. |

## Pricing

- **Free** — MIT self-host
- **Starter** — £79/mo (signed attestations + email support)
- **Pro** — £249/mo (dispute evidence vault + multi-user)
- **Fleet** — £799/mo (50+ operators, audit-export, SLA)

[Subscribe Pro → £249/mo](https://buy.stripe.com/aFa7sNcgAdQS0ZT1Uc8k91t) · [Talk to Nick](mailto:nicholas@meok.ai)

## Regulatory basis

- **CPA Model Conditions of Hire 2011** (last amended 2021) — the contractual backbone
  - Condition 8 — Hirer on-site responsibility
  - Condition 9 — Carve-outs (especially 9(d) Owner express-obligation breach)
  - Condition 13 — Hirer indemnity (subject to Condition 9)
  - Conditions 17-21 — Insurance, total loss, sub-let, jurisdiction
- **Baldwins Crane Hire Ltd v Vision Modular Systems Ltd** — Romford, 2026, £951k counter-claim (ongoing)
- **BS 7121-1:2016** — General code of practice for safe use of cranes
- **BS 7121-3 / BS 7121-5** — Mobile / Tower crane code
- **LOLER 1998 + PUWER 1998** — Equipment safety regs
- **Sale of Goods Act 1979** — Implied terms where T&Cs interact

## IMPORTANT — Legal disclaimer

The T&C templates returned by this MCP are **TEMPLATES, NOT LEGAL ADVICE**. They are generated from the public CPA Model Conditions but every operator MUST have a competent construction-law solicitor review the templates against their specific trade, insurance cover, and risk appetite **before** issuing to customers. The MEOK AI Labs templates do not replace solicitor sign-off.

Particularly delicate clauses where solicitor review is essential:

- `generate_cpa_hire_tcs` — Condition 13 indemnity wording
- `generate_cpa_contract_lift_tcs` — Owner-as-principal-contractor wording + insurance primacy
- `analyze_baldwins_v_vision_relevance` — risk verdict is a TRIAGE flag, not a legal opinion

## Sign your responses (production)

```bash
export MEOK_HMAC_SECRET="your-secret"
meok-cpa-contract-lift-mcp
```

Every tool response returns an HMAC-SHA256 signature for tamper-evident audit-trail evidence.

## Companion MCPs

Part of the **MEOK Plant + Crane** stack on haulage.app:

- `meok-loler-puwer-mcp` — LOLER/PUWER thorough examination workflow
- `meok-cpcs-card-check-mcp` — operator competency validation
- `meok-cpa-contract-lift-mcp` — this one

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)
