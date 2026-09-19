---
name: e3311-shaped-charges
description: "Evaluate a shaped charge as installed against ECSS-E-ST-33-11C clause 4.11.7. Use when the task is proving a conical or linear charge will cut what it is aimed at and nothing else: derating nominal penetration by the standoff it is actually mounted at and by the cosine of its misalignment, grading the resulting capability against the thickness to be cut, holding standoff deviation and alignment to their own tolerances, and closing the safety side with a keep-out radius scaled to charge diameter, the residual jet past the cut against the structure behind it, and spacing between neighbouring charges. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, shaped-charge-penetration-margin, linear-shaped-charge-cut-depth, shaped-charge-standoff-tolerance, shaped-charge-jet-misalignment, shaped-charge-keep-out-radius, sympathetic-detonation-spacing."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-shaped-charges, shaped-charge-penetration-margin, linear-shaped-charge-cut-depth, shaped-charge-standoff-tolerance, shaped-charge-jet-misalignment, shaped-charge-keep-out-radius, sympathetic-detonation-spacing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Shaped Charges (space-systems/ecss/e3311-shaped-charges)

Use when the task is the shaped-charge screen of ECSS-E-ST-33-11C
clause 4.11.7 -- a conical or linear charge that forms a jet and
drives it through a target, where the installation geometry owns as
much of the performance as the charge does.

## Domain quick reference

- A shaped charge is the one energetic device on a vehicle whose
  qualified performance is not what it delivers. The liner forms a
  jet, and how far that jet has run before it meets metal, and at
  what angle, change the depth it reaches.
- Standoff is not a clearance, it is a tuning parameter with an
  optimum. Both too close and too far cost penetration, so the
  quantity graded is the deviation from the optimum rather than the
  distance itself.
- Misalignment costs penetration as a cosine and costs aim linearly.
  A few degrees is a small derate and a large miss at the far end of
  a long linear charge, so the angle is graded as its own tolerance,
  not only as an efficiency.
- The capability is the nominal depth times both efficiencies, and it
  is that number, not the catalogue number, that gets compared with
  the thickness to be cut.
- The jet does not stop at the cut. Whatever capability remains past
  the target keeps going, so the structure behind the cut line is a
  requirement in its own right and the residual is computed, not
  assumed to be small.
- The keep-out radius scales with the charge diameter because the
  debris and blast field do. Quoting a fixed clearance in millimetres
  across a set of charges of different sizes grades the small ones
  harshly and the large ones not at all.
- Neighbouring charges are graded as a pair, against the larger of
  the two diameters, because sympathetic initiation is driven by the
  bigger donor rather than by an average.

## Workflow

1. Normalize the charge set, rejecting a duplicate identifier, an
   unknown charge kind and a misalignment at or past ninety degrees,
   because a jet turned that far reaches nothing.
2. Compute the standoff deviation from the optimum, turn it into a
   standoff efficiency at the charge's declared sensitivity, and
   floor that efficiency at zero rather than letting it go negative.
3. Take the cosine of the misalignment as the alignment efficiency
   and multiply the nominal penetration by both efficiencies to get
   the capability as installed.
4. Grade the capability against the target thickness with margin, and
   grade the standoff deviation and the misalignment against their
   own tolerances as separate findings.
5. Grade the safety side: clearance to sensitive hardware against a
   keep-out radius scaled to the charge diameter, and the clearance
   behind the target against the residual jet with margin.
6. Walk the declared neighbour pairs, grade each spacing against the
   larger diameter, and close with the accepted and rejected charges,
   the failed pairs and the verdict.

## Pitfalls

- Grading the catalogue penetration against the target. That figure
  was measured at the optimum standoff, square on, and no installed
  charge is both.
- Treating standoff as a minimum clearance. It has an optimum, and a
  charge mounted closer than optimum performs worse, which is the
  opposite of what a clearance intuition predicts.
- Reading a small misalignment as negligible because the cosine is
  near one. The derate is small and the aim error at the end of a
  long linear charge is not, and the tolerance exists for the second
  reason.
- Forgetting the residual jet. A charge sized with generous margin
  has more capability left over past the cut, so improving the
  performance margin actively worsens the backup-clearance case.
- Applying one keep-out distance across a mixed set of charges. The
  radius belongs to the diameter, and a fixed number silently
  under-protects the largest charge in the set.
- Comparing a margin with its requirement by bare arithmetic. The
  capability is a product of a nominal and two efficiencies, one of
  them a cosine, so a charge landing exactly on its requirement can
  sit a few units in the last place below it; the comparison absorbs
  that while the requirement stays untouched.

## Behavior contract (gate 3)

The charge normalization, the standoff-deviation and cosine
efficiencies, the installed capability and residual jet, the
performance, standoff, alignment, keep-out and backup-clearance
gates, the pairwise sympathetic-spacing walk and the array verdict
are exercised by the gate 3 contract test:
scripts/test_e3311_shaped_charges.py against
scripts/e3311_shaped_charges_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3311_shaped_charges.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
