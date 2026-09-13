---
name: e2007-test-area-occupancy-limits
description: "Use when determine which people and which hardware may stay inside a shielded electromagnetic enclosure under ECSS-E-ST-20-07C clause 5.2.5.2: match every rostered occupant against the roles the running mode genuinely needs, withdraw an occupant holding no run-step justification, categorize each declared item as article-under-verification, support-equipment, measurement-instrument, field-probe or stray, check the surviving headcount against the evacuation-route capacity, and sum the standing and hardware footprint inside the quiet-zone so the field-perturbation fraction stays under its allowance. Non-essential occupants, unjustified hardware, an over-capacity headcount and a perturbed quiet-zone are reported separately. Trigger: ecss, e-st-20-electrical-scope, e-st-20-07c-clause-5-2-5-2, enclosure-occupancy-control, essential-personnel-justification, quiet-zone-perturbation, shielded-enclosure-access, stray-item-withdrawal, egress-route-capacity."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-test-area-occupancy-limits, enclosure-occupancy-control, essential-personnel-justification, quiet-zone-perturbation, shielded-enclosure-access, stray-item-withdrawal, egress-route-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Enclosure Occupancy Limits (space-systems/ecss/e2007-test-area-occupancy-limits)

Use when the task is the occupancy obligation of ECSS-E-ST-20-07C clause
5.2.5.2 -- deciding who and what is allowed to remain inside a shielded
measurement enclosure while a step runs, and showing that everything left
inside is there because the running step needs it.

## Domain quick reference

- Two independent reasons drive the clause and they must not be collapsed.
  The safety reason is exposure and evacuation: an energized radiating or
  high-voltage step exposes whoever is inside, and the evacuation route
  has a finite capacity. The measurement reason is perturbation: every
  body and every unneeded object inside the quiet-zone scatters and
  absorbs the field the measurement depends on. A roster can satisfy one
  and violate the other, so both are evaluated and reported separately.
- Necessity is per run mode, not per facility. An emission step needs the
  run conductor and the measurement engineer; a susceptibility step adds
  the safety officer because a drive level is being raised; an
  enclosure-calibration step needs only the measurement engineer and has
  no article inside at all. Two situational additions extend the set: an
  article that must be commanded from inside brings its operator, and a
  formally witnessed acceptance step brings the quality witness. An
  observer or a visitor is never in the necessary set for any mode.
- Necessity of the role is not sufficient by itself. Each occupant also
  carries a justification naming the step they are there for, because a
  correctly-titled person with no job in the running step is exactly the
  occupancy the clause removes. A role that ends up with nobody left
  holding it is reported as an absent required role, which is a different
  finding from an occupant being withdrawn.
- Hardware is sorted the same way: an item serving a recognized function
  with a justification stays, and anything else -- an unfunctioned
  toolbox, a support rack left over from the previous step -- is
  uncategorized for this step and withdrawn. A verification step also has
  to contain the article it verifies; a calibration step does not.
- The perturbation check counts only what stays. Bodies count at a
  standing footprint, items at their declared footprint, and items
  recorded outside the quiet-zone contribute nothing. The occupied
  fraction is weighed against the allowance for the quiet-zone floor area.
- A fraction assembled by summing footprints can land a few units in the
  last place above an allowance it is physically equal to. The comparison
  absorbs that representation error; the allowance itself is never
  widened.

## Workflow

1. Establish the run mode and its situational flags, then derive the
   necessary role set. Reject an unrecognized run mode before anything
   else runs.
2. Walk the roster: withdraw an occupant whose role is not in the
   necessary set, withdraw an occupant with no run-step justification, and
   keep the rest. Reject a duplicated badge or an unrecognized role.
3. Report every necessary role left with no occupant as an absent
   required role, so a withdrawal never silently strips the step of a
   function it needs.
4. Categorize every declared item by its function and justification;
   report each stray item for withdrawal, and report an absent
   article-under-verification for any mode that requires one.
5. Check the surviving headcount -- not the rostered headcount -- against
   the evacuation-route capacity.
6. Sum the standing footprint of the surviving occupants and the footprint
   of the retained items that sit inside the quiet-zone, divide by the
   quiet-zone floor area, and report an exceedance of the perturbation
   allowance.
7. The step is clear to run only when personnel, hardware, egress and
   perturbation each return an empty finding list.

## Pitfalls

- Sizing the egress check on the rostered headcount rather than on the
  headcount that survives withdrawal, which either blocks a compliant step
  or hides the fact that the compliant step still cannot be evacuated.
- Counting stray hardware in the perturbation sum. The stray item is being
  withdrawn, so including its footprint invents an exceedance that the
  corrected configuration does not have; it belongs in the withdrawal
  list, not in the fraction.
- Treating a correct job title as the justification. The clause removes
  people with no role in the running step, and a titled occupant with no
  named task is exactly that case.
- Forgetting that a withdrawal can leave a needed function uncovered --
  removing the only measurement engineer is a compliance finding, not a
  tidier enclosure.
- Reading the calibration mode through the verification checklist and
  flagging a missing article that the mode never has.
- Widening the perturbation allowance to clear a configuration that
  exceeds it by a few units in the last place. The representation error
  belongs in the comparison; the allowance stays where the facility set
  it.

## Behavior contract (gate 3)

The necessary-role derivation, roster withdrawal, item categorization,
egress-capacity and quiet-zone-perturbation logic is exercised by the gate
3 contract test: scripts/test_e2007_test_area_occupancy_limits.py against
scripts/e2007_test_area_occupancy_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_test_area_occupancy_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
