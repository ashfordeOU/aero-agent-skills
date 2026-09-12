---
name: e20-electromagnetic-radiation-hazard-control
description: "Use when compute whether radiated fields keep people, propellant, ordnance and actuated thruster valves below their hazard thresholds under ECSS-E-ST-20C clause 6.3.3: categorize every receptor as personnel, fuel, ordnance or thruster actuation, derive the emitter's effective radiated power and far-field boundary, evaluate the incident power density in whichever field region the receptor stands in, compare it against the frequency-dependent occupational limit or the propellant-vapour limit, convert the power an initiator or valve drive couples out of that field into a decibel margin below its firing threshold, and size the separation distance the hazard limit demands. Trigger: ecss, e-st-20-electrical-scope, e-st-20c-clause-6-3-3, electromagnetic-radiation-hazard-control, radiation-hazard-to-personnel, radiation-hazard-to-ordnance, radiation-hazard-to-fuel, thruster-inadvertent-actuation, incident-power-density, minimum-safe-separation-distance."
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
  tags: [ecss, e-st-20-electrical-scope, e20-electromagnetic-radiation-hazard-control, radiation-hazard-to-personnel, radiation-hazard-to-ordnance, radiation-hazard-to-fuel, thruster-inadvertent-actuation, incident-power-density, minimum-safe-separation-distance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Electromagnetic Radiation Hazard Control (space-systems/ecss/e20-electromagnetic-radiation-hazard-control)

Use when the task is the clause 6.3.3 radiation hazard requirement of
ECSS-E-ST-20C -- showing that the transmitters on the vehicle, on the
pad and around the integration hall never put a hazardous field on a
person, on a propellant vapour, on an initiator, or on a thruster
valve that could be driven open by it.

## Domain quick reference

- Four receptor families are protected, and each is controlled by a
  different quantity. People and propellant vapours are controlled by
  the incident power density they stand in. Ordnance and thruster
  actuation are controlled by the power the firing circuit or the
  valve drive extracts from that field, because what matters at an
  initiator bridgewire is delivered watts, not the density in the air
  beside it. A receptor kind outside the four families is rejected
  rather than assumed harmless.
- The incident density depends on which field region the receptor
  stands in. The far field starts at twice the squared aperture
  diameter over the wavelength; beyond it the density is the effective
  radiated power spread over the sphere of that radius, and it falls
  with the square of range. Inside that boundary the spreading law
  does not hold and the density is better represented by the aperture
  plateau, four times the transmitter power over the physical aperture
  area, which is flat with range. A receptor inside the boundary is
  reported on that basis alone, because the plateau is an estimate
  standing in for a measured survey.
- The occupational limit for people is piecewise in frequency: flat at
  the low end, rising through the band where the body is most
  efficiently coupled, flat again at the top. It is continuous at both
  break points, so a limit table that jumps at 400 MHz or at 2 GHz has
  a transcription error. Outside the band the limit is undefined and
  the query is refused rather than extrapolated.
- The propellant-vapour limit is a single density figure, well above
  the personnel limit, and it is the ignition question, not the health
  question -- the two are checked separately even where the crew and
  the transfer line stand in the same place.
- The ordnance and thruster-valve check is a margin, not a comparison.
  Coupled power is incident density times the circuit's effective
  pickup area times its coupling efficiency, and the margin is ten
  times the base-ten logarithm of the firing or actuation threshold
  over that coupled power. Power ratios take ten times the logarithm,
  not twenty. Thruster actuation carries the stricter default margin
  of the two, because an inadvertently opened valve is a mission-level
  event with no safing step behind it.
- The separation distance is the inverse of the far-field density: the
  range at which a given radiated power falls to a stated limit. It is
  only meaningful outside the far-field boundary.

## Workflow

1. Categorize every receptor around the emitter into one of the four
   hazard families; reject a receptor kind that belongs to none.
2. Derive the emitter's effective radiated power from transmitter
   power, antenna gain and feed loss, and its far-field boundary from
   aperture and frequency.
3. For each receptor, decide the field region at its range and compute
   the incident power density with the law that region calls for;
   report any receptor standing inside the boundary.
4. For a personnel or fuel receptor, look up the density limit -- the
   frequency-dependent occupational value or the propellant-vapour
   value -- and flag a density above it.
5. For an ordnance or thruster receptor, compute the coupled power
   from pickup area and coupling efficiency, take the decibel margin
   below the firing or actuation threshold, and flag a margin below
   the requirement for that family.
6. Where a finding stands, compute the separation distance that brings
   the density to the limit and carry it into the pad layout or the
   transmit-inhibit rule.
7. Aggregate the findings; the emitter is cleared against clause 6.3.3
   only when the list is empty.

## Pitfalls

- Applying the spherical spreading law at a range inside the far-field
  boundary. Close to a large aperture it understates the density by
  orders of magnitude, and that is exactly where the pad crew and the
  umbilical ordnance sit.
- Using twenty times the logarithm for the coupled-power margin. That
  is the field-quantity form; a power ratio takes ten, and the error
  doubles every reported margin.
- Comparing incident density against an ordnance limit. Clause 6.3.3
  protects an initiator through the power its circuit couples in, and
  the pickup area and coupling efficiency of the installed harness are
  what decide it.
- Clearing a thruster valve on the ordnance margin. The valve is the
  stricter case of the two, and a margin that passes an initiator can
  still leave a valve inside its actuation window.
- Reading a zero coupled power as a proof of safety. It means the
  pickup area or the coupling efficiency was entered as zero, which is
  an unfilled input, not a measured result.
- Extrapolating the personnel limit below or above the band it is
  defined over instead of refusing the query and going back to the
  applicable exposure standard.

## Behavior contract (gate 3)

The receptor categorization, radiated-power, far-field boundary,
field-region, personnel and propellant limit, coupled-power,
decibel-margin and separation-distance logic is exercised by the gate 3
contract test:
scripts/test_e20_electromagnetic_radiation_hazard_control.py against
scripts/e20_electromagnetic_radiation_hazard_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_electromagnetic_radiation_hazard_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
