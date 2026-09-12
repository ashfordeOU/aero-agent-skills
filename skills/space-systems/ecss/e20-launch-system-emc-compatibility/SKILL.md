---
name: e20-launch-system-emc-compatibility
description: "Use when assess the electromagnetic environment a spacecraft meets before and during launch and demonstrate compatibility with it under ECSS-E-ST-20C clause 6.3.2.2: categorize each campaign phase as prelaunch or launch and each environment source as a launch-site fixed emitter, a launcher-borne emitter, a processing-facility emitter or an electrostatic source, compute the free-space field an emitter puts on the spacecraft at its separation distance, attenuate it through the fairing while the vehicle is encapsulated, check the source sits beyond the far-field boundary, confirm its frequency falls inside the tested susceptibility envelope, and hold the required margin in every mandatory phase. Trigger: ecss, e-st-20c-clause-6-3-2-2, launch-campaign-emc, prelaunch-electromagnetic-environment, launch-site-emitter, fairing-shielding-effectiveness, radiated-susceptibility-margin, far-field-boundary-check, triboelectric-charging-control."
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
  tags: [ecss, e-st-20-electrical-scope, e20-launch-system-emc-compatibility, launch-campaign-emc, prelaunch-electromagnetic-environment, launch-site-emitter, fairing-shielding-effectiveness, radiated-susceptibility-margin, far-field-boundary-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Launch System EMC Compatibility (space-systems/ecss/e20-launch-system-emc-compatibility)

Use when the task is the clause 6.3.2.2 launch-system electromagnetic
compatibility duty of ECSS-E-ST-20C -- writing down the environment
the spacecraft is exposed to from the moment it reaches the launch
site until it leaves the launcher, and showing that the design as
qualified survives every part of it.

## Domain quick reference

- The campaign splits into prelaunch phases (payload processing,
  fuelling, encapsulation, transfer to the pad, on-pad standby, final
  countdown) and launch phases (liftoff, atmospheric ascent, fairing
  jettison, upper-stage flight, separation). The split matters because
  the exposure changes with it, and a phase that carries no assessment
  is a hole in the case whatever the other phases show.
- Four kinds of source make up the environment. A launch-site fixed
  emitter (tracking radar, range safety command transmitter, ground
  telemetry, weather or surveillance radar) is the strongest and the
  furthest away. A launcher-borne emitter (launcher telemetry, a radar
  transponder, a receiver local oscillator) is weak but sits metres
  from the spacecraft. A processing-facility emitter (a handheld
  radio, wireless networking, a crane drive) only exists while people
  are around the vehicle. An electrostatic source (triboelectric
  charging, a lightning-induced transient, precipitation static) is
  not an emitter at all: it is controlled by a bonding and dissipation
  provision, not by a field computation, and asking for its field
  strength is a category error.
- The field an emitter puts on the spacecraft follows from its
  radiated power and its distance under the free-space far-field
  relation. That relation is only valid beyond the far-field boundary
  set by the emitting aperture and the wavelength; inside it the
  computed number is meaningless and a measurement or a near-field
  model is required instead. While the vehicle is encapsulated the
  fairing attenuates the incident field by its shielding
  effectiveness, which is why an on-pad radar illumination that would
  be alarming in the clean room is often benign in the countdown.
- Compatibility is the separation between the level the spacecraft was
  qualified to at that frequency and the field it actually sees. A
  frequency outside the tested envelope has no qualification level
  behind it, so it cannot produce a margin at all -- that is a finding
  in its own right and not a pass by omission.

## Workflow

1. Categorize every declared campaign phase as prelaunch or launch and
   reject a phase that belongs to neither.
2. Compare the declared phases against the mandatory campaign set and
   flag each phase that carries no assessment.
3. Categorize every environment source; route electrostatic sources to
   the dissipation-provision check and every emitter to the field
   computation.
4. For each emitter, confirm the spacecraft sits beyond the far-field
   boundary for that frequency and aperture; flag the pair when it
   does not, because the free-space field is not applicable there.
5. Compute the free-space field at the separation distance and, for a
   phase in which the vehicle is encapsulated, attenuate it by the
   fairing shielding effectiveness.
6. Look the qualification level up at the emitter frequency; flag a
   frequency that falls outside every tested band instead of scoring
   a margin against nothing.
7. Compute the separation between the qualification level and the
   incident field and flag a margin short of the requirement,
   absorbing representation error at the exact boundary.
8. Aggregate the phase-coverage, near-field, frequency-coverage,
   margin and electrostatic findings; the campaign is compatible only
   when every list is empty.

## Pitfalls

- Assessing the on-pad phases only. The clean-room and transfer phases
  are unencapsulated, so the fairing attenuation that makes the pad
  case comfortable simply is not there, and the facility emitters that
  only exist while people are present are at their closest.
- Applying the fairing shielding effectiveness after jettison. Once
  the fairing is gone the spacecraft is exposed again, and an ascent
  case built on an encapsulated assumption understates the upper-stage
  environment.
- Using the free-space relation for a launcher-borne emitter a couple
  of metres away. At those distances the spacecraft is usually inside
  the far-field boundary, where the relation does not hold and the
  number it produces is not conservative in any known direction.
- Scoring a margin against an extrapolated qualification level at a
  frequency that was never tested. No test, no level, no margin -- the
  gap belongs in the report, not in an interpolation.
- Treating triboelectric charging as a weak emitter and computing a
  field for it. It is controlled by a conductive path to structure,
  and the check is that the provision exists.
- Widening the required margin so an exact-boundary case passes; the
  tolerance belongs in the comparison, never in the requirement.

## Behavior contract (gate 3)

The phase and source categorization, encapsulation, free-space field,
far-field boundary, fairing attenuation, qualification-level lookup,
margin and aggregated-campaign logic is exercised by the gate 3
contract test: scripts/test_e20_launch_system_emc_compatibility.py
against scripts/e20_launch_system_emc_compatibility_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_launch_system_emc_compatibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
