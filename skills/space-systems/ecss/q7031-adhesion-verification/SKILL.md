---
name: q7031-adhesion-verification
description: "Determine whether an applied coat meets its adhesion requirement under ECSS-Q-ST-70-31C using the pressure-sensitive tape method of ECSS-Q-ST-70-13C: choose the cross-cut spacing from dry film thickness and substrate hardness, refuse a film too thick for the lattice, convert whole and partly detached squares into a detached-area percentage, band it into the six-step rating, then grade every test area, the number of areas and the spread between them, folding in a pull-off strength where one is reported. Use when a cross-cut or tape adhesion record has to be accepted or rejected. Trigger: ecss, q-st-70-13c-tape-test, coating-cross-cut-rating, paint-adhesion-lattice-spacing, coating-detached-area-percentage, paint-pull-off-strength, coating-adhesion-test-area-spread."
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
  tags: [ecss, q-st-70-31c-paint-quality-scope, q7031-adhesion-verification, coating-cross-cut-rating, paint-adhesion-lattice-spacing, coating-detached-area-percentage, paint-pull-off-strength, coating-adhesion-test-area-spread]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paint Application -- Adhesion Verification (space-systems/ecss/q7031-adhesion-verification)

Use when the task is the adhesion verification of ECSS-Q-ST-70-31C: a coat is
cured, a cross-cut and tape test has been run on it following
ECSS-Q-ST-70-13C, and the question is whether the recorded result accepts the
coating or sends it back.

## Domain quick reference

- The lattice spacing is not a free choice. It follows from the dry film
  thickness and from how hard the substrate underneath is: a thin film on a
  hard substrate takes the finest spacing, a thin film on a soft one and a
  mid-range film take the next, and a thick film takes the coarsest. Cutting
  a thin film at a coarse spacing under-reads the damage.
- Above a thickness limit the lattice method stops describing anything. The
  cut no longer reaches the substrate cleanly and the flakes that lift are
  cohesive failures inside the film, so a thick system is verified by a
  pull-off method instead, not by a lattice cut anyway.
- The rating is an area fraction, not a square count. A square partly lifted
  contributes its own fraction, and the denominator is the lattice size,
  which is the square of one less than the cut count. Twenty-five squares and
  a hundred squares do not produce interchangeable numbers.
- The band edges belong to the tighter side: a result sitting exactly on an
  edge takes the better rating. That is a representation question and is
  handled by a tolerance inside the comparison, never by rounding the
  measured percentage first.
- One test area is a sample, not a verification. A coat can pass on a flat
  and fail on a formed section, so the number of areas and the spread of
  their ratings carry requirements of their own; a wide spread is a process
  finding even when the worst area is inside the limit.
- The test is destructive. Every cut area becomes a repair, which is why the
  areas are planned onto witness coupons or onto surfaces whose repair is
  already authorised, rather than chosen wherever is convenient.

## Workflow

1. Validate each test area: a positive dry film thickness, a known substrate
   hardness, an integer detached-square count and any partial fractions
   strictly between nought and one.
2. Choose the cut spacing from thickness and substrate, refusing a film above
   the lattice limit rather than reporting a rating for it.
3. Derive the lattice size from the cut count and refuse a record whose
   affected squares outnumber the lattice.
4. Form the detached-area percentage from whole squares plus partial
   fractions over the lattice size, and band it into the six-step rating with
   the edges inclusive of the tighter side.
5. Grade every area against the worst rating allowed, the area count against
   its minimum, and the rating spread against its limit.
6. Where a pull-off strength is reported, test it against its minimum and
   fold the result into the same verdict.
7. Return the verdict with the per-area records, the worst rating, the spread
   and every finding named.

## Pitfalls

- Cutting at a convenient spacing rather than the one the thickness calls
  for. A coarse cut on a thin film lifts less, so the result is optimistic in
  exactly the direction that matters.
- Running a lattice on a film above the method's thickness limit. The result
  describes cohesion inside the coat, not adhesion to the substrate, and
  reporting it as an adhesion rating substitutes one property for another.
- Counting a partly lifted square as a whole one, or as nothing. Both
  distortions are avoidable: the fraction is what the area percentage is
  built from.
- Rounding the detached percentage before banding it. A value on an edge is
  meant to take the tighter rating, and rounding first moves it across.
- Verifying on one area. Adhesion varies with geometry, surface preparation
  and overspray history, so a single clean area is a sample that has not yet
  found the weak one.
- Reading a wide rating spread as an averaging problem. The spread is
  evidence that the process is not in control, and averaging it away removes
  the only signal that says so.

## Behavior contract (gate 3)

The spacing selection at every thickness band and both substrate hardnesses,
the lattice-limit refusal, the lattice size derivation, the whole-plus-partial
detached-area percentage, the six-step banding at its edges, the per-area
grading, the area-count and spread requirements and the pull-off fold-in are
exercised by the gate 3 contract test:
scripts/test_q7031_adhesion_verification.py against
scripts/q7031_adhesion_verification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7031_adhesion_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
