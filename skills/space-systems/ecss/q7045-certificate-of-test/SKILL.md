---
name: q7045-certificate-of-test
description: "Produce the certificate of test a released metallic material lot owes, and the verdict on whether it may be signed at all. Use when mechanical results have come back and someone must certify the release: group the specimens by the heat they were cut from so one certificate never averages two, size the sampling each heat owes from the product form and the released mass, count only specimens whose test was not voided, judge every counted specimen against the specification minimum rather than the heat mean, and build a deterministic reference per heat. Trigger: ecss, q-st-70-45-metallic-mechanical-testing, certificate-of-test-issue, per-heat-certificate-scope, material-lot-sampling-size, voided-specimen-exclusion, governing-minimum-property."
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
  tags: [ecss, q-st-70-45-metallic-mechanical-testing, q7045-certificate-of-test, certificate-of-test-issue, per-heat-certificate-scope, material-lot-sampling-size, voided-specimen-exclusion, governing-minimum-property]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Certificate of Test (space-systems/ecss/q7045-certificate-of-test)

Use when the task is the certificate side of the reporting clause of
ECSS-Q-ST-70-45: deciding whether a certificate of test can be issued
for a released lot, what heat it may cover, and what it is allowed to
state.

## Domain quick reference

- A certificate covers exactly one heat. The mechanical results of one
  heat say nothing about the parts of another, so a release spanning two
  heats owes two certificates. Averaging across them produces a number
  that describes neither heat and hides the weaker one.
- The sampling a heat owes comes from the product form and the mass
  released, not from what the laboratory happened to cut. Forms whose
  properties vary with position or direction — plate, extrusion, forging
  and casting — owe more than bar, and a large release owes one more
  specimen per started mass increment up to a cap, because past that
  point further specimens buy no more evidence than the scatter already
  shows.
- A voided specimen is a test that was run, not a test that counts. An
  out-of-gauge fracture or a machine fault removes the piece from the
  count, and the heat is then short of its sampling even though the
  laboratory ran the full programme.
- Every counted specimen is judged against the specification minimum.
  The mean is reported because a reader wants to see how close the heat
  ran, never because it is the quantity being accepted: a heat with one
  low piece and one high piece has a comfortable mean and an
  uncertifiable low piece.
- A property landing exactly on the minimum passes. That is a
  representation question, absorbed by a named tolerance inside the
  comparison, not a reason to move the specification.
- The reference is deterministic: the same laboratory, heat and issue
  date always produce the same certificate identifier, so a reissued
  certificate is recognisably the same document rather than a new one.

## Workflow

1. Group the specimens by heat, case-folding the identifiers, and refuse
   a set where one specimen identifier appears twice.
2. Size the owed sampling per heat from the product form and the
   released mass, applying the form uplift and the mass increment, and
   stop at the cap.
3. Remove the voided specimens and count what remains; a heat with
   nothing valid left is certified as nothing at all, with no reference.
4. Compute the governing minimum, the maximum and the mean of the valid
   values, and name the specimen that governs.
5. Report every counted specimen below the specification minimum
   individually, so the chase is against pieces rather than against a
   statistic.
6. Build the certificate reference per heat and return one verdict per
   heat, plus a release-level finding when more than one certificate is
   owed.

## Pitfalls

- Issuing one certificate for a delivery that carries two heats. Both
  heats may have passed; the certificate still cannot say which parts in
  the box came from which, and afterwards nobody can tell them apart.
- Counting voided specimens towards the sampling. The programme looks
  complete on the laboratory's run sheet and is short on the evidence
  the certificate rests on.
- Certifying on the mean. The mean is the one number that can pass while
  a piece of the released material fails, and the released material is
  what the certificate travels with.
- Sizing the sampling from what was tested. The owed number comes from
  the form and the mass; deriving it from the specimens received makes
  every release self-certifying.
- Widening the specification minimum to clear an exact-equality case.
  The equality is absorbed by the tolerance inside the comparison; the
  specified value stays as specified.
- Generating a fresh certificate identifier on reissue. A second
  identifier for the same heat and date turns one document into two in
  every downstream record.

## Behavior contract (gate 3)

The per-heat grouping, the form-and-mass sampling size with its cap, the
voided-specimen exclusion, the governing minimum against the
specification, the exact-boundary tolerance, the deterministic
certificate reference and the multi-heat release finding are exercised
by the gate 3 contract test:
scripts/test_q7045_certificate_of_test.py against
scripts/q7045_certificate_of_test_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_certificate_of_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
