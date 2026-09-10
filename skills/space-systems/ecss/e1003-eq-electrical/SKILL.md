---
name: e1003-eq-electrical
description: "Use when scoping and running the ECSS-E-ST-10-03C equipment electrical/RF test set for one equipment item: verify test applicability (EMC, magnetic, ESD, passive intermodulation, multipactor, corona/arc discharge) from equipment risk flags, define each test's status (not applicable, missing, passed, failed), and roll up the campaign disposition (complete, incomplete, failed) before equipment qualification/acceptance sign-off. Anchor: E-ST-10-03C clause 5.5.5. Trigger: equipment electrical test, EMC test, magnetic test, ESD test, passive intermodulation, PIM test, multipactor test, corona test, arc discharge test, e-st-10-03, ecss."
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
  tags: [ecss, e-st-10-03c, equipment-test, emc, esd, pim, multipactor, corona-arc, verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment Electrical/RF Tests (space-systems/ecss/e1003-eq-electrical)

Use when the task is scoping and running the equipment-level
electrical and RF test set of ECSS-E-ST-10-03C for one piece of
equipment, ahead of mission-specific tests (sibling e1003-eq-mission
leaf) and equipment-level test baseline closure (sibling
e1003-eq-qual / e1003-eq-acceptance / e1003-eq-protoflight leaves).

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.5.5 groups six electrical/RF test types
  for equipment: electromagnetic compatibility (EMC), magnetic,
  electrostatic discharge (ESD), passive intermodulation (PIM),
  multipactor, and corona/arc discharge.
- Not every test in the set applies to every equipment item. Each
  test's applicability is driven by an equipment-level risk or
  requirement flag established during design and analysis, not by
  running the test itself: EMC applies to any equipment with
  electrical interfaces; magnetic applies only when the project has
  levied a magnetic-cleanliness requirement; ESD applies when an
  external dielectric surface is exposed to a charging environment;
  PIM and multipactor apply only to RF equipment already flagged with
  the corresponding risk (multi-carrier RF chain for PIM, high RF
  power in vacuum for multipactor); corona/arc-discharge applies when
  high voltage is present together with an assessed risk of operating
  in the pressure transition region.
- Equipment with no electrical interfaces at all is out of scope for
  the entire 5.5.5 set -- every test is not applicable, and this leaf
  should not be invoked for it.
- A test that is applicable but has no recorded result is "missing",
  distinct from "not applicable" (out of scope) and from "failed" (run
  and did not pass); a campaign cannot close while any applicable test
  is missing.

## Workflow

1. For each equipment item, capture its electrical/RF risk flags:
   has_electrical_interfaces, magnetic_cleanliness_required,
   esd_susceptible, pim_risk_present, multipactor_risk_present,
   corona_arc_risk_present.
2. Determine applicability of each of the six tests from those flags.
   Equipment without electrical interfaces is not applicable for the
   whole set; otherwise EMC is always applicable and the remaining
   five follow their individual flag.
3. For each applicable test, record its result (passed or failed) as
   it becomes available; leave it unset until then.
4. Disposition each test's status: not_applicable (out of scope),
   missing (applicable, no result yet), passed, or failed.
5. Roll up the equipment's overall electrical/RF test status: failed
   if any test failed, incomplete if none failed but at least one
   applicable test is still missing, complete only when every
   applicable test has passed.
6. Build the campaign disposition across every equipment item in
   scope and confirm no equipment id from the intended set is missing
   before closing out the electrical/RF test set for that item.

## Pitfalls

- Treating a test with no recorded result as "not applicable" instead
  of "missing" -- silently drops a required test from the campaign.
- Running the magnetic or ESD test on equipment that never had the
  corresponding requirement flagged, or skipping PIM/multipactor on
  RF equipment that was flagged with the risk but treated as generic
  hardware.
- Declaring the campaign complete when one applicable test failed but
  the others passed -- one failure fails the whole equipment item,
  it does not average out.
- Invoking the full 5.5.5 set on equipment that has no electrical
  interfaces at all, instead of recognizing the set is out of scope.

## Behavior contract (gate 3)

The applicability, per-test status, and campaign roll-up logic is
exercised by the gate 3 contract test:
scripts/test_e1003_eq_electrical.py against
scripts/e1003_eq_electrical_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_electrical.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
