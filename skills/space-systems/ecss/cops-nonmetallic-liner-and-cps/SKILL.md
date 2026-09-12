---
name: cops-nonmetallic-liner-and-cps
description: "Use when evaluate a Composite Overwrapped Pressure System (COPS) with a homogeneous non-metallic liner, or an all-composite Pressure System (CPS) with no liner, under ECSS-E-ST-32 clause 4.4.4: determine the system variant (non-metallic-liner COPS or all-composite CPS), verify proof and burst pressure margins against ECSS safety factors, check liner permeation and buckling allowables for non-metallic variants, confirm pressure-cycle fatigue life meets the design service life multiplied by the qualification factor, and verify leak-before-burst or safe-life fracture-control compliance. Trigger: ecss, e-st-32-structures-scope, cops, cps, composite-pressure-vessel, nonmetallic-liner, all-composite-cps, liner-integrity, burst-pressure, pressure-cycle-life."
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
  tags: [ecss, e-st-32-structures-scope, cops, cps, composite-pressure-vessel, nonmetallic-liner, all-composite-cps, liner-integrity, burst-pressure, pressure-cycle-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPS Non-Metallic Liner & All-Composite CPS (space-systems/ecss/cops-nonmetallic-liner-and-cps)

Use when the task is to evaluate a Composite Overwrapped Pressure System
(COPS) employing a homogeneous non-metallic liner, or an all-composite
Pressure System (CPS) that carries no liner at all, per ECSS-E-ST-32
clause 4.4.4. The assessment covers system-variant determination, pressure
margin verification, liner-specific integrity checks, pressure-cycle life
qualification, and fracture-control compliance.

## Domain quick reference

- ECSS-E-ST-32 clause 4.4.4 distinguishes two sub-variants of
  non-metallic-lined or liner-free composite pressure hardware:
  (a) COPS with a homogeneous non-metallic liner — the composite
  overwrap carries structural load while the liner provides the
  gas-tight boundary; the liner material is a polymer or similar
  non-metallic solid with no metallic constituent; (b) all-composite
  CPS — the composite shell alone provides structural integrity and
  the gas-tight boundary; no separate liner element is present.
  The sub-variant drives which additional checks apply beyond the
  common structural margin and life checks.
- Structural margins are defined relative to the Maximum Expected
  Operating Pressure (MEOP). A minimum proof pressure of 1.1 × MEOP
  must be applied and sustained without failure or unacceptable
  deformation during qualification testing. A predicted (or
  demonstrated) burst pressure of at least 2.0 × MEOP is required to
  confirm sufficient structural reserve. These factors are paraphrased
  from ECSS-E-ST-32 Table requirements for composite pressure hardware;
  project-specific requirements may impose higher values.
- Pressure-cycle fatigue life qualification requires the hardware to
  sustain at least four times the maximum expected number of pressure
  cycles in service (design cycles × 4) without burst or leakage,
  demonstrating adequate fatigue margin under cyclic pressurisation.
- Fracture control for composite pressure hardware mandates either a
  demonstrated leak-before-burst (LBB) capability — the vessel leaks
  detectably before catastrophic rupture at all flaw sizes up to the
  non-destructive inspection detection threshold — or a safe-life
  analysis showing the design life is achieved with no crack growth to
  critical size. One of the two paths must be documented before the
  hardware is accepted.
- For the non-metallic liner variant, two additional checks apply:
  (i) liner gas permeation — the steady-state permeation rate of the
  pressurised gas through the non-metallic liner must not exceed the
  allowable set by the system-level leak budget; (ii) liner buckling
  resistance — the liner must not buckle under any external pressure
  condition (e.g., during autofrettage pressure reversal or vacuum
  ambient with internal depressurisation), verified by showing the
  ratio of critical buckling pressure to applied external pressure
  is at least 1.0.

## Workflow

1. Determine the system variant from the design definition: confirm
   whether a liner is present and, if so, confirm the liner material
   is homogeneous and non-metallic with no metallic constituent.
   Assign variant COPS_NONMETALLIC_LINER or ALL_COMPOSITE_CPS. Reject
   inputs where the variant cannot be resolved from available data.
2. Retrieve the MEOP from the system pressure envelope. Verify the
   applied qualification proof pressure is at least MEOP × 1.1 and
   that the predicted or test-demonstrated burst pressure is at least
   MEOP × 2.0. Flag either margin as deficient if below its threshold.
3. Retrieve the design pressure-cycle count (maximum expected cycles
   over service life) and the number of cycles sustained in the
   qualification fatigue test without burst or leakage. Confirm
   qualified cycles ≥ design cycles × 4; flag a shortfall as a
   cycle-life finding.
4. Check fracture-control compliance: confirm that either LBB
   capability has been demonstrated (flaw-tolerant path) or a
   safe-life analysis has been accepted (flaw-free path). Flag the
   finding if neither is on record.
5. For COPS_NONMETALLIC_LINER only — check liner gas permeation:
   obtain the measured or analytically predicted steady-state
   permeation rate and the system allowable; flag an exceedance.
   Also check liner buckling: obtain the critical-to-applied external
   pressure ratio; flag a ratio below 1.0 as a buckling risk.
6. Aggregate all findings. The hardware is structurally compliant under
   clause 4.4.4 only when the findings list contains no FAIL entries.
   A hardware item with any open finding is not accepted until the
   finding is resolved and re-evaluated.

## Pitfalls

- Treating the non-metallic liner as a structural load-carrying member
  equivalent to a metallic liner — the non-metallic liner contributes
  negligibly to structural load and its sizing is dominated by gas
  barrier and permeation requirements, not stress allowables.
- Applying the all-composite CPS burst factor to a COPS with a
  non-metallic liner without verifying the liner's compatibility with
  the burst test regime — liner cracking under proof can alter the
  effective burst pressure prediction if not accounted for in the
  structural model.
- Omitting the liner permeation check on the assumption that the
  composite overwrap itself is gas-tight — the ECSS clause requires a
  documented permeation analysis or test for the non-metallic liner
  variant because overwrap micro-cracking can open a permeation path
  through the liner at cyclic pressure.
- Accepting "neither LBB nor safe-life documented" as a pass because
  no crack has been observed — the absence of a documented fracture
  control path is itself a non-compliance finding, not a neutral
  condition.
- Using the design cycle count directly as the qualification target
  without applying the × 4 life factor — the ECSS fatigue
  qualification margin is multiplicative, not additive.

## Behavior contract (gate 3)

The system-variant determination, proof/burst margin, cycle-life,
fracture-control, liner-permeation, and liner-buckling logic is
exercised by the gate 3 contract test:
scripts/test_cops_nonmetallic_liner_and_cps.py against
scripts/cops_nonmetallic_liner_and_cps_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_cops_nonmetallic_liner_and_cps.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
