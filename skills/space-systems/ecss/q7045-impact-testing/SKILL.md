---
name: q7045-impact-testing
description: "Assess a set of Charpy V-notch specimens against its requirement and the conditions it was broken under. Use when the methods clause of ECSS-Q-ST-70-45 calls for impact toughness: scale the requirement to the width below the notch so a sub-size bar is not judged against a full-size figure, hold the set average and every individual bar to their own floors, confirm each bar was struck within tolerance of the stated temperature after a long enough soak and a quick enough transfer, and report readings outside the usable part of the pendulum. Trigger: ecss, q-st-70-45, charpy-subsize-width-scaling, charpy-set-average-and-individual-floor, charpy-strike-temperature-tolerance, charpy-transfer-time-limit, charpy-pendulum-capacity-band."
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
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-impact-testing, charpy-subsize-width-scaling, charpy-set-average-and-individual-floor, charpy-strike-temperature-tolerance, charpy-transfer-time-limit, charpy-pendulum-capacity-band, charpy-lateral-expansion-minimum]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Impact Testing (space-systems/ecss/q7045-impact-testing)

Use when the methods clause of ECSS-Q-ST-70-45 calls for impact toughness: a
set of notched bars has been conditioned and broken by a swinging pendulum,
the absorbed energies are in hand, and the question is whether the set
satisfies its requirement and whether the conditions it was broken under let
the energies mean what the report says they mean.

## Domain quick reference

- A sub-size bar carries a sub-size requirement. The absorbed energy scales
  with the width below the notch, so holding a 5 mm bar to a full-size figure
  rejects compliant material for a reason that is arithmetic, not metallurgy.
- The requirement is a pair. A set average and an individual floor both have
  to hold, because one brittle bar averaged away by two tough ones is exactly
  the population the individual floor exists to catch.
- The energy belongs to a temperature. A bar that soaked too briefly never
  reached the medium, and a bar that waited too long between the bath and the
  anvil was struck somewhere between the medium and the room.
- The pendulum has a usable middle. Near the bottom of its capacity, windage
  and bearing friction are a large part of the reading; near the top, the
  hammer barely gets through and the reading saturates.
- Lateral expansion is a separate acceptance quantity from energy. A
  requirement that names it is not satisfied by an energy that clears its
  floor, and an unmeasured expansion against a stated minimum is a gap in
  the evidence rather than a pass.

## Workflow

1. Validate the set: at least three bars, no negative energies, and a width
   below the notch that is one of the standard sizes.
2. Scale the full-size requirement by the width factor to get the set average
   requirement, and take the individual floor from that scaled figure.
3. Compare the set average and then every individual bar, with inclusive
   comparisons so a bar landing exactly on its floor passes.
4. Compare each strike temperature against the stated temperature and its
   tolerance, one finding per bar that drifted.
5. Compare the soak duration and the transfer time against their limits, so
   the temperature the energies are reported at is defensible.
6. Express each reading as a fraction of the pendulum capacity and report the
   ones outside the usable band.
7. Compare lateral expansion against its minimum when one is stated, and
   report a stated minimum with no measurement behind it.

## Pitfalls

- Judging a sub-size set against the full-size requirement. It is the single
  most common way compliant material is rejected on paper.
- Reporting only the set average. The average is the number that hides the
  one bar the individual floor was written for.
- Treating transfer time as housekeeping. Five seconds of a thin bar out of a
  cold bath moves the notch temperature enough to move the energy.
- Choosing a pendulum far larger than the expected energy. The set reads low
  and consistently low, which looks like a material property.
- Letting a stated lateral-expansion minimum pass unmeasured. A requirement
  with no measurement is an open finding, not a silent pass.

## Behavior contract (gate 3)

The width scaling, the set average and individual floors, the strike
temperature tolerance, the soak and transfer conditions, the pendulum
capacity band, the lateral-expansion comparison and the set verdict are
exercised by the gate 3 contract test:
scripts/test_q7045_impact_testing.py against
scripts/q7045_impact_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7045_impact_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
