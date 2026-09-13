---
name: e2006-current-path-environmental-robustness
description: "Use when verify that the environments a spacecraft sees do not interrupt or degrade a bonding current path under ECSS-E-ST-20-06C clause 6.8.3: categorize each exposure as random-vibration, sine-vibration, mechanical-shock, acoustic-noise, thermal-cycling, thermal-vacuum or humidity-and-corrosion, confirm the exposure set required for the path class is complete, check each run reached the qualification level in the right unit and was held long enough, require live continuity-monitoring while the joint is mechanically excited, count monitored discontinuity events, and compare the pre/post bond-resistance drift and the post-exposure reading against the path-class allowance. Trigger: ecss, e-st-20-06c, clause-6-8-3, bonding-current-path-robustness, bond-resistance-drift, random-vibration-exposure, mechanical-shock-exposure, continuity-monitoring-during-exposure, environmental-exposure-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-current-path-environmental-robustness, bonding-current-path-robustness, bond-resistance-drift, random-vibration-exposure, mechanical-shock-exposure, continuity-monitoring-during-exposure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Current-Path Environmental Robustness (space-systems/ecss/e2006-current-path-environmental-robustness)

Use when the task is the evidence check of ECSS-E-ST-20-06C clause
6.8.3 -- demonstrating that the mechanical and thermal environments do
not break or progressively degrade the bonding current paths that carry
fault current, discharge current, a signal reference or a surface bleed.

## Domain quick reference

- Clause 6.8.3 is about survival, not about the as-built value. A bond
  that met its resistance bound on the bench and opens at resonance
  has failed the clause even if the post-exposure reading looks
  healthy, because an intermittent open re-closes when the excitation
  stops.
- Which exposures a path must have seen follows the path class. A
  fault-current-return-path and a discharge-return-path must have seen
  random-vibration, mechanical-shock and thermal-cycling; a
  signal-reference-bond needs random-vibration and thermal-cycling;
  a static-bleed-path needs random-vibration and
  humidity-and-corrosion, because corrosion of the bleed interface,
  not vibration, is what usually takes it out.
- Level adequacy is per environment and per unit: grms for
  random-vibration, g-peak for sine-vibration, g-srs-peak for
  mechanical-shock, cycle counts for thermal exposures, hours for
  humidity. A level compared across units is not a comparison at all,
  so a unit that does not belong to the environment is rejected
  outright rather than graded.
- Live continuity-monitoring is required while the joint is
  mechanically excited (random-vibration, sine-vibration,
  mechanical-shock, acoustic-noise). A monitored open at or beyond the
  discontinuity threshold is a failure regardless of the post-exposure
  reading. Thermal exposures are graded on the pre/post readings
  instead -- the degradation mechanism there is slow.
- Two resistance criteria apply after exposure, and both matter: the
  fractional drift from the pre-exposure value (a joint that moved
  significantly is relaxing or corroding even if it still passes) and
  the absolute post-exposure reading against the path-class limit.

## Workflow

1. Categorize the path class and look up the exposure set it must
   have on record, rejecting an unrecognized class.
2. Categorize each exposure record's environment and check the level
   in the environment's own unit against the qualification level.
3. Where a duration requirement applies, confirm the run was held for
   at least the required time.
4. Confirm live continuity-monitoring was in place for every
   mechanically exciting exposure, and count the monitored events at
   or beyond the discontinuity threshold.
5. Compute the pre/post resistance drift and compare its magnitude
   against the allowance; separately compare the post-exposure
   reading against the path-class limit.
6. Report the path robust only when the required exposure set is
   complete and every exposure passes all four checks; otherwise
   report it not-demonstrated with the per-exposure findings.
7. Roll the paths up into a campaign verdict for the verification
   review.

## Pitfalls

- Grading a vibration exposure on the post-run reading alone. The
  failure mode is an intermittent open under excitation; it leaves no
  trace once the shaker stops, so an unmonitored run cannot be
  evidence whatever the post reading says.
- Accepting a run below the qualification level because the bond
  survived -- the margin between the applied level and the
  qualification level is the evidence, not the survival.
- Comparing a shock level against a random-vibration requirement, or
  any level across mismatched units; the numbers are not the same
  quantity.
- Reading only the absolute post-exposure value and ignoring drift: a
  joint that doubled its resistance and still sits inside the limit is
  degrading and will not stay inside it.
- Treating a short glitch in the monitor as noise without a defined
  discontinuity threshold -- the threshold is what makes the
  monitoring evidence rather than an opinion.
- Declaring a path robust from the exposures it happened to see. The
  required set is driven by the path class, and an absent exposure is
  a finding, not a silent pass.

## Behavior contract (gate 3)

The environment categorization, exposure-level, duration, monitoring,
discontinuity-count, resistance-drift and campaign roll-up logic is
exercised by the gate 3 contract test:
scripts/test_e2006_current_path_environmental_robustness.py against
scripts/e2006_current_path_environmental_robustness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_current_path_environmental_robustness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
