---
name: cospe-metallic-liner
description: "Use when evaluate metallic-liner COSPE structural and pressure
  integrity under ECSS-E-ST-32C clause 4.6.2: categorize the liner material as
  an aluminum alloy, titanium alloy, stainless steel, or nickel alloy; compute
  the margin-of-safety against liner yield and ultimate failure at maximum
  expected operating pressure; verify that the proof pressure ratio and burst
  pressure ratio satisfy the minimum multipliers required by the standard;
  confirm that the liner wall thickness meets the specified minimum; and check
  that the demonstrated fatigue-life, reduced by the prescribed scatter factor,
  covers the required qualification life. Trigger: ecss, e-st-32-structures-scope,
  cospe, metallic-liner, copv, pressure-vessel, burst-pressure, fatigue-life,
  margin-of-safety."
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
  tags: [ecss, e-st-32-structures-scope, cospe, metallic-liner, copv, pressure-vessel, burst-pressure, fatigue-life, margin-of-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COSPE with Metallic Liner (space-systems/ecss/cospe-metallic-liner)

Use when the task is to evaluate a composite overwrapped pressure vessel (COSPE)
that uses a metallic liner under ECSS-E-ST-32C clause 4.6.2 — verifying liner
material acceptability, structural margins against yield and ultimate failure,
proof and burst pressure ratios, wall thickness adequacy, and fatigue life
qualification against the required scatter factor.

## Domain quick reference

- Clause 4.6.2 applies to COSPE with a metallic liner, where the liner acts as
  the pressure-containing membrane and the composite overwrap carries the
  primary structural load. Accepted metallic liner material families are
  aluminum alloys, titanium alloys, stainless steels, and nickel alloys; any
  other material requires explicit program justification.
- Structural margins are expressed as margin of safety (MoS): MoS =
  (allowable / applied) − 1.0. Both yield MoS and ultimate MoS must be ≥ 0.0
  at the maximum expected operating pressure (MEOP).
- Proof pressure must be at least 1.1 × MEOP for a metallic-liner COSPE; the
  ratio P_proof / P_MEOP below this threshold is a violation regardless of
  observed leak-free behaviour.
- Burst pressure must reach at least 2.0 × MEOP; this ratio ensures the
  composite overwrap provides adequate residual strength after the liner has
  yielded.
- Wall thickness of the metallic liner must not fall below the minimum derived
  from corrosion allowance, manufacturing tolerance, and minimum-gauge
  requirements; a liner thinner than its minimum is a structural finding even
  if stress margins are positive.
- Fatigue life demonstration must cover cycles_required × scatter_factor
  (scatter_factor = 4.0) to account for material scatter; the effective
  credited life is cycles_demonstrated / 4.0 and must equal or exceed the
  mission-derived cycles_required.

## Workflow

1. Confirm the liner material type falls within the accepted metallic families
   (aluminum alloy, titanium alloy, stainless steel, or nickel alloy). Reject
   any unrecognized material type before proceeding — it requires a dedicated
   materials-substantiation path not covered by this clause.
2. Obtain or compute the hoop stress at MEOP (σ = P × r / t for thin-walled
   approximation, or the full Lamé solution for thick-walled geometry). Compare
   the hoop stress against the liner's yield strength and ultimate strength; a
   negative MoS in either case is a structural violation.
3. Verify the proof pressure ratio P_proof / P_MEOP ≥ 1.1. A ratio below the
   minimum means the vessel has not been subjected to the required proof
   stimulus and cannot be accepted under clause 4.6.2.
4. Verify the burst pressure ratio P_burst / P_MEOP ≥ 2.0. Burst is assessed
   by analysis or test; both paths must satisfy the same ratio requirement.
5. Confirm the liner wall thickness at the thinnest measured location is ≥ the
   minimum wall thickness derived from design requirements. A liner wall below
   the minimum is flagged even when MoS is positive (the MoS was computed on a
   nominal geometry that no longer holds).
6. Compute the effective qualified life = cycles_demonstrated / 4.0. If this
   value is less than cycles_required, flag a fatigue life shortfall; the
   vessel must either demonstrate additional cycles or reduce its required
   mission cycle count.
7. Aggregate all violation flags. The liner is compliant under clause 4.6.2
   only when the violations list is empty.

## Pitfalls

- Using the composite overwrap's strength allowable instead of the metallic
  liner's when checking MoS — the liner and overwrap carry different load
  fractions and must be assessed against their own allowables.
- Treating proof pressure evidence as equivalent to burst margin — passing a
  proof test at 1.1 × MEOP does not imply the burst ratio is 2.0; both checks
  are independently required.
- Skipping the wall thickness check when stress margins are positive — a liner
  wall below the design minimum represents a dimensional non-conformance that
  the stress check does not capture.
- Applying the fatigue scatter factor only to the failure data and not to the
  demonstrated cycle count — the scatter factor of 4.0 is applied as
  cycles_demonstrated / 4.0 ≥ cycles_required, meaning the tested life must
  be four times the required life.
- Ignoring the liner yield check on the grounds that the composite overwrap
  prevents gross rupture — for metallic-liner COSPE the liner is expected to
  remain elastic at MEOP; yielding before MEOP is a design violation, not an
  accepted condition.

## Behavior contract (gate 3)

The liner material categorization, margin of safety, proof and burst pressure
ratio, wall thickness, and fatigue life logic is exercised by the gate 3
contract test: scripts/test_cospe_metallic_liner.py against
scripts/cospe_metallic_liner_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_cospe_metallic_liner.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
