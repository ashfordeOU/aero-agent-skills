---
name: e20-overall-emc-programme-establishment
description: "Use when establish the supplier electromagnetic compatibility programme for a spacecraft under ECSS-E-ST-20C clause 6.2.1: map each declared compatibility activity onto the programme area it serves, derive the area set the mission profile actually demands from its radio frequency payload, ordnance, magnetic sensor, crewed element and launcher exposure, list the areas and the mandatory programme elements nobody has declared yet, check every activity names an owner and is established no later than the milestone at which it can still shape the design, and apply the programme margin policy to each victim circuit category. Trigger: ecss, e-st-20-electrical-scope, overall-emc-programme-establishment, spacecraft-emc-programme-setup, emc-programme-area-coverage, emc-programme-milestone-establishment, emc-programme-margin-policy, named-emc-authority."
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
  tags: [ecss, e-st-20-electrical-scope, e20-overall-emc-programme-establishment, overall-emc-programme-establishment, spacecraft-emc-programme-setup, emc-programme-area-coverage, emc-programme-milestone-establishment, emc-programme-margin-policy, named-emc-authority]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Overall EMC Programme Establishment (space-systems/ecss/e20-overall-emc-programme-establishment)

Use when the task is the clause 6.2.1 set-up of ECSS-E-ST-20C -- the
supplier declaring what its electromagnetic compatibility programme
covers at spacecraft level, who owns each activity, by which milestone
each part of the programme is established, and which margin policy the
programme applies.

## Domain quick reference

- The programme is described by activities, and each activity serves
  exactly one compatibility area: emission control, susceptibility
  control, grounding and bonding, shielding and harness routing,
  electrostatic discharge control, magnetic cleanliness, radio
  frequency compatibility, radiation hazard, lightning and launch-site
  compatibility, or intersystem compatibility with the launcher. An
  activity that serves no recognised area is a programme entry nobody
  can review.
- Five areas are unconditional at spacecraft level: emission control,
  susceptibility control, grounding and bonding, shielding and harness
  routing, and electrostatic discharge control. Every other area is
  pulled in by the mission profile -- a radio frequency payload pulls
  in frequency compatibility, ordnance or a crewed element pulls in
  radiation hazard control, a magnetometer or a magnetically sensitive
  instrument pulls in magnetic cleanliness, use of launch-site services
  pulls in lightning and site compatibility, and a launcher electrical
  interface pulls in intersystem compatibility. Deriving the area set
  from the profile is what stops the programme from being a generic
  table copied between projects.
- Beyond the activities, the programme owes a fixed set of elements:
  the control plan, the approach to predictive work, the verification
  programme, the interference-critical point list, the requirement
  flow-down, and a named compatibility authority. An element declared
  with a blank value is absent -- a row with no document number
  delivers nothing.
- Each area has a last milestone at which it can still be established
  without forcing a redesign. Emissions, susceptibility and the
  grounding concept must be fixed by the preliminary design review
  because the architecture depends on them; shielding rules,
  electrostatic discharge control, magnetic cleanliness, frequency
  compatibility and hazard control can still be fixed at the critical
  design review; launch-site and launcher compatibility can be closed
  later because they depend on the receiving side.
- The programme's margin policy binds the interference-critical points:
  the margin is the distance in decibels between the level a victim
  circuit tolerates and the level predicted at its terminals, and the
  required value follows the circuit category -- an ordnance or
  safety-critical circuit demands far more than a standard one. That
  margin is a difference of decibel values, so an exactly-met policy
  can land a unit in the last place low; the comparison absorbs the
  representation error rather than relaxing the policy.

## Workflow

1. Categorize each declared activity into its compatibility area;
   reject an activity that is not a clause 6.2.1 spacecraft-level
   compatibility activity.
2. Derive the required area set from the mission profile flags,
   rejecting an unrecognized or non-boolean flag before it silently
   removes an area from the programme.
3. Subtract the covered areas from the required set and report every
   area with no activity behind it; compute the coverage fraction.
4. Check the mandatory programme elements and report each one absent or
   declared with a blank value.
5. For each activity, confirm it names an owner and that its
   establishment milestone is not later than the last milestone at
   which its area can still shape the design.
6. For each interference-critical point, compute the margin in decibels
   from the susceptibility threshold and the predicted level, look up
   the margin its circuit category demands, and flag a point that does
   not hold it.
7. Aggregate the area, element, activity and margin findings. The
   programme is established only when every list is empty and the area
   coverage is complete.

## Pitfalls

- Reusing the previous project's activity table without re-deriving the
  area set from this mission's profile -- adding an ordnance train or a
  magnetometer changes what the programme must cover, and a copied
  table reports full coverage of the wrong set.
- Declaring an area covered because a document title mentions it; the
  test is an activity with an owner and an establishment milestone,
  not a heading.
- Establishing the grounding and bonding concept at the critical design
  review to save early effort -- by then the structure, harness routing
  and box interfaces are committed, and the concept is documenting a
  decision rather than driving one.
- Listing the compatibility authority as an organisation rather than a
  named role, then finding at the first interference case that nobody
  holds the decision.
- Applying one margin to every interference-critical point; the
  category of the victim circuit is the whole reason the policy exists,
  and a single value either over-constrains ordinary circuits or
  under-protects the critical ones.
- Failing an exactly-met margin because a decibel subtraction landed a
  unit in the last place low, then raising the declared threshold to
  make it pass -- the fix belongs in the comparison, never in the
  policy.

## Behavior contract (gate 3)

The activity categorization, profile-driven area derivation,
programme-element, ownership and milestone, and margin-policy logic is
exercised by the gate 3 contract test:
scripts/test_e20_overall_emc_programme_establishment.py against
scripts/e20_overall_emc_programme_establishment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_overall_emc_programme_establishment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
