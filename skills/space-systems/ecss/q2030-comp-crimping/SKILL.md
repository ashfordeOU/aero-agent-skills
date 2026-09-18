---
name: q2030-comp-crimping
description: "Verify a crimp-termination lot against the complementary crimping requirements of ECSS-Q-ST-20-30C clause 7.4, which take precedence over the delegated workmanship criteria wherever both speak. Use when the task is resolving which limit governs a crimp characteristic, grading a measured crimp height against the window the contact and wire gauge carry, sizing the tensile sample a lot owes and grading every pull against the minimum force its gauge carries, refusing a barrel holding an unqualified second wire or any solder, and confirming the crimping tool's calibration is still current. Trigger: ecss, q-st-20-30c, complementary-crimping-requirements, crimp-height-window, crimp-pull-test-sampling, crimp-barrel-wire-count, complementary-over-delegated-precedence, crimp-tool-calibration-currency, solder-in-crimp-barrel."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-comp-crimping, complementary-crimping-requirements, crimp-height-window, crimp-pull-test-sampling, complementary-over-delegated-precedence, crimp-barrel-wire-count]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Crimping Requirements (space-systems/ecss/q2030-comp-crimping)

Use when the task is the complementary crimping layer of ECSS-Q-ST-20-30C
clause 7.4 -- the small set of space-specific crimp requirements that sits
on top of the commercial workmanship chapter the standard delegates the
bulk of crimp acceptance to, and that wins wherever the two overlap.

## Domain quick reference

- The standard does not restate crimp workmanship; it adopts an external
  workmanship document chapter by chapter and then adds a complementary
  clause. Reading only the complementary clause misses most of the crimp
  criteria; reading only the adopted chapter misses the deltas that make
  the termination a space termination.
- Precedence runs by SOURCE, not by tightness. Where the complementary
  clause and the adopted chapter both speak to a characteristic, the
  complementary value governs even when it is the looser of the two. That
  is a deliberate engineering decision, so the correct behaviour is to
  apply it and report the relaxation, not to quietly substitute the
  tighter number and call the result compliant.
- Crimp height is the process witness, not a cosmetic dimension. It is
  the one measurement that ties a finished crimp back to the qualified
  tool-and-die setting, so it is graded against a window keyed to the
  contact part number and the wire gauge together -- the same contact on
  a different gauge is a different window.
- The tensile check is destructive and therefore sampled. A sample is
  sized from the lot, never fixed at a habitual three, and every pull in
  it has to reach the minimum its gauge carries. A sample mean is not the
  criterion: one low pull is a failed sample however high the others ran.
- Two constructions the complementary layer rules out outright are a
  second wire pushed into a barrel qualified for one, and solder anywhere
  in a crimp. Both produce a joint that passes a pull test on the day and
  fails later, the first by unequal strand compression and the second by
  a wicked, stiff transition that cracks under vibration.
- A crimp is only as traceable as the tool that made it. A lot crimped
  with a tool whose calibration has lapsed has no valid process record,
  and that is a lot finding rather than a per-crimp one.

## Workflow

1. Validate the lot: each crimp record carries an identifier, a gauge, a
   measured height and the nominal-plus-tolerance window it is graded
   against. Reject a duplicate identifier rather than folding two records
   into one.
2. For every characteristic that both sources speak to, resolve the
   governing limit by precedence and record whether the complementary
   value relaxed the delegated one.
3. Grade each measured crimp height against its window, absorbing
   representation error at the window edge with a named tolerance instead
   of widening the window.
4. Examine each record for the ruled-out constructions: an unqualified
   multiple-wire barrel, solder in the crimp, an insulation support the
   contact provides but the crimp left unengaged.
5. Size the tensile sample from the lot size, the sampling fraction and
   the sample floor, and take the governing minimum force as the toughest
   gauge present in the lot.
6. Grade every pull against that minimum, absorbing an exact equality
   with a tolerance, and treat a short sample as a finding in its own
   right rather than as a pass on the pulls that were run.
7. Confirm the tool calibration interval, then roll every per-crimp and
   lot-level finding into one verdict with the findings named.

## Pitfalls

- Substituting the tighter of the two sources. Precedence is by source;
  silently applying the delegated number where the complementary clause
  has spoken hides a relaxation the project accepted on purpose.
- Grading a crimp height against the contact alone. The window depends on
  the contact and the gauge together, so a gauge change inside the same
  connector is a new window and usually a new die setting.
- Reporting a tensile sample by its mean or its median. Every pull owes
  the minimum; a mean hides the one strand-damaged crimp the sample was
  taken to find.
- Running a habitual three pulls whatever the lot size. The sample is
  sized from the lot; a fixed count is a coverage finding on a large lot
  and wasteful destruction on a small one.
- Accepting a double crimp because the pull test passed. The pull test
  measures the barrel, not the two wires inside it; unequal compression
  shows up as an intermittent months later, so the qualification of the
  multiple-wire process is what licenses it, not the force reading.
- Treating a lapsed tool calibration as paperwork. Without a valid tool
  record the height measurements have nothing to tie back to, so the
  whole lot loses its process evidence, not just its signature.
- Failing a crimp whose height lands exactly on a window edge. The
  equality is a representation question, settled with a tolerance inside
  the comparison and never by moving the window.

## Behavior contract (gate 3)

The source normalization, the precedence resolution and relaxation flag,
the crimp-height window and edge grading, the gauge-keyed tensile
minimum, the sample sizing, the per-pull grading, the ruled-out
construction screens, the tool-calibration currency check and the whole
lot verdict are exercised by the gate 3 contract test:
scripts/test_q2030_comp_crimping.py against
scripts/q2030_comp_crimping_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_crimping.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
