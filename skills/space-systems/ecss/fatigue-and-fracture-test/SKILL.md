---
name: fatigue-and-fracture-test
description: "Use when assess fatigue life and fracture-critical behaviour of a
  spacecraft structural component under ECSS-E-ST-32C clause 4.6.3.11: define a
  representative load spectrum from mission-profile blocks at discrete stress
  levels, apply Miner's rule to accumulate cycle damage and compare against the
  failure threshold, derive the required test life using a material-appropriate
  scatter factor, select an inspection method with adequate crack-detection
  capability, evaluate each specimen against completed-cycles and crack-found
  criteria, and verify residual strength after sustained damage.
  Trigger: ecss, e-st-32-structures-scope, fatigue-test, fracture-test,
  load-spectrum, miners-rule, crack-detection, damage-tolerance, residual-strength."
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
  tags: [ecss, e-st-32-structures-scope, fatigue-test, fracture-test, load-spectrum, miners-rule, crack-detection, damage-tolerance, residual-strength]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fatigue and Fracture Test (space-systems/ecss/fatigue-and-fracture-test)

Use when the task is the fatigue and fracture test of a spacecraft structural
component per ECSS-E-ST-32C clause 4.6.3.11 — constructing a load spectrum
from mission-profile blocks, accumulating Miner's rule damage, deriving the
test life from a scatter factor, selecting a crack-detection method, and
assessing specimen outcome and residual strength.

## Domain quick reference

- Clause 4.6.3.11 requires that fatigue-critical components be exercised
  under a realistic load spectrum and that any cracks be detectable before
  they become critical. The spectrum is built from a set of stress-level
  blocks, each described by a peak stress amplitude and a cycle count drawn
  from the mission profile (launch, on-orbit manoeuvres, thermal cycling,
  re-entry as applicable).
- Miner's rule provides the cumulative damage index D = Σ(n_i / N_i),
  where n_i is the number of applied cycles at stress level i and N_i is
  the number of cycles to failure at that level from the S-N curve.
  Failure is predicted when D reaches 1.0. A spectrum that drives D to or
  above 1.0 before the end of the required test life is a finding.
- The test life is not equal to the design life: a scatter factor (≥ 1.0)
  accounts for material variability and unknown load uncertainty. Typical
  values are 4.0 for metallic structures and 6.0 for fibre-reinforced
  composites. The specimen must survive test_life = ceil(design_life ×
  scatter_factor) cycles without triggering the failure criterion.
- Crack detection capability depends on the inspection method. Each method
  has a minimum detectable crack size; a method is only acceptable for a
  given inspection interval if its threshold is smaller than the critical
  crack size at that interval. Common methods and indicative thresholds:
  eddy current (~0.1 mm), dye penetrant (~0.2 mm), magnetic particle
  (~0.3 mm), ultrasonic/radiographic (~0.5 mm), visual (~3.0 mm).
- Residual-strength verification after the fatigue test confirms that
  accumulated damage has not reduced the load-carrying capacity below
  the limit load. A linear knock-down model (strength reduced
  proportionally to Miner damage) is used as a conservative bound.

## Workflow

1. Inventory the load environment and construct the spectrum: one block
   per distinct stress-level band in the mission profile, each with a
   positive stress amplitude and a positive cycle count. Reject any block
   with a non-positive value before it enters the damage calculation.
   A single-block spectrum is permissible but warrants a review note
   recommending multi-block representation for realism.
2. Select or derive the S-N curve for the material and joint configuration
   at each stress level in the spectrum. Every stress level in the
   spectrum must have a corresponding S-N entry; a missing entry blocks
   the damage calculation with an explicit error.
3. Apply Miner's rule: compute D = Σ(n_i / N_i) over all blocks. If D ≥
   1.0 the spectrum drives the component to failure before the end of the
   applied cycles; report a finding and do not proceed to derive the test
   life until the spectrum or the design is revised.
4. Determine the material category (metallic or composite) and apply the
   appropriate scatter factor to derive the test life. Use
   test_cycles = ceil(design_life_cycles × scatter_factor). Ensure the
   scatter factor is ≥ 1.0; a value below 1.0 is a configuration error.
5. Select the non-destructive inspection method for crack monitoring
   during the test. Confirm the method's detection threshold is below the
   smallest crack size that must be caught. Record the selected method and
   threshold in the test plan.
6. Run the fatigue test. After the test, evaluate the specimen: it passes
   if it completed at least the required test cycles and no crack was
   detected before the required life (standard mode), or if it completed
   the required life even with a crack (damage-tolerance demonstration
   mode). Failure to reach the required cycle count, or a crack appearing
   before the required life in standard mode, is a test failure.
7. After the test, compute the residual strength using the accumulated
   Miner damage and confirm it exceeds the limit load. A residual
   strength at or below limit load is a finding that must be resolved
   before the structural margin can be closed.

## Pitfalls

- Applying the design-life cycle count directly as the test-life count —
  the scatter factor is mandatory; omitting it unconservatively
  understates the required test duration.
- Using a single S-N data point extrapolated beyond its valid stress range
  — the S-N curve must cover every stress level in the spectrum; any
  extrapolation outside the data range needs explicit justification.
- Treating a missing S-N entry as zero damage — a missing entry means the
  damage contribution is unknown, which is a data gap, not a conservative
  bound; the calculation must be blocked until the data is supplied.
- Selecting a crack-detection method whose threshold exceeds the critical
  crack size at the inspection interval — the method will miss a
  growing crack, leaving the component at undetected risk.
- Collapsing standard-mode and damage-tolerance-mode pass criteria — in
  standard mode any crack before the required life is a failure; in
  damage-tolerance mode the structure must still survive to the required
  life even after a crack is detected; the two modes must not be mixed.
- Reading D < 1.0 as a safety margin without checking residual strength —
  accumulated sub-critical damage still reduces load capacity; a residual-
  strength check is required even when Miner's rule has not been reached.

## Behavior contract (gate 3)

The spectrum-validation, Miner's-rule damage, test-life derivation,
crack-detection capability, specimen-outcome, and residual-strength logic
is exercised by the gate 3 contract test:
scripts/test_fatigue_and_fracture_test.py against
scripts/fatigue_and_fracture_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fatigue_and_fracture_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
