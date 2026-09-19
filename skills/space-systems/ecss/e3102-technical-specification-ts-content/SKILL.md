---
name: e3102-technical-specification-ts-content
description: "Structure and grade the technical specification content ECSS-E-ST-31-02 clause 5.1 requires of two-phase heat transport equipment: check the four families of content, performance, environmental, interface and test data, against the mandatory topics each owes, then test every individual requirement for a number, a unit, a workable tolerance and a named verification method, and report a topic that is missing separately from a requirement that cannot be closed. Use when a heat pipe or loop heat pipe technical specification is being written or reviewed before it is issued to a supplier. Trigger: ecss, e-st-31-02-two-phase, two-phase-technical-specification-content, ts-performance-requirements, ts-environmental-requirements, ts-interface-requirements, ts-test-data-requirements, requirement-verifiability-audit."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-technical-specification-ts-content, two-phase-technical-specification-content, ts-performance-requirements, ts-environmental-requirements, ts-interface-requirements, ts-test-data-requirements, requirement-verifiability-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Technical Specification Content (space-systems/ecss/e3102-technical-specification-ts-content)

Use when the task is the technical specification of ECSS-E-ST-31-02
clause 5.1 -- working out what a two-phase heat transport specification
has to contain before it goes to a supplier, and whether the draft in
hand actually contains it in a form anybody can verify.

## Domain quick reference

- The specification is the document the equipment is bought, built and
  verified against. The clause therefore asks two independent questions
  of it, and a draft can pass one and fail the other.
- Coverage runs over four families. Performance: what the equipment has
  to transport and how well, including transported power, conductance,
  adverse tilt and start-up. Environmental: what it survives while doing
  it, operating and non-operating temperature, vibration and radiation.
  Interface: mounting, thermal contact, envelope and mass, bonding.
  Test data: what evidence comes back with the hardware, and to what
  uncertainty.
- Verifiability is a property of the individual requirement, not of the
  document. A statement needs a number, a unit, a tolerance and a named
  verification method before it can be closed at a review, however well
  it reads.
- A zero tolerance is the specific trap. It looks rigorous and no
  measurement can meet it, so it converts into a waiver on first
  contact with a test report. A negative tolerance is simply an error.
- The verification method has to come from a fixed set -- test,
  analysis, review of design, inspection -- because the method decides
  what evidence is admissible. An unnamed method is an open question
  disguised as a closed requirement.
- Supplementary content is allowed and is not a defect. A topic the
  project adds beyond the mandatory set is recorded as supplementary so
  the reviewer can see the specification is wider than the floor, not
  off it.

## Workflow

1. Take the draft as a list of typed requirements, each carrying an
   identifier, a content family and a topic. Refuse a repeated
   identifier: two requirements with one identifier cannot both be
   tracked to closure.
2. Index the requirements by family and topic, separating the mandatory
   topics from the supplementary ones the project has added.
3. Compute coverage per family against the mandatory topic list, and
   keep the counts as integers so a completeness verdict never rests on
   a rounded fraction.
4. Assess each requirement for verifiability independently of coverage:
   finite value, real unit, positive tolerance, named method. Collect
   every reason a requirement fails rather than stopping at the first.
5. Raise one finding per missing topic and one per unverifiable
   requirement, so a review can see at a glance whether the gap is
   breadth or quality.
6. Close complete only when coverage is whole AND nothing is
   unverifiable; either failing keeps the specification open.

## Pitfalls

- Grading the specification on page count or section headings. A
  section can exist and contain nothing verifiable, which is exactly the
  draft that passes an internal review and fails at the supplier's first
  question.
- Writing a performance number with no tolerance. Two-phase transport
  numbers are measured with real uncertainty, and a bare figure gives
  the test engineer no band to pass against.
- Setting a tolerance to zero to look demanding. It cannot be met, so it
  is waived, and a waived requirement is weaker than a realistic one.
- Deriving completeness from a percentage. The coverage fraction is for
  reporting; the verdict comes from the integer count of covered topics
  against required ones, because a fraction that rounds to one is not
  the same as nothing missing.
- Leaving the test data family to the acceptance phase. The evidence the
  specification asks for decides what the supplier instruments and
  records, and asking after the tests are run means the data does not
  exist.

## Behavior contract (gate 3)

Requirement validation, verifiability assessment, requirement indexing,
per-family and overall coverage, supplementary topic reporting and the
completeness verdict are exercised by the gate 3 contract test:
scripts/test_e3102_technical_specification_ts_content.py against
scripts/e3102_technical_specification_ts_content_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_technical_specification_ts_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
