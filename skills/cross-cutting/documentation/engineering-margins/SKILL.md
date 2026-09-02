---
name: engineering-margins
description: "Use when you must compute the margin of safety for a structural element and state it in an engineering report: compare the allowable load against the applied load, express the stress margin as a unitless decimal or a percent, and produce the pass/fail verdict on the limit basis or ultimate basis. Produces the margin of safety, the margin percent, the limit margin, and the one-line report sentence with consistent units in newtons. Trigger: margin of safety, engineering report, allowable load, limit load, ultimate load, stress margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: documentation
  tags: [margin-of-safety, engineering-report, allowable, limit-load, ultimate-load, documentation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Engineering Margins (cross-cutting/documentation/engineering-margins)

Use when the task is the margin of safety for a structural element
and the report sentence that carries it: allowable versus applied
load, the limit basis and the ultimate basis, and the pass/fail
verdict. This is the cross-cutting documentation-pack discipline for
reporting margins; strength and allowable computation leaves live in
the structures pack.

## Domain quick reference

- Quantity convention: allowable and applied values are loads in
  newtons (N). Stresses in pascals (Pa) work identically because the
  margin is unitless, but a single call must never mix units: pick
  one unit (all N, or all Pa) and state it in the report. The
  Pa/MPa mix is the known bug class.
- Margin of safety MS = (allowable / applied) - 1, unitless decimal.
- MS >= 0 passes (allowable at least equals applied); MS < 0 fails.
- Margin percent = MS * 100, in percent.
- Limit margin ML = (limit_allowable / limit_applied) - 1, the limit
  basis check.
- Example: allowable 125000 N, applied 100000 N: MS = 0.25, pass.
- Example: allowable 90000 N, applied 100000 N: MS = -0.10, fail.

## Workflow

1. Pick the quantity and unit convention (loads in newtons), the
   same unit for both inputs.
2. Compute the margin with margin_of_safety.
3. Express it as a percent with margin_percent.
4. Check the limit basis with limit_margin.
5. Get the verdict with margin_verdict.
6. Write the report sentence with report_margin, naming the basis
   (limit or ultimate).

## Pitfalls

- Mixing units: Pa for one input and MPa for the other. The margin
  formula divides one value by the other, so mixed units silently
  corrupt the result. Pick one unit for both inputs.
- Reading a negative margin as an error: MS < 0 is a real fail
  verdict to report, not an exception.
- Forgetting the basis: the report sentence must state limit or
  ultimate.
- Reporting the percent margin as the decimal margin:
  margin_percent returns MS * 100, not MS.
- Writing the margin without the verdict: the report sentence
  carries the margin, the basis, and the pass/fail verdict.

## Behavior contract (gate 3)

The margin logic is exercised by the gate 3 contract test:
scripts/test_engineering_margins.py against
scripts/engineering_margins_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_engineering_margins.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 are
  referenced for the margin-of-safety practice; the margin formula
  is common structural-analysis methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
