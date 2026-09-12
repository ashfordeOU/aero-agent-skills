---
name: copv-metallic-liner
description: "Use when verify a Composite Overwrapped Pressure Vessel (COPV) with metallic liner under ECSS-E-ST-32-02C §4.3.3: determine liner hoop stress at MEOP, confirm proof and burst pressure factors meet minimum requirements, evaluate fatigue-life of the metallic liner against scatter-factored design cycle count, assess composite overwrap fiber stress at burst via netting theory, and check liner yield limits at proof. Covers titanium, aluminium, and Inconel liners, autofrettage detection, margin-of-safety computation, and consolidated compliance reporting. Trigger: ecss, e-st-32-structures-scope, copv, metallic-liner, composite-overwrap, pressure-cycle-fatigue, proof-pressure, burst-pressure, pressure-vessel."
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
  tags: [ecss, e-st-32-structures-scope, copv, metallic-liner, composite-overwrap, pressure-cycle-fatigue, proof-pressure, burst-pressure, pressure-vessel]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPV with Metallic Liner (space-systems/ecss/copv-metallic-liner)

Use when the task is to verify or size a Composite Overwrapped Pressure Vessel
with metallic liner under ECSS-E-ST-32-02C §4.3.3 — computing liner stress at
Maximum Expected Operating Pressure, verifying proof and burst pressure factors
against ECSS minimums, estimating composite overwrap fiber stress at burst via
netting theory, and assessing metallic liner fatigue life with a scatter-factored
cycle requirement.

## Domain quick reference

- A COPV with metallic liner consists of two load-sharing elements: the metallic
  liner (aluminium, titanium, or Inconel alloy) provides the leak-tight barrier
  and carries a fraction of the hoop load; the composite overwrap (carbon or
  aramid fiber in an epoxy matrix) carries the structural hoop and axial load.
  At MEOP the liner must remain within its yield envelope; the overwrap is sized
  to the burst requirement.
- Proof testing is conducted above MEOP (proof factor ≥ 1.25 × MEOP per
  ECSS-E-ST-32-02C) to screen for manufacturing defects. For a non-autofrettage
  design the liner must not yield at proof; for an autofrettage design the liner
  is intentionally taken through yield to introduce beneficial residual
  compressive stress in the liner bore, improving fatigue performance. The proof
  check identifies which regime applies and flags unexpected yielding.
- Burst pressure (factor ≥ 2.0 × MEOP) sets the design requirement for the
  composite overwrap. Fiber stress at burst is estimated using netting theory:
  the fibers are assumed to carry all load, scaled by the fiber volume fraction.
  The netting-theory result is conservative for hoop-dominated cylindrical
  sections and provides a first-pass overwrap sizing check.
- Liner fatigue arises from cyclic pressurisation and depressurisation. A
  power-law (Basquin-type) S-N model — Nf = (σ_f / σ_a)^m — estimates fatigue
  life from the stress amplitude and material constants. The life requirement is
  the product of the mission design cycle count and a scatter factor (default
  4.0) that accounts for material variability and statistical confidence.

## Workflow

1. Gather vessel geometry (inner radius, liner thickness, overwrap thickness),
   material properties (liner yield strength, fiber tensile allowable, fiber
   volume fraction, Basquin fatigue constants), loading (MEOP, design cycle
   count), and design factors (proof factor, burst factor, fatigue scatter
   factor). Reject any missing required input before any check runs.
2. Compute liner hoop stress at MEOP using the thin-wall Barlow formula
   (σ = p × r / t). Compare against liner yield strength to obtain margin of
   safety. A negative margin means the liner is overstressed at operating
   pressure and must be redesigned before proceeding.
3. Verify the proof factor is at or above the ECSS minimum (1.25). Compute
   liner hoop stress at proof pressure; determine whether the liner yields
   (autofrettage regime) or remains elastic (non-autofrettage regime). Flag
   unexpected yielding as a finding requiring an explicit autofrettage design
   decision before qualification.
4. Verify the burst factor is at or above the ECSS minimum (2.0). Estimate
   fiber hoop stress at burst via netting theory: σ_fiber = p_burst × r /
   (t_overwrap × Vf). Compare against the fiber tensile allowable to obtain
   overwrap burst margin. A negative margin requires overwrap thickness
   increase or fibre selection change.
5. Compute liner fatigue life using the Basquin power-law model:
   Nf = (σ_f / σ_a)^m, where σ_f is the fatigue strength reference, σ_a is
   the liner hoop stress amplitude per cycle, and m is the slope exponent.
   Apply the scatter factor to the design cycle count to obtain the required
   life. Flag the liner as fatigue-inadequate if Nf < design_cycles × scatter.
6. Aggregate all findings. The vessel is compliant only when the liner MEOP
   margin, proof factor, liner proof yield check, overwrap burst margin, and
   fatigue adequacy all return no findings.

## Pitfalls

- Applying a burst factor below 2.0 and treating the vessel as flight-qualified —
  ECSS-E-ST-32-02C sets 2.0 as the minimum factor for COPV flight hardware;
  lower factors require formal deviation approval from the responsible authority.
- Conflating the liner yield limit at proof between autofrettage and
  non-autofrettage designs — in a non-autofrettage design, liner yielding at
  proof is a finding; in an autofrettage design it is intended and the residual
  stress state must be characterised and entered into the fatigue assessment,
  not treated as a failure or suppressed.
- Using gross overwrap cross-section area instead of net fiber area in the
  netting-theory burst check — the fiber volume fraction must scale the
  load-bearing area; omitting Vf systematically underestimates fiber stress and
  produces a non-conservative margin.
- Applying the design cycle count directly as the fatigue life requirement
  without the scatter factor — the scatter factor accounts for test-to-test
  variability and statistical confidence; omitting it produces an
  unconservative fatigue assessment that can pass on analysis but fail
  qualification test.
- Treating a missing or unset liner material property as a pass — an incomplete
  input set must raise an error before any check runs, not silently default to
  zero or unity, because both defaults yield nonsensical results.

## Behavior contract (gate 3)

The hoop stress, proof/burst factor, fiber stress, fatigue life, and consolidated
compliance checks are exercised by the gate 3 contract test:
scripts/test_copv_metallic_liner.py against scripts/copv_metallic_liner_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_copv_metallic_liner.py

## Compliance

- ECSS-E-ST-32-02C (Structural general requirements, pressure vessels):
  referenced as the clause anchor; no verbatim text reproduced.
- compliance: STANDARDS-REF, gated: false.
