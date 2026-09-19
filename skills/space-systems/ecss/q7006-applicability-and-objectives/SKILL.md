---
name: q7006-applicability-and-objectives
description: "Determine whether a space material has to be irradiated at all under ECSS-Q-ST-70-06C and what objective the campaign carries: scale the mission particle fluence and the ultraviolet dose in equivalent sun hours from the predicted environment, read the exposure regime off the item location and its cover, decide which agents actually drive degradation, separate a screening run from a qualification or characterization run, apply the test-level factor the objective demands, and derive the properties the degradation is read on. Use when framing a radiation test request, sizing a campaign or reviewing a heritage argument offered instead of one. Trigger: ecss, q-st-70-06c, space-material-radiation-test-applicability, radiation-test-objective-decision, mission-particle-fluence-scaling, equivalent-sun-hours-dose, radiation-degradation-property-set, radiation-test-heritage-justification."
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
  tags: [ecss, q-st-70-06c-particle-and-uv-radiation-testing, q-st-70-06c, q7006-applicability-and-objectives, space-material-radiation-test-applicability, radiation-test-objective-decision, mission-particle-fluence-scaling, equivalent-sun-hours-dose, radiation-degradation-property-set, radiation-test-heritage-justification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Applicability and Objectives (space-systems/ecss/q7006-applicability-and-objectives)

Use when the task is the framework decision of ECSS-Q-ST-70-06C, taken before
any environment table or exposure profile is written: does this material need
a particle and ultraviolet degradation test, which agents drive it, what is
the campaign for, and which properties carry the answer.

## Domain quick reference

- The test exists to relate a property change to an exposure, not to produce a
  dose figure. Everything downstream — the environment definition, the coupon
  count, the measurement points — follows from which property is expected to
  move and by how much, so the property set is fixed at this stage.
- Two agents act, and they are stopped very differently. Ultraviolet is
  surface-absorbed and any solid cover removes it outright; charged particles
  are attenuated by mass, so a shielded item still sees the penetrating tail
  of the spectrum. An item behind a wall therefore has a particle-only test
  and a bare external surface has both.
- Exposure is scaled from the mission, not from the facility. The integrated
  fluence comes from the predicted flux, the duration and the fraction of the
  mission the item is actually exposed for; the ultraviolet dose is expressed
  in equivalent sun hours so that an eclipsed orbit is not charged for the
  time it spends in shadow.
- Objective decides the level, not the other way round. A qualification run is
  deliberately carried above the predicted exposure; a screening run and a
  characterization run are carried at it, because their product is comparative
  or model data rather than a capability statement.
- Metals, ceramics and glasses do not degrade in bulk at mission levels, but
  the exemption is a function exemption and not a material one: the moment the
  item is optically functional, a small change in transmittance or a trace of
  colour-centre formation is the result, and the low-exposure threshold that
  excuses a structural part no longer applies.
- Heritage displaces a test only when it envelopes it. The claim has to cover
  the fluence, the ultraviolet dose and the top of the energy spectrum, and be
  the same material from the same process route; failing any one of those the
  claim is evidence, not a substitute.

## Workflow

1. Validate the item description: location, cover thickness, material
   category and the function it performs. A non-positive duration or a
   fraction outside zero to one is an input error, not a degenerate case.
2. Scale the mission exposure: integrate the predicted particle flux over the
   exposed duration, and convert the illuminated fraction of the orbit into
   equivalent sun hours at the declared solar intensity.
3. Read the exposure regime — bare external surface or shielded item — from
   the location and the cover, remembering that a very thin cover already
   removes ultraviolet entirely.
4. Decide the applicable agents, applying the low-exposure threshold only to
   items that are not optically functional and exempting robust material
   categories on the same condition.
5. Grade any heritage claim against the mission envelope, spectrum top and
   process route; record each shortfall as a finding rather than discounting
   the claim silently.
6. Fix the objective from the agents, the heritage outcome and whether model
   data was asked for, then apply its test-level factor to each applicable
   mission exposure.
7. Derive the degradation property set from the material category and the
   function, and return the decision record with every finding.

## Pitfalls

- Testing a shielded item for ultraviolet. The cover removes the agent
  completely, so the run measures the facility rather than the material, and
  the particle exposure that does matter gets less beam time for it.
- Charging an eclipsed orbit for the whole mission duration. Equivalent sun
  hours exist precisely so that shadow time is not paid for; using elapsed
  time instead inflates the dose and the campaign with it.
- Letting the facility's convenient flux set the objective. The level follows
  from the objective and the predicted environment; a facility that cannot
  reach it is a facility finding, not a reason to relabel a qualification run
  as a screening run.
- Applying the low-exposure threshold to an optical item. A coverglass or a
  lens shows a measurable transmittance change far below the fluence at which
  a structural polymer is worth testing, and the exemption quietly deletes the
  one measurement that mattered.
- Accepting heritage on the material name alone. A different cure schedule,
  pigment lot or coating line changes the surface chemistry the degradation
  happens in, so a same-material claim from a different process route is not
  an enveloping claim.
- Deciding the property set after the exposure. Coupon count, measurement
  points and whether a property can be read without breaking the specimen all
  depend on the property list, so fixing it late forces a second campaign.

## Behavior contract (gate 3)

The mission exposure scaling, exposure-regime decision, agent applicability,
objective and test-level derivation, property-set construction and heritage
grading are exercised by the gate 3 contract test:
scripts/test_q7006_applicability_and_objectives.py against
scripts/q7006_applicability_and_objectives_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7006_applicability_and_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
