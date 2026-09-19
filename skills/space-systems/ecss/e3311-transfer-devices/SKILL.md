---
name: e3311-transfer-devices
description: "Evaluate an explosive transfer train against ECSS-E-ST-33-11C clause 4.11.4. Use when the task is proving that an initiation gets from where it was made to everywhere it is needed: grading each donor-to-acceptor crossing as the reliable transfer gap against the gap the design presents, holding a through-bulkhead crossing to its containment margin and a retained seal, grading each line segment on core load against the propagating minimum and installed bend radius, computing arrival time down every branch from length over propagation velocity plus crossing delays, and reading the spread and the qualified temperature range. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-transfer-train, through-bulkhead-initiator-containment, detonation-transfer-line-core-load, explosive-transfer-gap-margin, transfer-branch-simultaneity, transfer-line-bend-radius."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-transfer-devices, explosive-transfer-train, through-bulkhead-initiator-containment, detonation-transfer-line-core-load, explosive-transfer-gap-margin, transfer-branch-simultaneity, transfer-line-bend-radius]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Transfer Devices (space-systems/ecss/e3311-transfer-devices)

Use when the task is the transfer screen of ECSS-E-ST-33-11C clause
4.11.4 -- through-bulkhead initiators, detonation transfer lines and
ignition transfer lines, the parts of an explosive subsystem that do
no work themselves and exist only to carry an initiation somewhere
else.

## Domain quick reference

- Nothing in a transfer train produces an effect. That makes the
  subject narrow and unforgiving: the initiation either arrives,
  arrives everywhere close enough to simultaneously, and arrives
  without opening a wall on the way, or the train has failed.
- A crossing is graded as a ratio of gaps, not as an energy. The
  useful number is the largest gap across which transfer is still
  reliable, divided by the gap the assembly tolerance stack actually
  presents, because that is the quantity a gap test produces and the
  quantity a shim changes.
- A through-bulkhead device is two requirements wearing one name. It
  must transfer, and it must leave the bulkhead intact -- so the
  containment margin and the post-firing seal are graded separately
  from the transfer margin, and either one can fail alone.
- Core load is graded against the minimum that will propagate, not
  against a nominal. A line one notch under its propagating minimum
  does not run weakly; it stops, usually somewhere nobody instrumented.
- Bend radius is an installation property, not a procurement one. The
  qualified line is fine and the routed line is not, and the check has
  to read what the harness drawing did rather than what the data sheet
  allows.
- Simultaneity is computed, never declared: segment length over
  propagation velocity, summed along a branch, plus each crossing's
  own delay. The spread between the earliest and latest branch is the
  quantity a separation joint actually feels.
- The qualified temperature range is graded against the predicted one
  with margin on both ends, because a transfer line that is cold-brittle
  fails at one end of the mission and nowhere else.

## Workflow

1. Normalize the train and resolve every reference: reject duplicate
   segment, interface or branch identifiers, a branch routed through a
   segment nobody declared, and an interface that appears on no
   branch, because an unrouted crossing is one nobody timed.
2. Grade each crossing on transfer margin -- reliable gap over design
   gap -- and, where it goes through a bulkhead, on its containment
   margin and its retained seal as separate findings.
3. Grade each segment on core load against the propagating minimum and
   on installed bend radius against the line's own minimum.
4. Compute arrival time for every branch from segment transit times
   plus crossing delays, take the spread between earliest and latest,
   and grade it against the simultaneity allowance.
5. Grade the qualified temperature range against the predicted range
   with margin applied at both the cold and the hot end.
6. Close with the failed segments, the failed crossings, the
   simultaneity and temperature outcomes and the overall verdict.

## Pitfalls

- Grading a crossing against a nominal gap. The design gap is the
  worst case of a tolerance stack, and the nominal is the one number
  in the drawing that no built unit has.
- Treating a through-bulkhead initiator as a transfer question only.
  It is also a pressure vessel penetration, and a device that
  transfers perfectly while venting the compartment has failed the
  requirement that justified choosing it.
- Reading a comfortable core load as a propagation guarantee without
  the bend radius. A line that is over-loaded and over-bent still
  fails at the bend, and the two findings have to be reported apart.
- Declaring simultaneity from equal line lengths. Crossing delays and
  differing propagation velocities move the arrival, and a joint that
  unzips from one end tears rather than separates.
- Leaving an interface off every branch and assuming it was timed.
  A crossing on no branch contributes no delay to any arrival, so the
  spread silently improves.
- Comparing a margin with its requirement by bare arithmetic. An
  arrival spread or a gap ratio landing exactly on its limit can sit a
  few units in the last place the wrong side of it; the comparison
  absorbs that while the limit stays untouched.

## Behavior contract (gate 3)

The train normalization and branch resolution, the transfer-gap and
bulkhead containment gates, the core-load and bend-radius segment
gates, the branch arrival and simultaneity spread computation, the
temperature gate and the overall verdict are exercised by the gate 3
contract test: scripts/test_e3311_transfer_devices.py against
scripts/e3311_transfer_devices_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e3311_transfer_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
