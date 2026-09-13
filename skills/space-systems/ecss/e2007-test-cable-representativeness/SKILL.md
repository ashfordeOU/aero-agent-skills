---
name: e2007-test-cable-representativeness
description: "Use when verify that a harness-sample wired onto an electromagnetic-compatibility bench reproduces the flight harness build practice of ECSS-E-ST-20-07C clause 5.2.6.6.1: compare twist-lay-length and the resulting twists-per-metre against the flight run, categorize the shield-construction as braid, foil, braid-over-foil or unshielded and compare braid-optical-coverage, categorize the shield-termination as circumferential-backshell, pigtail or unterminated, bound the pigtail self-inductance that a flight backshell would never add, and check the exposed run-length the setup geometry demands. Trigger: ecss, e-st-20-07c, harness-sample-representativeness, twist-lay-length, twists-per-metre, braid-optical-coverage, shield-termination-backshell, pigtail-inductance, exposed-run-length."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-test-cable-representativeness, harness-sample-representativeness, twist-lay-length, twists-per-metre, braid-optical-coverage, shield-termination-backshell, pigtail-inductance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Test Cable Representativeness (space-systems/ecss/e2007-test-cable-representativeness)

Use when the task is the harness-sample rule of ECSS-E-ST-20-07C
clause 5.2.6.6.1 -- showing that the cable a unit is wired up with for
an electromagnetic-compatibility run is built the way the flight
harness is built, in twisting, in shielding and in how the shield is
landed, rather than being a convenient bench lash-up.

## Domain quick reference

- The harness is the dominant coupling structure in most unit-level
  runs. Conducted emission leaves through it, radiated emission is
  largely radiated by it, and injected disturbance enters through it.
  A sample that differs from the flight build in twisting, shielding or
  termination measures a different antenna, so the result describes the
  bench and not the spacecraft.
- Twisting is captured by the lay length -- the axial distance for one
  full twist -- which converts directly to twists per metre. Tighter
  twisting shrinks the loop area of the differential pair and cuts
  magnetic-field coupling; an untwisted or loosely twisted sample
  standing in for a tightly twisted flight pair overstates susceptibility
  and can understate emission from the balanced mode.
- Shield construction splits into braid, foil, braid-over-foil and
  unshielded. Braid is graded by optical coverage, the fraction of the
  surface the braid actually closes, which drives the transfer
  impedance at the frequencies the run covers. Foil closes the surface
  fully but has no mechanical robustness and a higher resistance, so a
  foil sample is not a substitute for a braid one even at equal
  nominal coverage.
- Termination is where most of the representativeness is lost. A
  circumferential-backshell lands the shield around its whole
  circumference and keeps the transfer impedance low. A pigtail
  gathers the shield into a short wire, and that wire is a series
  inductance in the shield return, which lifts the transfer impedance
  steeply with frequency. Substituting a pigtail for a flight backshell
  is one of the most common ways a bench result goes optimistic on
  susceptibility and pessimistic on emission at once.
- Pigtail self-inductance follows the round-wire relation, growing with
  the pigtail length and falling only weakly with conductor diameter,
  which is why a pigtail is bounded by length rather than trimmed by
  using thicker wire.
- The exposed run-length matters as well: the setup geometry assumes a
  declared length of harness running parallel to the ground plane at a
  declared height, and a short sample simply presents less coupling
  structure to the measurement.

## Workflow

1. For each harness run in the setup, resolve the flight build and the
   sample build. Reject a run whose shield or termination hardware is
   declared inconsistently.
2. Convert both lay lengths to twists per metre and compare the sample
   against the flight run using the declared tolerance fraction. Flag a
   sample that is untwisted where the flight run is twisted.
3. Categorize both shield constructions. Flag a construction family
   mismatch, and for a braid or braid-over-foil pair compare optical
   coverage against the declared allowance in percentage points.
4. Categorize both shield terminations. Flag a family mismatch --
   above all a pigtail standing in for a circumferential-backshell --
   and flag an unterminated sample shield outright.
5. Where both sides are pigtails, compute the pigtail self-inductance
   from length and conductor diameter and check the sample against the
   declared inductance ceiling as well as the length ceiling.
6. Check the exposed run-length of the sample against the length the
   setup geometry requires.
7. Aggregate per run and across the setup. The harness-sample is
   representative only when every run's finding list is empty.

## Pitfalls

- Comparing lay length without converting to twists per metre. A
  longer lay is looser twisting, so the sense of the comparison
  inverts, and a raw lay-length difference alone hides which side is
  the tighter build.
- Treating equal nominal coverage as equal shielding. Foil and braid
  reach that coverage with different transfer impedance and different
  termination behaviour, so the construction family has to match before
  the coverage number means anything.
- Landing a shield with a pigtail because the backshell was not
  available. The pigtail inductance dominates the shield return above
  a few megahertz, and no amount of care in the rest of the setup
  recovers the transfer impedance the flight backshell would have had.
- Thickening the pigtail wire to buy margin. The round-wire relation
  moves the inductance only through a logarithm of the diameter, so the
  length ceiling is the control that actually works.
- Shortening the sample to fit the bench. The exposed run-length is
  part of the declared setup geometry, and a short run presents less
  coupling structure, which quietly lowers every emission reading.

## Behavior contract (gate 3)

The twist comparison, shield-construction and shield-termination
categorization, pigtail-inductance bounding, exposed run-length check
and aggregate representativeness logic is exercised by the gate 3
contract test: scripts/test_e2007_test_cable_representativeness.py
against scripts/e2007_test_cable_representativeness_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_test_cable_representativeness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
