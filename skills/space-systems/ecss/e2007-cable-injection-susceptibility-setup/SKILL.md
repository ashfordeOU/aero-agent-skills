---
name: e2007-cable-injection-susceptibility-setup
description: "Derive the coupling arrangement ECSS-E-ST-20-07C clause 5.4.8.3 asks for from the standard bench layout: apply each declared delta to the baseline bands, refuse an unknown delta or one that closes a band, grade harness length, harness height, both probe distances and bond resistance against those bands, confirm the monitor probe sits between the injection probe and the unit, bound their separation by the probe aperture below and a fraction of a wavelength above, compare the band ceiling with the exposed harness resonance, and turn a jig-to-bench impedance mismatch into a drive error. Use when a harness injection setup is built or reviewed. Trigger: ecss, e-st-20-07c, cable-injection-susceptibility-setup, harness-injection-bench-layout, injection-monitor-probe-separation, exposed-harness-resonance-ceiling, injection-jig-calibration-error, injection-bench-governing-parameter."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-cable-injection-susceptibility-setup, harness-injection-bench-layout, injection-monitor-probe-separation, exposed-harness-resonance-ceiling, injection-jig-calibration-error, injection-bench-governing-parameter]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Cable Injection Susceptibility Setup (space-systems/ecss/e2007-cable-injection-susceptibility-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause 5.4.8.3 --
arranging the bench that couples a susceptibility signal onto a harness
bundle. The clause does not build a bench from nothing: it starts from the
standard layout already used for the other runs and modifies it only where
coupling current onto a bundle, and monitoring what actually flowed,
demands something different.

## Domain quick reference

- The arrangement is derived, not independent. Every departure from the
  standard layout is a declared delta with a reason; an undeclared
  departure is a setup finding even when the number it produces looks
  reasonable. A delta may move a band, never close it, so a delta leaving a
  parameter with no admissible value is an input error rather than a very
  tight bench.
- Two probes sit on the bundle and their order is the whole point. The
  monitor has to be between the injection point and the unit, because that
  is the only place where what it reads is what reaches the unit. Behind
  the injection probe it reads the current going the other way, into the
  support equipment.
- Their separation is bounded from both sides and the bounds come from
  different physics. Too close and the two apertures couple to each other
  rather than to the harness; too far and, at the top of the band, the
  separation is an appreciable part of a wavelength and the monitored
  current is a different point on a standing wave.
- The exposed harness run has a quarter-wave resonance, and it is the
  ceiling on the whole layout. Below it the injected current is roughly
  the same wherever the probe sits; above it the current depends on probe
  position, and the run stops being repeatable from one bench to the next.
- Height above the ground plane and bond resistance still set the return
  path. Common-mode current has to come back somewhere, and a poor bond
  turns the return into an uncontrolled part of the injected loop.
- An injection probe is calibrated in a jig of known impedance. The bench
  is not the jig, and the difference is a decibel error on any drive level
  set from the calibration alone. Closing the loop on the monitor probe
  absorbs that error into extra amplifier drive; leaving it open means the
  current injected is simply not the current calibrated.
- A capacitive clamp couples through the harness jacket instead of around
  the bundle, so what it injects depends on the build of that particular
  harness. It is usable, and it is a limitation that travels with the
  results.

## Workflow

1. Validate the realized bench: a recognized coupling method and level
   control, positive geometry, aperture, band ceiling and impedances, a
   non-negative bond resistance, and a deviation list naming only graded
   parameters.
2. Resolve the bands: start from the standard layout and apply each
   declared delta, refusing an unknown parameter, an unknown delta key and
   any delta that collapses a band.
3. Grade each geometry parameter against its resolved band as conforming,
   a declared deviation, or nonconforming.
4. Check the probe order first, then bound the separation from below by the
   probe aperture and from above by the wavelength fraction at the top of
   the band.
5. Take the quarter-wave resonance of the exposed harness and compare it
   with the band ceiling the run is specified to.
6. Form the decibel error between the calibration jig impedance and the
   bench impedance, and route it by how the level is controlled: a finding
   open loop, a limitation closed loop.
7. Rank the graded parameters by their fractional distance from the nearer
   band edge and name the governing one, then aggregate. The setup stands
   only when no finding stands.

## Pitfalls

- Treating the injection bench as a fresh arrangement. It inherits the
  standard layout, and a parameter nobody thought to declare is still being
  changed silently.
- Putting the monitor probe on the far side of the injection probe, where
  it measures the current flowing away from the unit and reports a level
  the unit never saw.
- Setting the probe separation by what fits on the bench. It has a floor
  from mutual coupling and a ceiling from the wavelength, and only one of
  those is obvious in the room.
- Running the band up past the resonance of the exposed harness, which
  makes the injected current a function of where the probe was clamped and
  quietly removes repeatability.
- Setting the drive from the jig calibration on a bench whose common-mode
  impedance is nothing like the jig, then reporting a level that was never
  injected.
- Accepting a declared deviation as if it were conformance. It keeps the
  run usable, but it travels with the results as a limitation and has to
  reach whoever reads them.

## Behavior contract (gate 3)

The bench validation, delta resolution and band grading, probe order and
separation bounding, harness resonance ceiling, jig-to-bench calibration
error routed by level control, governing-parameter ranking and the
aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_cable_injection_susceptibility_setup.py against
scripts/e2007_cable_injection_susceptibility_setup_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_cable_injection_susceptibility_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
