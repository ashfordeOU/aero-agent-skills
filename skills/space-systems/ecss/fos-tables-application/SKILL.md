---
name: fos-tables-application
description: "Use when determine the required factor of safety (FOS) for a structural
  component under ECSS-E-ST-32C clause 4.2.5: select the applicable yield, ultimate,
  or proof FOS from the tabulated values based on mission type (unmanned or human
  spaceflight), apply that factor to limit loads to obtain design loads, and compute
  the resulting margin of safety for each load case. Trigger: ecss, e-st-32-structures-scope,
  factor-of-safety, yield-factor, ultimate-factor, proof-factor, unmanned-spaceflight,
  human-spaceflight, margin-of-safety, structural-sizing."
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
  tags: [ecss, e-st-32-structures-scope, factor-of-safety, yield-factor, ultimate-factor, proof-factor, unmanned-spaceflight, human-spaceflight, margin-of-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — FOS Tables Application (space-systems/ecss/fos-tables-application)

Use when the task is selecting and applying the tabulated factors of safety from
ECSS-E-ST-32C clause 4.2.5 to structural load cases — covering yield, ultimate
(burst), and proof factors for both unmanned and human spaceflight missions.

## Domain quick reference

- ECSS-E-ST-32C clause 4.2.5 provides two sets of FOS tables: one for unmanned
  spacecraft and one for human spaceflight (human-rated) missions. The correct
  table is selected based on mission type before any FOS value is read.
- Three factor categories apply: the **yield factor** (jY) limits permanent
  deformation under design loads; the **ultimate factor** (jU) guards against
  fracture or collapse; the **proof factor** (jP) is used when verifying pressure
  retention via a proof pressure test. Each category has a distinct tabulated
  minimum.
- For unmanned missions the tabulated minimums are: jY = 1.10, jU = 1.25,
  jP = 1.10. For human spaceflight missions the more conservative values are:
  jY = 1.25, jU = 1.40, jP = 1.50. Using the unmanned table for a human-rated
  programme is a non-conformance.
- Margin of safety is defined as: MS = (allowable / (FOS × limit load)) − 1.
  A non-negative MS indicates the design meets the requirement; a negative MS
  is a finding that must be resolved before the stress analysis is closed.
- Mixed-mission programmes (a payload flying on both an unmanned carrier and a
  human-rated vehicle) must use the higher (human spaceflight) FOS for the
  joint design unless a formal tailoring waiver is in place.

## Workflow

1. Determine the mission type for the hardware under analysis: unmanned or human
   spaceflight. When there is uncertainty (dual-manifest or multi-mission), default
   to human spaceflight until a tailoring decision is formally recorded.
2. Select the applicable FOS table column (unmanned or human spaceflight) and
   record the three required minimum factors: jY, jU, jP. Do not blend values
   from both columns without a documented tailoring rationale.
3. For each structural load case, identify the governing factor category:
   — yield-critical cases: use jY;
   — ultimate/burst cases: use jU;
   — proof pressure cases: use jP.
   A single component may have separate yield and ultimate load cases that each
   require their own FOS application and margin check.
4. Compute the design load for each case: design load = FOS × limit load. The
   design load is the value that the allowable (material strength, test capability,
   or burst pressure) must equal or exceed.
5. Compute the margin of safety: MS = (allowable / design load) − 1. Record the
   governing (minimum) MS across all load cases for the component.
6. Accept the component if every MS ≥ 0. Reject (flag as a finding) if any MS < 0.
   A component whose FOS source (unmanned vs human spaceflight table) is not
   documented is also flagged, even if the numeric MS appears positive.

## Pitfalls

- Reading the FOS from the unmanned column when the mission is human-rated, or
  vice versa — the distinction is not a minor conservatism; it is a mandatory
  normative requirement of clause 4.2.5 and will be checked at design review.
- Applying the yield FOS to a burst or fracture load case (or the ultimate FOS
  to a yield-only case) — each factor category applies to a specific failure mode
  and they must not be substituted for one another.
- Treating a positive MS as proof of compliance without confirming the allowable
  was derived from the correct material coupon population (A-basis vs B-basis)
  and the correct FOS column.
- Omitting the proof factor for a pressure-bearing component on the grounds that
  a proof test was not performed — if no proof test is conducted, an analysis-only
  proof margin must still be demonstrated using jP and the maximum expected
  operating pressure as the limit load.

## Behavior contract (gate 3)

The mission-type selection, FOS lookup, design-load computation, and margin-of-safety
logic is exercised by the gate 3 contract test:
scripts/test_fos_tables_application.py against
scripts/fos_tables_application_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fos_tables_application.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
