---
name: copc-nonmetallic-liner
description: "Use when verify structural compliance of a Composite Overwrapped Pressure Container (COPC) fitted with a homogeneous non-metallic liner per ECSS-E-ST-32 clause 4.5.3: categorize the liner material as thermoplastic, thermoset, or elastomer; check proof and burst pressure factors against MEOP minimums; assess liner gas permeation rate against the project allowable limit; compute the load-sharing ratio between liner and composite overwrap; confirm liner-fluid chemical compatibility; and validate demonstrated cyclic fatigue life against mission cycle requirements with the applicable safety factor. Flag any factor shortfall, permeation exceedance, compatibility gap, or fatigue deficit before design acceptance. Trigger: ecss, e-st-32-structures-scope, copc, nonmetallic-liner, pressure-vessel, proof-pressure, burst-pressure, permeation, load-sharing, fatigue-life."
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
  tags: [ecss, e-st-32-structures-scope, copc, nonmetallic-liner, pressure-vessel, proof-pressure, burst-pressure, permeation, load-sharing, fatigue-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPC Non-Metallic Liner Assessment (space-systems/ecss/copc-nonmetallic-liner)

Use when the task is the structural compliance assessment of a Composite
Overwrapped Pressure Container (COPC) fitted with a homogeneous
non-metallic liner per ECSS-E-ST-32 clause 4.5.3 — verifying that the
liner material is recognized and compatible with its stored fluid,
that proof and burst pressure factors meet the required minima, that gas
permeation remains within the project allowable, that the liner does not
carry an excessive share of the structural load, and that the demonstrated
cyclic fatigue life covers mission cycles with the required safety factor.

## Domain quick reference

- ECSS-E-ST-32 clause 4.5.3 addresses COPCs whose liner is a homogeneous
  non-metallic material. Three liner families are distinguished by polymer
  class: thermoplastic (e.g. HDPE, nylon), thermoset (e.g. epoxy,
  cyanate ester), and elastomer (e.g. EPDM, butyl). Each family has
  different permeation characteristics, thermal expansion mismatch
  behaviour with the composite overwrap, and susceptibility to chemical
  attack by the stored fluid.
- Unlike metallic liners, non-metallic liners are gas-permeable. The
  permeation rate (mass per unit time leaking through the liner wall)
  must be assessed against a project-level allowable derived from
  mission leakage and contamination budgets. A rate below the allowable
  is required before the design can be accepted.
- The composite overwrap carries the primary structural load. The liner
  contributes stiffness, but a liner load-share ratio above about 20 %
  of the combined (liner + overwrap) axial stiffness signals that the
  overwrap is undersized or the liner is thicker than necessary, and
  requires design review.
- Proof pressure equals MEOP multiplied by the proof factor (minimum
  1.1); burst pressure equals MEOP multiplied by the burst factor
  (minimum 1.5). These factors are applied to the COPC system — liner
  and overwrap together — not to each layer in isolation.
- Non-metallic liners are susceptible to chemical attack from stored
  fluids, particularly propellants. Compatibility must be confirmed
  against test data or a recognised engineering database for the specific
  liner polymer and fluid combination before the design is accepted.
- Cyclic fatigue life is validated by test. The demonstrated cycle count
  must equal or exceed mission cycles multiplied by the applicable
  scatter safety factor (typically 4.0 for pressure vessels under
  ECSS-E-ST-32). A shortfall in demonstrated life is a design finding,
  not a test credit.

## Workflow

1. Identify the liner material and categorize it into one of the three
   recognized polymer families: thermoplastic, thermoset, or elastomer.
   Reject any material string that does not map to a known family — an
   unrecognized liner type must be resolved with the materials authority
   before the assessment proceeds.
2. Check the proof pressure factor (proof pressure ÷ MEOP). Flag the
   design if the factor is below the minimum of 1.1. Separately check
   the burst pressure factor (burst pressure ÷ MEOP) and flag if below
   the minimum of 1.5. Record both values in the compliance matrix
   regardless of pass or fail status.
3. Obtain the liner gas permeation rate (g/day or equivalent unit) from
   test or material database and compare it against the project allowable
   limit. Flag the design if the rate exceeds the limit, recording the
   exceedance value. If no project limit is on record, flag the absence
   as a missing requirement, not a pass.
4. Compute the liner load-share ratio: liner axial stiffness divided by
   the sum of liner and overwrap axial stiffness. If the ratio exceeds
   0.20 (20 %), raise a design review flag. The flag does not
   automatically fail the assessment but must be resolved by analysis or
   test before sign-off.
5. Confirm liner-fluid chemical compatibility. If the liner polymer
   family is not listed as confirmed compatible with the stored fluid in
   the engineering database, raise a compatibility finding. This requires
   test evidence or a material authority disposition before the finding
   can be closed.
6. Check cyclic fatigue life: multiply the mission cycle count by the
   scatter safety factor (default 4.0). If the demonstrated cycle count
   from qualification test data falls below this value, flag the shortfall
   with the deficit cycle count.
7. Aggregate all findings. The COPC is compliant only when every check
   from steps 2 through 6 passes and the findings list is empty.

## Pitfalls

- Omitting the permeation check on the assumption that the liner is
  effectively gas-tight — non-metallic liners are inherently permeable,
  and a permeation rate must be established by test or material data even
  when the rate is expected to be low.
- Applying the proof and burst factors to the composite overwrap in
  isolation rather than to the COPC as a system. The liner and overwrap
  share load, and the system-level proof and burst pressures must be
  verified against the combined structural model.
- Treating a missing project permeation limit as a pass — an unset limit
  means the mission leakage and contamination budget was never cascaded
  to the container, which is a requirements gap, not evidence of
  compliance.
- Accepting a liner-fluid compatibility assertion without test data or a
  recognised database reference. Non-metallic polymers can undergo
  swelling, embrittlement, or dissolution that is specific to polymer
  grade and fluid purity, and cannot be inferred from the family-level
  categorization alone.
- Using the metallic liner cyclic fatigue approach (autofrettage-based
  pre-stressing) for non-metallic liners — non-metallic liners do not
  undergo plastic pre-stressing, and the fatigue life must be established
  by direct pressure-cycle testing at qualification load levels.

## Behavior contract (gate 3)

The liner categorization, pressure factor, permeation, load-share,
compatibility, and fatigue life logic is exercised by the gate 3 contract
test: scripts/test_copc_nonmetallic_liner.py against
scripts/copc_nonmetallic_liner_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_copc_nonmetallic_liner.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
