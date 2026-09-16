---
name: e2008-coverglass-coating-adhesion-test
description: "Use when an adhesion result is about to be filed from a method nobody agreed to in advance. Verify that coverglass coating adhesion is shown against a test standard the customer has accepted, per ECSS-E-ST-20-08C clause 8.7.18: reduce the nomination to one standard on that accepted list and refuse anything off it, then read the run by the family the standard prescribes -- tape peel strength, dwell and removal angle behind a removed-area share; lattice spacing, detached squares and an adhesion grade; or a stud pull-off stress that counts only when the glue was not the weakest link. Trigger: ecss, e-st-20-08c-clause-8-7-18, coverglass-coating-adhesion-acceptance, customer-accepted-adhesion-standard, coating-tape-peel-removal-share, cross-cut-lattice-adhesion-grade, coating-pull-off-stud-stress, adhesion-failure-mode-conclusiveness."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-coating-adhesion-test, coverglass-coating-adhesion-acceptance, customer-accepted-adhesion-standard, coating-tape-peel-removal-share, cross-cut-lattice-adhesion-grade, coating-pull-off-stud-stress, adhesion-failure-mode-conclusiveness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Coating Adhesion Test (space-systems/ecss/e2008-coverglass-coating-adhesion-test)

Use when the task is clause 8.7.18 of ECSS-E-ST-20-08C -- the adhesion
of a coverglass coating shown against a test standard the customer has
accepted. The clause names no method, and that is the point. The
sentence puts the customer's acceptance in front of the arithmetic, so
a result from a method nobody agreed to in advance is not a weaker
result; it is not a result, and no amount of care in the laboratory
converts it into one afterwards.

## Domain quick reference

- The accepted list is the gate. It is supplied by the customer, it
  names the standard and the method that standard prescribes, and a
  nomination outside it stops the assessment before any number is read.
- One standard, not two. Two open standards produce two results with no
  rule for reconciling them, and the families do not convert into one
  another, so the ambiguity has to be closed at the nomination.
- Tape peel reads the share of the tested area the coating left with
  the tape. The tape is the instrument: its own peel strength, the
  dwell that lets the adhesive wet out, and the removal angle all have
  to be the specified ones before the removed area means anything.
- A cross-cut lattice reads the share of the enclosed squares that
  detached, banded into a grade. A lattice of n parallel cuts per axis
  encloses (n - 1) squared squares, and the spacing has to suit the
  coating thickness -- a sub-micron optical coating wants the finest
  spacing, and a coarse lattice puts the grade bands out of scope.
- A stud pull-off reads a stress, force over the bonded face. The
  failure mode decides whether that stress belongs to the coating: a
  break in the glue only says the coating held at least as well as the
  adhesive, which is a lower bound and not a measurement.
- Void and not accepted are different outcomes with different
  consequences. A wrong tape, a short dwell, a coarse lattice or a glue
  failure under the requirement all mean the run is repeated; a clean
  run over its limit means the coating is rejected.
- The customer's accepted grade is part of the acceptance, not a
  constant. A programme that accepts grade one and a programme that
  accepts grade four are reading the same lattice differently, and the
  grade alone does not carry the verdict.

## Workflow

1. Take the customer's accepted list and refuse it if it is empty or
   names a method family that cannot be read.
2. Reduce the nomination to exactly one standard on that list. Refuse a
   nomination that names none, names two, or names one the customer
   never accepted.
3. Pull the family the accepted standard prescribes and demand the
   evidence that family owes. Missing evidence stops the reading rather
   than defaulting to a nominal.
4. For a tape peel, check the tape band, the dwell and the removal
   angle first, then read the removed area as a share of the tested
   area against its ceiling.
5. For a lattice, check the spacing against the coating thickness
   first, then count the enclosed squares, take the detached share and
   band it into a grade against the grade the customer accepts.
6. For a stud pull, convert force and stud diameter into a stress, then
   let the failure mode decide whether a shortfall is a finding against
   the coating or a run that has to be repeated with better glue.
7. Close with a verdict that keeps void separate from not accepted.

## Pitfalls

- Reading the number before the standard. A tidy removed-area share
  from a method the customer never accepted is the most persuasive way
  to file a result the customer can reject outright later.
- Treating aggressive tape as conservative. Tape above the band strips
  coatings that were adherent enough for the application, and the
  rejection it produces is about the tape rather than the coating.
- Pulling the tape before the adhesive has wetted out. A short dwell
  flatters the coating, and it flatters it silently, because the
  removed area simply comes back small.
- Cutting a coarse lattice into a sub-micron coating. The grade bands
  were built for a spacing suited to the thickness, and a lattice at
  the wrong pitch produces a grade that looks comparable and is not.
- Recording a glue failure as a pass. It bounds the coating bond from
  below; below a requirement that bound settles nothing, and filing it
  as a pass loses the one article that might have been weak.
- Carrying the grade without the accepted grade. Grade two is a pass on
  one programme and a rejection on the next, so the verdict needs both
  numbers or it does not travel.
- Comparing a derived stress or share against its limit by bare
  arithmetic. Each is a ratio rescaled across units, so the comparison
  absorbs a few units in the last place while the limit itself is never
  relaxed.

## Behavior contract (gate 3)

The customer accepted-list gate, single-standard nomination, per-family
evidence requirement, tape band, dwell and removal angle, removed-area
share, lattice square count, detached share, adhesion grade bands, cut
spacing by coating thickness, pull-off stress, failure-mode
conclusiveness and the void-versus-not-accepted split are exercised by
the gate 3 contract test:
scripts/test_e2008_coverglass_coating_adhesion_test.py against
scripts/e2008_coverglass_coating_adhesion_test_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_coating_adhesion_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
