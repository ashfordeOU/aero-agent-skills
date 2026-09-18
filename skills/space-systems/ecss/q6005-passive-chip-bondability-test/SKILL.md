---
name: q6005-passive-chip-bondability-test
description: "Determine whether a lot of bare passive chips is bondable from the destructive wire pull sample ECSS-Q-ST-60-05C clause 8.2.2 calls for before the lot is used: read the minimum pull force for the wire material and diameter actually used from an interpolated table, size the sample as a floor on bonds pulled and on the chips they spread over, categorize where each bond separated, fail a lift at the termination or a termination off the chip body whatever force was read, and reduce the forces to a mean, a sample deviation and a minimum. Use when chip termination bondability evidence is graded. Trigger: ecss, q-st-60-05c, passive-chip-termination-bondability, chip-termination-bond-pull-strength, bond-lift-at-termination-mode, passive-chip-bondability-sample-plan, wire-diameter-minimum-pull-force."
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
  tags: [ecss, q-st-60-05-hybrid-procurement-scope, q6005-passive-chip-bondability-test, passive-chip-termination-bondability, chip-termination-bond-pull-strength, bond-lift-at-termination-mode, passive-chip-bondability-sample-plan, wire-diameter-minimum-pull-force]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Passive Chip Bondability (space-systems/ecss/q6005-passive-chip-bondability-test)

Use when the task is the bondability verification of ECSS-Q-ST-60-05C
clause 8.2.2 — proving on a destructive sample, before the lot is committed
to hardware, that wires attached to the terminations of a bare passive chip
reach the strength the assembly needs and separate in the wire rather than
at the termination.

## Domain quick reference

- Bondability is a property of the termination as delivered, not of the
  bonder. That is why the sample is pulled from the incoming lot on a
  settled process: the question being asked is whether this lot's
  terminations accept a wire, and a changing process makes the answer
  unreadable.
- The minimum pull force follows the wire, not the chip. It rises with wire
  diameter and differs between gold and aluminium at the same diameter, so
  the figure has to be read for the wire actually used on the sample. A
  diameter outside the tabulated span is not a small extrapolation; the
  table is obtained for it or the sample is not graded.
- Where the bond separated matters as much as the force. A break in the
  wire span, at the heel or in the neck says the wire yielded before the
  joint did — the joint outlived the wire, which is the result wanted. A
  lift at the termination, or the termination itself coming away from the
  chip body, says the interface failed.
- An interface failure is not redeemed by a high reading. A bond that lifts
  at ten gram-force on a three gram-force minimum still lifted at the
  termination, and the number only says that this particular termination
  happened to be among the better ones. Force and separation mode are two
  independent verdicts on the same pull.
- The sample has two floors, not one. A floor on the bonds pulled gives the
  statistics something to stand on, and a floor on the distinct chips they
  came from stops a single well-metallized chip carrying the lot — chip to
  chip variation within a lot is exactly what is being sampled for.
- The spread is part of the evidence. A mean comfortably above the minimum
  with a wide spread and a low minimum reading is a lot that is going to
  produce field failures, so the minimum and the sample deviation are
  reported alongside the mean rather than summarized away.

## Workflow

1. Resolve the bonding wire material and read the minimum pull force for
   its diameter by interpolating the per-material table; refuse a diameter
   the table does not span rather than extrapolating past its ends.
2. Size the sample from the lot: the bond count floor and the distinct chip
   count floor, with the chip floor capped at the lot for a very small lot.
3. Categorize the separation of each pulled bond into one of the recognised
   modes and mark the ones that happened at an interface.
4. Judge each reading on both counts — force at or above the minimum, and a
   separation that is not an interface failure — absorbing representation
   error at the minimum with a named tolerance rather than by lowering it.
5. Reduce the readings to a count, a mean, a sample standard deviation, a
   minimum and a maximum, and index which pulls were weak and which
   separated at an interface.
6. Declare the lot bondable only when the sample met both floors, no pull
   separated at an interface and no pull fell below the minimum; otherwise
   report the finding that governs.

## Pitfalls

- Grading the pull on force alone. The force test and the separation mode
  test are independent, and a sample of strong lifts at the termination is
  a failed lot that a force-only summary reports as passing comfortably.
- Using one minimum force for the whole programme. The minimum belongs to
  the wire diameter and material on the sample, so a figure carried over
  from a different wire is either unearned or unreasonably harsh.
- Extrapolating the pull table to cover the wire in hand. The relationship
  is not linear outside the tabulated span, so a value invented past the
  ends is not a conservative estimate, it is an unknown presented as a
  limit.
- Pulling enough bonds from too few chips. The bond count is satisfied and
  the lot is still unsampled, because the variation the test exists to find
  lives between chips, not between bonds on one chip.
- Reporting only the mean. A comfortable mean hides a low minimum, and the
  low minimum is the reading that predicts the escape.
- Failing a bond that read exactly the minimum. The equality is a
  representation question about an interpolated limit, handled by the
  tolerance inside the comparison, not a reason to reject the lot.

## Behavior contract (gate 3)

The wire material resolution, minimum pull force interpolation, sample
floors, separation mode categorization, per-pull verdict, pull statistics
and the lot bondability decision are exercised by the gate 3 contract test:
scripts/test_q6005_passive_chip_bondability_test.py against
scripts/q6005_passive_chip_bondability_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_passive_chip_bondability_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
