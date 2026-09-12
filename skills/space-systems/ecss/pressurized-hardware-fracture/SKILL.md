---
name: pressurized-hardware-fracture
description: "Use when assess pressurized hardware for fracture criticality under
  ECSS-E-ST-32C clause 8.2, covering pressure vessels (PV), pressure systems (PS),
  pressure components, lines, and containers: categorize each item as fracture-critical
  or non-fracture-critical based on failure consequence and propellant content, compute
  the critical crack size from fracture toughness and operating stress, verify
  Leak-Before-Burst (LBB) compliance, confirm that proof testing or NDE screens the
  initial flaw below the critical size, and estimate fatigue crack-growth life against
  the design cycle budget. Trigger: ecss, e-st-32-structures-scope, fracture-control,
  pressure-vessel, leak-before-burst, fracture-toughness, crack-growth, proof-test,
  pressurized-hardware, lbb."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, pressure-vessel, leak-before-burst, fracture-toughness, crack-growth, proof-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control of Pressurized Hardware (space-systems/ecss/pressurized-hardware-fracture)

Use when the task is the fracture-control assessment of pressurized hardware
under ECSS-E-ST-32C clause 8.2: categorizing pressure vessels (PV), pressure
systems (PS), pressure components, lines, and containers for fracture
criticality, computing critical crack sizes and fracture margins, verifying the
Leak-Before-Burst (LBB) criterion, confirming proof-test or NDE screening
adequacy, and estimating fatigue crack-growth life against the design cycle
budget.

## Domain quick reference

- Clause 8.2 assigns pressurized hardware to one of two categories: **fracture-critical**
  (failure consequence is catastrophic or critical, or the item contains propellant) or
  **non-fracture-critical** (remaining items controlled by proof test and safe-life
  without explicit fracture analysis).  Every candidate item must be assigned to
  exactly one category before any crack-size or life calculation begins.

- The **critical crack size** (a_c) is the half-crack length at which the applied
  stress-intensity factor K_I equals the material fracture toughness K_Ic under the
  Maximum Expected Operating Pressure (MEOP) loading:
  `a_c = (K_Ic / (β · σ · √π))²`, where β is the geometry factor and σ is the
  applied stress.  A crack equal to a_c will propagate unstably; all retained
  initial flaws must lie well below this value.

- The **Leak-Before-Burst (LBB) criterion** requires that a crack growing through
  the wall thickness produces a detectable leak before reaching the critical length
  for unstable burst.  A common screening check: a_c must exceed twice the wall
  thickness (the through-wall crack of length equal to the wall thickness is stable
  at MEOP).  When LBB is satisfied, a leak provides advance warning before
  catastrophic burst, which is the basis for controlled depressurization.

- **Proof testing** loads the hardware to a proof factor (typically 1.25–1.5 ×
  MEOP) to screen out pre-existing cracks larger than the proof-surviving crack size
  a_proof = (K_Ic / (β · σ_proof · √π))².  Any crack larger than a_proof causes
  fracture during the proof test, so the hardware is rejected before service.
  **NDE** screens cracks above a detection limit a_nde.  The initial flaw assumed
  for life calculations is `min(a_proof, a_nde)`.

- **Fatigue crack-growth life** is estimated from the initial crack to the critical
  crack using the Paris–Erdogan law: da/dN = C · (ΔK)^m.  A constant-ΔK
  approximation provides a conservative screening bound; a full variable-K numerical
  integration is required in the final fracture-control report.

## Workflow

1. **Categorize each pressurized hardware item** as fracture-critical or
   non-fracture-critical.  Failure consequence of catastrophic or critical, or
   propellant containment, triggers the fracture-critical path.  Reject any
   unrecognized hardware type before it enters the calculation.

2. **Compute the critical crack size** a_c at MEOP for every fracture-critical item,
   using the material K_Ic, the applied membrane stress, and the appropriate geometry
   factor β for the crack orientation and location (surface, through, corner).

3. **Assess the LBB criterion**: verify that a_c ≥ lbb_factor × wall thickness.
   When LBB is not satisfied, the proof-test path (step 4) must demonstrate adequate
   initial-flaw screening; both failures together constitute a compliance gap.

4. **Evaluate proof-test and NDE screening**: compute a_proof at the proof stress,
   compare it to a_nde, and set the initial crack assumption to the smaller value.
   When a_proof < a_nde, the proof test screens flaws that NDE would miss.

5. **Check the fracture margin** K_Ic / K_applied − 1 at the initial crack under
   MEOP loading.  A negative margin means the retained initial flaw exceeds the
   critical size at operating pressure — this is an immediate compliance failure.

6. **Estimate fatigue crack-growth life** from the initial crack to a_c using the
   Paris law constants and the mid-crack ΔK as the constant-K approximation.
   Compare the estimated cycle count against the design cycle requirement; flag
   life_adequate = False when estimated cycles fall short.

7. **Determine overall compliance**: for fracture-critical hardware, all of the
   following must hold — positive fracture margin, LBB satisfied OR proof test more
   stringent than NDE, and life adequate.  For non-fracture-critical hardware,
   positive fracture margin and life adequacy are sufficient.

## Pitfalls

- **Skipping the categorization step and running fracture analysis on every item**:
  non-fracture-critical items are controlled by proof test and safe-life only; a
  full fracture analysis is not required and may introduce spurious findings if the
  wrong K_Ic values or geometry factors are applied.

- **Treating LBB failure as an automatic compliance failure without checking the
  proof-test path**: clause 8.2 allows proof-test screening to substitute for LBB
  when a_proof < a_nde.  The compliance gate is LBB satisfied OR proof screens NDE,
  not LBB alone.

- **Using the NDE detection limit directly as the initial crack without applying a
  proof test**: if a proof test has been performed and a_proof < a_nde, the initial
  crack is a_proof, which gives a more optimistic (and physically correct) life
  estimate.

- **Applying the constant-ΔK Paris approximation as a final result**: the
  constant-ΔK bound is conservative for screening only.  A final fracture-control
  report requires a variable-K numerical integration from a_initial to a_c over the
  actual stress spectrum.

- **Omitting the geometry factor β and using the centre-cracked panel formula for
  every case**: β varies significantly with crack geometry (surface crack, through
  crack, corner crack) and with the ratio a/W.  Using β = 1 for all configurations
  can underestimate K_I by 10–30 %, potentially masking a genuine compliance failure.

## Behavior contract (gate 3)

The categorization, critical-crack-size, LBB, proof-test-adequacy,
fracture-margin, fatigue-life, and full-assessment logic is exercised by the
gate-3 contract test: scripts/test_pressurized_hardware_fracture.py against
scripts/pressurized_hardware_fracture_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_pressurized_hardware_fracture.py
```

## Compliance

- ECSS-E-ST-32C is freely downloadable from ESA; cite the standard and clause
  number as the anchor only.  All procedural content in this skill is paraphrased
  from common fracture-mechanics knowledge and the ECSS clause structure, not
  reproduced verbatim.
- compliance: STANDARDS-REF, gated: false.
