---
name: e2008-coverglass-testing-overview
description: "Use when a coverglass test matrix or lot sampling plan needs its qualification and procurement halves separated. Map a declared coverglass test matrix onto the two roles ECSS-E-ST-20-08C clause 8.3.1 keeps apart: the tests that carry qualification evidence for a design and a process, and the tests that run as routine lot procurement. Group the declared set against the catalogue, catch a test booked under a role it cannot serve, grade each mandatory set on the fraction actually booked, size the per-lot specimen draw and the over-build a destructive lot test forces, and return one programme verdict with the missing tests named. Trigger: ecss, e-st-20-08c-clause-8-3-1, coverglass-test-role-partition, coverglass-qualification-test-coverage, coverglass-lot-procurement-sampling, coverglass-test-misassignment, coverglass-destructive-specimen-demand."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c-clause-8-3-1, e2008-coverglass-testing-overview, coverglass-test-role-partition, coverglass-qualification-test-coverage, coverglass-lot-procurement-sampling, coverglass-test-misassignment, coverglass-destructive-specimen-demand]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Testing Overview (space-systems/ecss/e2008-coverglass-testing-overview)

Use when the task is to say which coverglass tests belong to
qualification and which belong to routine procurement under
ECSS-E-ST-20-08C clause 8.3.1 -- and to show a declared test matrix has
actually kept the two apart.

## Domain quick reference

- The coverglass test set is two programmes wearing one heading.
  Qualification runs once against a design and a process, is often long
  and often consumes the article, and answers whether the glass
  survives the environment at all. Procurement runs again on every lot
  delivered, is short and normally non-destructive, and answers whether
  this lot is the article that was qualified.
- Role is a property of the test, not of the project. An irradiation or
  thermal endurance run cannot become an incoming check by being
  written in that column, and an incoming batch identity check proves
  nothing about the design however often it is repeated.
- A test booked under a role it cannot serve is worse than a missing
  test, because the matrix reads as covered. That is why a
  misassignment sets the verdict on its own, ahead of any coverage
  arithmetic.
- Several tests genuinely serve both -- visual inspection, dimensional
  inspection, spectral transmittance -- so a test matrix is read as a
  mapping from each test to the programme or programmes it is booked
  to. A dual-role test is the normal case, not an exception to handle.
- Each programme carries its own mandatory set, and the sets are not
  the same length, so coverage is graded per programme and then
  weighted into one index rather than counted across the whole matrix.
- A declared coating drags its own test in, and not always into both
  programmes. A conductive coating adds a surface conductivity
  measurement to the lot programme as well; an ultraviolet-reflective
  coating adds a stability run that only qualification can hold,
  because the test is destructive and belongs to no lot.
- A destructive test placed in the procurement programme has a price in
  hardware. The specimens it consumes never reach the customer, so the
  lot has to be over-built by the draw, and the draw follows the lot
  size through a sampling fraction with a floor and a cap.

## Workflow

1. Validate the testing policy first: both programmes weighted above
   zero, a sampling fraction inside the unit interval, and whole-number
   sample limits with the cap at or above the floor.
2. Read the matrix as a booking of each test to one or both programmes,
   rejecting an unrecognised test or an unrecognised programme rather
   than skipping the entry.
3. Normalise the coating stack, because the mandatory sets move with
   it.
4. Catch misassignment first: every booking where the catalogue role
   forbids the programme claimed. This outcome stands on its own and is
   reported per booking, not once.
5. Group the declared tests by catalogue role so the qualification-only,
   procurement-only and dual-role populations can be seen apart.
6. Derive each programme's mandatory set, base tests plus what the
   coatings add and the role filter allows, and grade the fraction
   actually booked to that programme. A test booked only to the other
   programme counts as missing here.
7. Weight the two fractions into the overview index. A case landing
   exactly on the partial floor keeps the partial verdict; the
   comparison absorbs representation error and the floor does not move.
8. Size the lot draw from the lot size and the sampling policy, then
   total the specimens any destructive procurement test consumes.
9. Close on one verdict -- roles misassigned, mandatory tests missing,
   roles partially separated, or roles separated -- listing every gap
   and every over-build, not only the first.

## Pitfalls

- Writing one flat test list for the coverglass. The list cannot say
  which evidence is once-per-design and which is once-per-lot, so a
  qualification run quietly becomes a recurring cost and a lot check
  quietly becomes the qualification argument.
- Moving a long endurance run into incoming inspection to save a
  campaign. The role does not travel with the column heading; the
  matrix then reads as covered while the qualification evidence it
  claims does not exist.
- Counting a dual-role test once. A test that serves both programmes
  has to be booked to both, or one programme grades as short of a test
  that is in fact being run.
- Deriving the mandatory sets before the coatings are fixed. A coating
  added after the matrix was written reopens one or both programmes,
  and only the role filter decides which.
- Planning a destructive test into the lot programme without an
  over-build. The specimens are consumed, so a lot sized to the order
  ships short by the whole draw.
- Reading the weighted index as the answer. A high index can sit on top
  of a misassigned booking, which is exactly the case the verdict order
  is built to surface.

## Behavior contract (gate 3)

The policy validation, catalogue roles and destructiveness, permitted
test sets per programme, coating-driven mandatory sets, booking
normalisation, misassignment detection, role grouping, per-programme
coverage, weighted overview index, lot sample size, destructive
specimen demand and the programme verdict are exercised by the gate 3
contract test: scripts/test_e2008_coverglass_testing_overview.py
against scripts/e2008_coverglass_testing_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_testing_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
