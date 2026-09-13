---
name: e2007-test-ground-plane-general
description: "Use when verify that the ground-plane arrangement under a unit on electromagnetic-compatibility test reproduces the known flight-installation arrangement of ECSS-E-ST-20-07C clause 5.2.3.1: categorize the flight mounting-interface as hard-mounted, isolator-mounted or stand-off-mounted, require the test plane to share the conduction family of the flight mounting-panel, check plane area, shortest edge, unit set-back and lateral extension beyond the unit footprint, check the plane-to-facility bonding-path for bond-point count and strap-chain direct-current resistance, and raise a finding when the flight arrangement is neither known nor bounded by a declared worst-case. Trigger: ecss, e-st-20-electrical-scope, test-ground-plane, ground-plane-representativeness, flight-installation-arrangement, emc-test-setup, mounting-interface, plane-bonding-path, unit-footprint-extension."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-test-ground-plane-general, test-ground-plane, ground-plane-representativeness, flight-installation-arrangement, emc-test-setup, plane-bonding-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Test Ground Plane, General (space-systems/ecss/e2007-test-ground-plane-general)

Use when the task is the general ground-plane arrangement of
ECSS-E-ST-20-07C clause 5.2.3.1 -- showing that the plane a unit is
mounted on for an electromagnetic-compatibility test reproduces the
installation arrangement the unit actually flies in, rather than a
convenient bench substitute.

## Domain quick reference

- The clause anchor is a representativeness requirement, not a
  performance requirement: the measured emission and susceptibility of
  a unit depend on the return path its mounting structure offers, so
  the plane under the unit on test has to stand in for the flight
  mounting-panel. Two setups that differ only in mounting structure
  can produce markedly different conducted and radiated results on the
  same hardware.
- Four properties carry the representativeness: the conduction family
  of the plane (metallic, composite or dielectric), the geometry of
  the plane relative to the unit footprint, the bonding-path from the
  plane to the facility reference, and the mounting-interface kind
  (hard-mounted, isolator-mounted or stand-off-mounted). A deviation
  in the conduction family or the interface kind changes the return
  path itself and is a major finding; a deviation in grade within one
  family, or in set-back, degrades the fidelity and is a minor one.
- The house verification defaults this leaf applies are a plane area
  floor of 2.25 square metres, a shortest-edge floor of 760 mm, a
  nominal unit set-back of 100 mm from the front edge with a 20 mm
  tolerance, a lateral extension floor of 500 mm beyond the unit
  footprint on each side, at least two plane-to-facility bond points,
  and a strap-chain direct-current resistance at or below 2.5
  milliohms. A programme may tighten any of them; each is a module
  constant so an override is explicit.
- An unknown flight arrangement is itself a finding. The clause is
  anchored on a *known* installation, so an assessment run against an
  undefined arrangement can only close if a worst-case arrangement has
  been declared and recorded, and even then it closes as a minor
  finding, never as a clean pass.
- The direct-current resistance of the plane itself is out of scope
  here: a metallic plane is capped by clause 5.2.3.2 and a composite
  plane has to reproduce the surface-resistivity of the real
  installation per clause 5.2.3.3. This leaf checks the arrangement;
  those two check the plane material.

## Workflow

1. Establish whether the flight installation arrangement is known.
   If it is not, check whether a worst-case arrangement has been
   declared; record the bounded case as a minor finding and an
   undefined case as a major one, then continue the assessment against
   whatever arrangement was declared.
2. Resolve the conduction family of the flight mounting-panel and of
   the proposed test plane. Reject an uncategorized material outright
   rather than guessing its family. A family mismatch is major; the
   same family in a different grade is minor.
3. Check the plane geometry against the unit footprint: plane area
   against the area floor, shortest edge against the edge floor,
   lateral extension per side against the extension floor, and the
   front set-back against its nominal and tolerance. Reject a unit
   footprint larger than the plane dimension it sits on.
4. Check the bonding-path from the plane to the facility reference:
   the bond-point count against the floor, and the strap-chain
   direct-current resistance -- summed over the chain when segment
   resistances are supplied -- against the cap. Separately flag a test
   plane bonded at fewer points than the flight installation.
5. Check the mounting-interface kind. A flight isolator replaced by a
   hard-mounted test interface, or an isolator added where the flight
   unit is hard-mounted, is major; any other substitution between
   hard-mounted and stand-off-mounted is minor.
6. Aggregate every finding into one report. The setup is compliant
   when no major finding stands, and fully representative only when
   the minor list is empty as well.

## Pitfalls

- Reading a clean geometry check as a representative setup -- a plane
  of the right size in the wrong conduction family offers a different
  return path and fails the clause even though every dimension passes.
- Removing a flight mounting isolator "to get a cleaner ground" -- the
  isolator is part of the installation the clause points at, and
  hard-mounting the unit for convenience changes the very impedance
  the test is meant to measure through.
- Treating an unknown flight arrangement as a pass because nothing
  contradicted the setup -- an arrangement that was never captured is
  a finding in its own right, and only a declared worst-case lets the
  assessment close at all.
- Bonding the plane to the facility at a single point and reading the
  low measured resistance as sufficient -- the count and the
  resistance are separate requirements, and a single point leaves the
  plane's reference dependent on one strap.
- Letting a boundary case fail on representation error -- a strap
  chain that sums to exactly the cap in decimal can land a few units
  in the last place above it in binary, so the comparison absorbs that
  with a tolerance instead of widening the engineering cap.

## Behavior contract (gate 3)

The installation-knowledge, geometry, material-family, bonding-path
and interface-kind logic is exercised by the gate 3 contract test:
scripts/test_e2007_test_ground_plane_general.py against
scripts/e2007_test_ground_plane_general_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_test_ground_plane_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
