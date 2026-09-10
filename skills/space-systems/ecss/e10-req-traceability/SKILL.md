---
name: e10-req-traceability
description: "Use when maintaining bidirectional requirement traceability under ECSS-E-ST-10C: keep the requirements traceability matrix (RTM) aligned across customer requirements, derived requirements, allocated products and verification records, and detect broken, missing or dangling trace links before review gates. ECSS-E-ST-10C clause 5.2.2 governs requirement traceability as part of system engineering requirement flow-down. Trigger: ecss, e-st-10c, requirement traceability, RTM, trace matrix, bidirectional trace, 5.2.2, space systems engineering."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10c, requirement-traceability, rtm, traceability-matrix, bidirectional-trace, systems-engineering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Traceability (space-systems/ecss/e10-req-traceability)

Use when maintaining the bidirectional requirement traceability chain
under ECSS-E-ST-10C clause 5.2.2, after requirements have been analysed
(sibling e10-req-analysis) and flowed down (e10-trs-flowdown).

## When to use

- Keeping the Requirements Traceability Matrix (RTM) current as
  requirements, products and verifications change.
- Checking before a review gate that every requirement resolves both
  directions: upward to the requirement(s) it originates from, and
  downward to an allocated product and a verification record.
- Auditing a delivered RTM for broken, missing, or dangling links.

## Domain quick reference

Trace directions (bidirectional, 5.2.2):

- Upward: derived requirement -> the customer/upper-level requirement
  it was produced from. Customer-level requirements are the root and
  have no upward link.
- Downward: requirement -> product(s) it is allocated to, and
  requirement -> verification activity/record that closes it.

## Procedure

1. Collect the requirement records (id, level, parents, products,
   verifications), product records and verification records.
2. Run `python3 scripts/test_e10_req_traceability.py` to confirm the
   module's own contract still passes.
3. From Python, import the sibling logic module and call:

```python
import e10_req_traceability_logic as rtl
# records: dicts with id/level/parents/products/verifications
gaps = rtl.trace_gaps(requirements, products, verifications)
```

4. Interpret gap codes (constant names on the module):

- `GAP_NO_UPWARD_TRACE` - derived requirement without a parent.
- `GAP_NO_DOWNWARD_TRACE` - customer requirement with neither a child
  requirement nor a direct product allocation.
- `GAP_NO_PRODUCT_ALLOCATION` - requirement with no product allocated
  (customer requirements flowing to derived children are exempt).
- `GAP_NO_VERIFICATION_LINK` - requirement with no verification record.
- `GAP_DANGLING_PARENT` / `GAP_DANGLING_PRODUCT` /
  `GAP_DANGLING_VERIFICATION` - link references a record outside the
  given sets.

5. Fix each gap in the RTM before the review gate; re-run
   `rtl.is_fully_traced(...)` until it returns `(True, {})`.

## Verification

- The offline unittest suite passes (`python3 -m unittest
  scripts.test_e10_req_traceability`, or the test file directly).
- A clean bidirectional chain returns no gaps.
