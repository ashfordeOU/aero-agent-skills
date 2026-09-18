---
name: e2020-representative-interface-for-load-testing
description: "Evaluate whether the bench source feeding a load tested on its own really represents the limiter the unit will fly behind. Use when a standalone load test is set up against ECSS-E-ST-20-20C clause 5.3.4.1.1: compare the bench limit value, trip-off delay, series impedance and inductance and undervoltage threshold with the flight branch, match the latching and retrigger character exactly, recognise a hard laboratory supply that can never enter limitation, and state whether the resulting evidence transfers to the integrated system. Trigger: ecss, e-st-20-20c-clause-5-3-4-1-1, standalone-load-test-source, representative-limiter-interface, lcl-current-limit-match, trip-off-delay-match, bench-source-series-impedance, hard-laboratory-supply, load-test-evidence-transfer."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-representative-interface-for-load-testing, standalone-load-test-source, representative-limiter-interface, lcl-current-limit-match, trip-off-delay-match, bench-source-series-impedance, hard-laboratory-supply, load-test-evidence-transfer]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Representative Interface for Standalone Load Testing (space-systems/ecss/e2020-representative-interface-for-load-testing)

Use when the task is clause 5.3.4.1.1 of ECSS-E-ST-20-20C -- a user
equipment is being tested on its own, long before it meets the power
subsystem, and the question is what it should be fed from. The clause
recommends the standalone test present a source interface that
represents the limiter the unit will actually sit behind, rather than
whatever supply the test rack happens to carry.

## Domain quick reference

- A protected branch and a laboratory supply are different sources in
  the only way that matters. Behind a latching current limiter an
  inrush above the limit never draws its natural peak: the branch is
  held at the limit value, the output falls towards whatever the load
  is pulling, and the whole event runs against a deadline, the trip-off
  delay. A stiff bench supply delivers the peak, recovers instantly and
  never sets that deadline.
- The consequence is the defect the clause exists to prevent. A unit
  that charges its input capacitance comfortably from the rack supply
  can fail to finish the same charge inside the trip-off delay once a
  limiter is in the path, so the branch latches off and the unit never
  starts. Nothing in the standalone record predicts it.
- Five numeric parameters carry the representation: the limit value,
  the trip-off delay, the series impedance, the series inductance and
  the undervoltage threshold. Each gets its own tolerance. The limit
  and the threshold are held tightest because the load behaviour hinges
  directly on them; the two parasitic series terms are allowed to be
  looser, because a bench harness is never the flight harness.
- Two further properties are discrete and carry no tolerance at all:
  whether the source latches off after the delay, and whether it
  inhibits a retrigger. A bench source that recovers by itself turns a
  latching failure into a nuisance the operator never sees.
- The hard laboratory supply is its own finding, not a large deviation.
  A bench limit set far above the flight limit, or a source with no
  trip at all, cannot reproduce a limitation event at any tolerance,
  and reporting it as a percentage understates it.
- Whether the interface matters for a given unit depends on the unit.
  A load whose inrush stays under the flight limit never provokes
  limitation; a load whose inrush reaches it makes the limitation event
  the very thing the bench has to reproduce.

## Workflow

1. Validate both source descriptions as complete and self-consistent:
   every parameter present, the two series terms allowed to be zero for
   an ideal source, the undervoltage threshold below the nominal.
2. Take the tolerance set, project values overriding the defaults
   parameter by parameter rather than wholesale.
3. For each numeric parameter, form the bench deviation relative to the
   flight value and compare it with its tolerance, absorbing
   representation error so a value sitting exactly on the tolerance
   reads as inside it.
4. Compare the latching and retrigger flags as equality; a mismatch is
   a finding with no numeric excuse.
5. Screen separately for the hard source: a bench limit above the
   flight limit by the hard factor, or a source that never trips.
6. Decide whether the load provokes limitation at all, by comparing its
   inrush with the flight limit.
7. Add the load-side findings -- a steady demand above the limit means
   the branch has no stable state to test in -- and close with whether
   the standalone evidence transfers, naming every reason it does not.

## Pitfalls

- Reading "same voltage, enough current" as representative. The bus
  voltage is the parameter the bench most reliably gets right and the
  one that matters least; the limit value and the trip-off delay are
  what decide whether the unit starts.
- Setting the bench limit generously so the test never trips. That
  removes exactly the behaviour the standalone test was meant to
  exercise, and the run passes because nothing was asked of it.
- Treating a non-latching bench supply as a close-enough limiter. A
  source that recovers on its own converts a latch-off into a restart
  cycle, which reads as a working unit on the bench and as a dead
  branch in the system.
- Ignoring the series inductance because it is small. It sets the rate
  the limited current can move at during the collapse, so an ideal
  bench source can hide a stability problem the flight harness creates.
- Reporting a bench limit an order of magnitude above flight as a
  percentage deviation. A hard source is a different kind of finding
  and a tolerance cannot be widened far enough to make it acceptable.
- Comparing a deviation against its tolerance by bare arithmetic. Both
  are ratios of floats, so a bench value placed deliberately on the
  tolerance can land a few units in the last place outside it; the
  comparison absorbs that while the tolerance itself stays as declared.

## Behavior contract (gate 3)

The interface validation, tolerance resolution, relative deviation,
per-parameter and per-flag comparison, hard-source screening, required
envelope, limitation-expected decision and the standalone-test verdict
are exercised by the gate 3 contract test:
scripts/test_e2020_representative_interface_for_load_testing.py against
scripts/e2020_representative_interface_for_load_testing_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_representative_interface_for_load_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
