---
name: q7046-qualification-test-programme
description: "Build the qualification test programme a threaded fastener type owes before it is released for flight procurement. Use when a fastener type, size variant or production lot has to be qualified, or when a material, heat-treatment, coating or source change raises how much of the qualification has to be repeated: take the required test set from the criticality category, allocate specimens per test across the lots and size variants actually offered, separate the tests that must be drawn lot by lot from those owed once per variant, and report a programme still owing specimens rather than calling it qualified. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-qualification-test-programme, fastener-qualification-specimen-allocation, fastener-requalification-trigger, fastener-lot-and-type-coverage."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-qualification-test-programme, fastener-qualification-test-programme, fastener-qualification-specimen-allocation, fastener-requalification-trigger, fastener-lot-and-type-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Qualification Test Programme (space-systems/ecss/q7046-qualification-test-programme)

Use when the task is the testing clause of ECSS-Q-ST-70-46 at programme
level: deciding which mechanical-property tests a fastener type owes,
how many specimens each test takes, how those specimens spread over the
production lots and size variants on offer, and what a change to the
material, the heat treatment, the coating or the source costs in
re-testing.

## Domain quick reference

- Qualification is owed by a fastener *type* — one part number, one
  material, one heat-treatment route, one coating — and evidenced by
  specimens drawn from real production lots of that type. A type
  qualified on engineering samples has no lot evidence behind it.
- The required test set comes from the criticality the fastener is used
  at, not from what the supplier happens to offer. A fracture-critical
  fastener owes the full mechanical set plus microstructure and
  embrittlement evidence; a structural fastener owes the load-carrying
  subset; non-structural hardware owes the basics.
- Tests split into two groups by what they are sensitive to. Tensile,
  proof, hardness, microstructure and coating thickness move with the
  heat-treatment and plating of the individual lot, so they are drawn
  lot by lot. Shear, fatigue, torque-tension, corrosion and stress
  rupture are geometry- and process-driven, so one set per size variant
  answers for every lot of that variant.
- Specimen counts are per test, not per programme. Multiplying one
  headline number across every test either over-buys hardware on the
  cheap tests or under-samples the expensive ones.
- A change does not reopen the whole programme. Re-qualification scope
  is the intersection of the tests that change can move with the tests
  the category already owed, so a coating change costs the coating,
  corrosion, embrittlement and torque-tension evidence and leaves the
  tensile evidence standing — while a change of material grade or of
  manufacturing source reopens everything.
- An incomplete programme has no verdict. Naming the test and the
  specimen shortfall is the useful output; "not yet qualified" without
  the shortfall sends someone back to count it again.

## Workflow

1. Read the criticality category and refuse an uncategorized type
   rather than defaulting it to the lightest set.
2. Take the required test set and the per-test specimen count for that
   category.
3. Validate the lot count and the size-variant count offered; both are
   positive integers, and a zero of either is an input error, not an
   empty programme.
4. Allocate specimens: a lot-sensitive test takes its count for every
   lot and every variant; a variant-driven test takes its count once per
   variant. Sum to the programme total.
5. Compare the specimens actually tested, per test, against the
   allocation. Report every shortfall with its test name and the number
   of specimens outstanding; report a test recorded that the category
   never asked for as a finding rather than a failure.
6. For each declared change, intersect the tests that change can move
   with the required set and report the re-qualification scope; refuse
   an unrecognised change type instead of guessing it is harmless.
7. Give a verdict only when nothing is outstanding and no declared
   change is unanswered.

## Pitfalls

- Qualifying a type on one lot. A single lot cannot show lot-to-lot
  spread in heat treatment, which is exactly what the lot-sensitive
  tests exist to bound.
- Treating a size variant as covered because a neighbouring size was
  tested. Shear and fatigue scale with geometry, and the thread run-out
  of a short variant is not the thread run-out of a long one.
- Applying one specimen count to every test. The count belongs to the
  test, and copying the largest across the set is a procurement cost
  that buys no extra evidence.
- Re-running the entire programme after a coating change. The scope is
  the intersection with the required set; re-testing tensile evidence
  that the change cannot move spends schedule for nothing.
- Accepting an unrecognised change type as no-impact. An unknown change
  is unscoped, not harmless, and has to be refused so a human decides.
- Reporting "not qualified" without the shortfall. The outstanding
  specimen count per test is what lets procurement close the programme.

## Behavior contract (gate 3)

The category rules, specimen allocation over lots and variants, the
lot-sensitive versus variant-driven split, the shortfall accounting and
the re-qualification scope are exercised by the gate 3 contract test:
scripts/test_q7046_qualification_test_programme.py against
scripts/q7046_qualification_test_programme_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_qualification_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
