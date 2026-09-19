---
name: e2021-generic-actuator-electronics-ratings
description: "Size the output power and output current a reusable actuator electronics design should be rated for, per clause 5.5.4 of ECSS-E-ST-20-21C. Use when a family of actuator loads has to fix one generic driver rating rather than a rating per project: form each load's demand from its lowest resistance against its highest drive voltage, sum the loads that fire together so a salvo outranks its members, take the envelope over those groups instead of a family mean, apply the design margin once at the envelope, then grade the declared ratings against that envelope and against the recommended generic capability. Trigger: ecss, e-st-20-21c, generic-actuator-electronics-ratings, reusable-driver-sizing, output-power-capability, output-current-capability, simultaneous-firing-group, rating-sizing-driver."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-5-4, e2021-generic-actuator-electronics-ratings, e-st-20-21c, generic-actuator-electronics-ratings, reusable-driver-sizing, output-power-capability, output-current-capability, simultaneous-firing-group]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Generic Actuator Electronics Ratings (space-systems/ecss/e2021-generic-actuator-electronics-ratings)

Use when the task is clause 5.5.4 of ECSS-E-ST-20-21C: an actuator
electronics intended for reuse is recommended to carry an output power
and an output current capability a later actuator will still fit inside.
This leaf turns a family of loads into those two ratings and grades a
declared pair against them.

## Domain quick reference

- A generic design is rated for the actuator that has not been chosen
  yet. Rating it to the loads of the first project is what makes the
  second project open the box, which is the cost the recommendation
  exists to avoid.
- Each load's demand is taken at its own corner: the lowest resistance
  it can present against the highest drive voltage the design permits.
  The nominal pair produces a demand that no qualification case
  exercises and that the first cold, low-tolerance unit exceeds.
- Actuators fired together are one demand. The driver has to source the
  sum over the simultaneously fired group, so a two-initiator salvo
  outranks either initiator alone, and the envelope is taken over groups
  rather than over individual loads.
- The envelope is a maximum, never a mean. Averaging a family lets a
  crowd of small latches pay for the one heavy separation salvo, and the
  rating that comes out is below a demand already on the manifest.
- The design margin is applied once, at the envelope. Applying it per
  load and again at the envelope compounds it into hardware nobody
  asked for; omitting it rates the unit at exactly the demand already
  seen, with nothing left for the load not yet known.
- Covering today's family is necessary and not sufficient. The
  recommended generic capability is the second condition, and a driver
  that clears its own project while sitting under that figure is a
  project driver wearing a generic label.
- Each rating names the group that drove it, because that is the load to
  renegotiate, re-group or move to its own driver when the rating turns
  out to be unaffordable.

## Workflow

1. Validate the specification: a non-negative design margin fraction and
   positive recommended capability figures for current and power.
2. Form each load's demand from its minimum resistance and its maximum
   drive voltage, defaulting a load with no declared group to a group of
   its own so a non-salvo family still works.
3. Sum the demands inside every simultaneously fired group and reject a
   family with duplicate load names, which would otherwise double-count
   or silently drop a load.
4. Take the envelope as the largest group demand for current and for
   power independently, since the two can be driven by different groups.
5. Apply the design margin once to each envelope to obtain the required
   ratings, and record what the envelope was before the margin so the
   two are never confused.
6. Grade each declared rating twice: against the required rating from
   the family, and against the recommended generic capability, treating
   an exact match with a named tolerance rather than by relaxing either.
7. Report the shortfalls, name the sizing group behind each rating, and
   return the rating token.

## Pitfalls

- Sizing on nominal resistance and nominal bus voltage. Both move the
  demand the wrong way, and the combination understates the current by
  more than any margin a reviewer would accept.
- Treating a salvo as its individual initiators. The driver never sees
  them one at a time, and a rating that covers the largest single
  initiator is short by the rest of the group.
- Averaging the load family. The mean is not a demand anything makes,
  and a family of many small latches plus one separation salvo averages
  down to a rating the salvo exceeds on its first firing.
- Applying the design margin per load and again at the envelope. The
  allowance compounds, and the resulting rating is expensive in mass and
  dissipation for no requirement.
- Rating the unit to the current family and calling it generic. The
  recommended capability is what makes the design reusable, and a driver
  under it will be redesigned by the next project that needs it.
- Reporting an inadequate rating without naming the sizing group. The
  action is a load-side action -- re-group the salvo, split it across
  drivers, raise the actuator resistance -- and it cannot be taken
  against a bare number.

## Behavior contract (gate 3)

The specification validation, per-load corner demand, simultaneous group
summation, envelope selection, single margin application, dual grading
against the family and the generic baseline, and sizing-group naming are
exercised by the gate 3 contract test:
scripts/test_e2021_generic_actuator_electronics_ratings.py against
scripts/e2021_generic_actuator_electronics_ratings_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2021_generic_actuator_electronics_ratings.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
