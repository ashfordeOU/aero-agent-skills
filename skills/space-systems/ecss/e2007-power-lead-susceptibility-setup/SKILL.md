---
name: e2007-power-lead-susceptibility-setup
description: "Validate the bench arrangement a power-lead susceptibility injection is built on. Use when the task is ECSS-E-ST-20-07C clause 5.4.7.3 and a supply-lead injection has to be set up on the standard bench configuration: confirm every supply lead is terminated in its own stabilization network, hold the exposed run and its height above the ground plane to their allowances, place the series injection element inside the window measured from the unit connector, keep the current monitor clamped beside it, and check the bond to the plane and the separation from any signal lead. Refuses a supply pair carrying one lead, an unknown polarity and an offset declared on a lead nothing is injected into. Trigger: ecss, e-st-20-07c, power-lead-susceptibility-setup, supply-lead-injection-arrangement, lead-stabilization-network, injection-element-position, current-monitor-offset, ground-plane-bond-resistance, signal-lead-separation."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-power-lead-susceptibility-setup, supply-lead-injection-arrangement, lead-stabilization-network, injection-element-position, current-monitor-offset, ground-plane-bond-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Power-Lead Susceptibility Injection Setup (space-systems/ecss/e2007-power-lead-susceptibility-setup)

Use when the task is the injection arrangement of ECSS-E-ST-20-07C clause
5.4.7.3 -- the standard bench configuration with the series injection
element added to one supply lead, and the question of whether the bench
in front of you is the arrangement the susceptibility run is supposed to
be made on.

## Domain quick reference

- The arrangement is the standard configuration plus one addition. The
  unit sits bonded to a ground plane, each supply lead runs a fixed
  exposed length to its own stabilization network at a fixed height above
  that plane, and the injection element is inserted into ONE of those
  leads. Nothing about the base configuration is relaxed because an
  injection was added.
- Every supply lead is terminated in its own network, the return included.
  A shared network, or a return taken straight to the supply, leaves the
  impedance the disturbance sees undefined and the run unrepeatable.
- The injection element sits in a window measured from the unit
  connector, not simply "close to the unit". Too near and it loads the
  connector; too far and the disturbance is attenuated along the run
  before it reaches the pins that matter.
- One lead is injected at a time. Two elements in circuit at once makes
  the current at the unit the sum of two paths and no single measured
  value describes what was injected. The return lead is not the injected
  lead: it is the reference the injected current comes back on.
- The current monitor is clamped beside the element, not anywhere on the
  lead. A monitor far from the injection reads a current shaped by the
  length of lead between them rather than the current entering the unit.
- The exposed run and its height above the plane are geometry, and the
  geometry sets the coupling. Both carry an allowance, both are checked
  on every lead, and a lead lifted off its spacers is as much a setup
  error as a lead of the wrong length.
- The bond of the unit to the plane is a measured number, not an
  observation that a strap is fitted. An undeclared bond is an open item,
  not a pass.
- A bound met exactly is met. A difference of two distances can land a
  few units in the last place outside an exactly-met allowance; absorb
  that in the comparison, never by widening the allowance.

## Workflow

1. Normalize each lead: identifier, polarity, whether it is terminated in
   its own stabilization network, exposed run, height, and -- only when
   the lead is the injected one -- the injection and monitor offsets.
   Reject an unknown key, a missing key, an unknown polarity, a blank
   identifier, a non-boolean flag, and an offset declared on a lead that
   is not injected.
2. Reject an arrangement of fewer than two leads, a duplicated
   identifier, and a set of polarities that is not one high lead and one
   return lead.
3. Check each lead's exposed run against its nominal length and
   fractional allowance, and its height against the nominal height and
   its absolute allowance.
4. Report any lead not terminated in its own stabilization network.
5. For the injected lead, place the element in the window measured from
   the connector, separating too-near from too-far in the finding.
6. Check the current monitor against the element it is meant to sit
   beside, and the separation kept from any signal lead.
7. Check the arrangement as a whole: exactly one injected lead, the
   injected lead is not the return, a ground plane is declared, and the
   bond to it was measured and is below its limit.
8. Aggregate: report the conforming fraction of the leads and call the
   bench fit only when no finding remains.

## Pitfalls

- Terminating only the high lead in a stabilization network and running
  the return straight back to the supply, which leaves the impedance the
  injected disturbance works into undefined.
- Placing the injection element wherever the bench is convenient: the
  window is measured from the unit connector, and both ends of it exist
  for a reason.
- Leaving a second injection element in circuit from an earlier lead, so
  two paths carry disturbance and the monitored current describes
  neither of them.
- Injecting the return lead because the element fitted more easily there
  -- the return is the reference the injected current comes back on.
- Clamping the current monitor at a convenient point far from the
  element and reading that current as the current entering the unit.
- Recording the bond as "strap fitted" instead of a measured resistance,
  then discovering at the review that no number exists.
- Widening a length allowance to make a borderline lead conform, rather
  than absorbing the representation error of the difference.

## Behavior contract (gate 3)

The lead-run and height tolerance checks, the injection-window placement,
the current-monitor offset, the ground-plane bond, the signal-lead
separation, the lead and arrangement validation and the whole-bench
verdict are exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_susceptibility_setup.py against
scripts/e2007_power_lead_susceptibility_setup_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_e2007_power_lead_susceptibility_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
