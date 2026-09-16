---
name: e2008-crimping-visual-inspection
description: "Use when crimped terminations have been examined and each one needs a disposition. Evaluate crimped wire terminations against the crimping workmanship standard the customer has accepted, under ECSS-E-ST-20-08C clause 5.5.3.2.15: refuse a standard with no recorded acceptance and a gauge it does not tabulate, compare each measured crimp height with the band for its own gauge, count the strands that reached the barrel against those nicked inside it or brushed outside it, read bell mouth, insulation support, trapped insulation and the inspection window, check pull-out against the gauge minimum, and roll the harness up with its pull-test sample coverage. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-15, crimped-wire-termination-inspection, crimping-workmanship-standard-acceptance, crimp-height-gauge-band, crimp-strand-loss-count, crimp-pull-out-check."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-crimping-visual-inspection, crimped-wire-termination-inspection, crimping-workmanship-standard-acceptance, crimp-height-gauge-band, crimp-strand-loss-count, crimp-pull-out-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Crimping Visual Inspection (space-systems/ecss/e2008-crimping-visual-inspection)

Use when the task is the crimp inspection of ECSS-E-ST-20-08C clause
5.5.3.2.15 -- crimped wire terminations graded against a crimping
workmanship standard that the customer has accepted, rather than against
a general view of what a good crimp looks like.

## Domain quick reference

- The acceptance is part of the authority. A workmanship standard the
  customer has not accepted may be entirely sound and still cannot
  carry a disposition under this clause, so a standard with no recorded
  acceptance is refused before any termination is read.
- Every number in the grading is per gauge. The crimp height band, the
  strand count the conductor carries and the pull-out force the joint
  has to hold all change with the wire, so a termination is only ever
  compared with its own gauge entry.
- A gauge the standard does not tabulate has no band. The band for a
  gauge sitting between two tabulated ones is not the average of
  theirs, and interpolating one grades the joint against a number
  nobody accepted.
- Crimp height is the compression measurement, and it fails in two
  opposite directions. Under the band the barrel has been driven into
  the strands and cut them; over it the barrel never closed and the
  joint is mechanical rather than a cold weld.
- A strand that never reached the barrel and a strand nicked inside it
  are different losses. The first is current capacity that was never
  connected; the second is a section that will work-harden and part
  later. A brushed strand is both, plus an isolation question.
- The features carry the strain relief. The bell mouth stops the
  strands turning on a sheared edge and the insulation support takes
  the bending load off the conductor, so their absence is a finding
  even when every dimension passes.
- A crimp is not adjustable. Rework here means cutting the termination
  back and making a new one, which is why the height window that
  distinguishes rework from rejection is about the contact and the
  wire length left, not about the crimp itself.
- Pull-out is sampled, not universal. The harness reports how much of
  the declared population was pull tested, because a sample nobody
  counted is a sample nobody took.

## Workflow

1. Validate the workmanship standard: identifier, revision, recorded
   customer acceptance and acceptor, and a gauge table whose bands have
   a floor below their top and a positive pull-out minimum and strand
   count.
2. Check the revision the inspection cites against the accepted
   standard in hand before any termination is read.
3. For each termination, take its gauge entry, refusing an untabulated
   gauge and a strand count that disagrees with the one the gauge
   carries.
4. Derive the compression and conductor figures: the crimp height
   against the band and its position inside it, the strands in the
   barrel, the strands lost, nicked and brushed, and the pull-out force
   where one was measured.
5. Grade the termination: height outside the band into the rework
   window or past it, strand loss and nicked fractions against their
   allowances, brushed strands against their count, insulation support,
   trapped insulation, bell mouth, inspection window and pull-out.
6. Roll the harness up: how many terminations carry a finding, how much
   of the harness allowance is left, how many were pull tested against
   the sample fraction, and how many declared terminations still have
   no record.
7. Report the worst disposition, the terminations not accepted, the
   remaining allowance and the completeness flag.

## Pitfalls

- Applying a workmanship standard nobody recorded the customer
  accepting. The dispositions that come out of it are defensible
  engineering and not evidence of compliance with this clause.
- Carrying one crimp height band across a mixed-gauge harness. The
  band that passes the heavier wire crushes the lighter one.
- Interpolating a band for a gauge the standard skips. Two tabulated
  neighbours do not imply the entry between them.
- Reading the crimp height as a single-sided limit. Too small and too
  large are different failures of the same measurement, and a check
  written one way round passes every barrel that never closed.
- Counting only the strands in the barrel. The strands brushed outside
  it are lost current paths that are also loose conductors inside the
  assembly.
- Passing a termination on its dimensions with no bell mouth or no
  insulation support. Nothing in the numbers sees the load path that
  those two features carry.
- Reporting a pull-test result without reporting how many terminations
  were pull tested. A sample of one on a harness of forty reads exactly
  like a sample of four unless the count is on the page.
- Comparing a measured crimp height with a band edge, or a counted
  number of strands with a derived allowance, by bare arithmetic. The
  allowance is a product of a declared fraction and a counted
  population and the height sits against a tabulated edge, so either
  can evaluate a few units in the last place past its limit; the
  comparison absorbs that representation error while the limit stays
  untouched.

## Behavior contract (gate 3)

The standard validation including customer acceptance, the per-gauge
band lookup and its refusal of an untabulated gauge, the crimp height
and band-position derivation, the strand loss, nicked and brushed
counts, the feature and pull-out checks, the per-termination
dispositions and the harness allowance with its pull-test sample
coverage and completeness rollup are exercised by the gate 3 contract
test: scripts/test_e2008_crimping_visual_inspection.py against
scripts/e2008_crimping_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_crimping_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
