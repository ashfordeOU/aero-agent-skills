---
name: e20-antenna-requirement-verification
description: "Use when verify the antenna engineering provisions of ECSS-E-ST-20C clause 7.2.4: assign each antenna requirement a verification method its characteristic can actually evidence, check the planned closure gate is neither earlier than that method can physically close nor later than the gate the antenna category is held to, confirm every closed requirement names a well-formed antenna verification record and every waived one carries a reference and a rationale, and compute the verification-coverage fraction against the agreed threshold before the antenna data package is presented. Trigger: ecss, e-st-20-electrical-scope, antenna-requirement-verification, antenna-verification-matrix, radiation-pattern-verification, antenna-review-gate-closure, antenna-verification-record, guided-wave-interface-verification."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-requirement-verification, antenna-verification-matrix, radiation-pattern-verification, antenna-review-gate-closure, antenna-verification-record, guided-wave-interface-verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Antenna Requirement Verification (space-systems/ecss/e20-antenna-requirement-verification)

Use when the task is the verification side of the antenna engineering
provisions of ECSS-E-ST-20C clause 7.2.4 -- choosing the method that
closes each antenna requirement, placing its closure at a review gate
the method can actually reach, and proving the antenna verification
matrix carries a record for every requirement it declares closed.

## Domain quick reference

- The antenna provisions of clause 7.2 are requirements like any
  other: each one is closed by exactly one of the ECSS verification
  methods -- analysis, review-of-design, verification-by-test,
  inspection, or similarity -- and the method has to produce evidence
  for the characteristic being claimed. A radiation-pattern or
  gain-and-polarization requirement is a measured electromagnetic
  quantity, so it closes by verification-by-test or by a correlated
  analysis; a guided-wave-interface requirement is an as-built
  property, so it closes by verification-by-test or inspection; a
  materials-and-finish requirement is an observable or heritage
  argument, so it closes by inspection, review-of-design or
  similarity. A failure-rate-allocation requirement is arithmetic on
  the reliability data, so it never closes by inspection.
- A method cannot close before the evidence it needs exists.
  Review-of-design argues from design data, so it can close from the
  preliminary-design gate onward; analysis and similarity need the
  detailed design, so they close from the critical-design gate onward;
  verification-by-test and inspection need representative hardware, so
  they close no earlier than the qualification gate. Placing a
  verification-by-test closure at the preliminary-design gate is a
  planning defect, not an aggressive schedule.
- Each antenna requirement category is also held to a latest gate: the
  antenna performance requirements close by the qualification review,
  the design-data categories by the critical-design review. A closure
  planned after that gate leaves the antenna data package incomplete
  at the point the gate needs it.
- A requirement is open, closed, or waived. A closed requirement names
  a well-formed verification record identifier in the antenna
  verification matrix; the matrix entry, not the engineer's memory, is
  the evidence. A waived requirement names a waiver reference and a
  written rationale -- a waiver with neither is an untraced deviation.
- Verification-coverage is the fraction of antenna requirements that
  are closed or formally waived. The agreed threshold is compared with
  a tolerance so that an exactly-met fraction expressed as a ratio of
  integers is not read as a shortfall by floating-point representation
  alone.

## Workflow

1. Load the antenna requirement list. Reject a duplicate requirement
   identifier and an unrecognized antenna requirement category before
   any assessment runs -- an unknown category has no admissible-method
   set, so no verdict about it is defensible.
2. For each requirement, normalize the declared verification method
   and the planned review gate, then check the method against the
   admissible set for that antenna category. Flag a method that cannot
   evidence the characteristic.
3. Check the planned gate against the earliest gate the chosen method
   can reach, and against the latest gate the category is held to.
   Flag both directions separately; they are different defects with
   different fixes (re-plan the method vs. re-plan the schedule).
4. For each closed requirement, confirm the verification record
   identifier is present and well formed. For each waived requirement,
   confirm both the waiver reference and the rationale are present.
5. If an assessment gate is supplied, flag every requirement still
   open whose planned closure gate has already been reached or passed.
6. Compute verification-coverage over the whole requirement set and
   compare it with the agreed threshold. The antenna requirement set
   is verification-compliant only when no requirement carries a
   finding and the coverage threshold is met.

## Pitfalls

- Accepting verification-by-test as the answer for every antenna
  requirement because it sounds strongest -- a materials-and-finish or
  failure-rate-allocation requirement has no measurable pass/fail at
  antenna level, and the resulting matrix entry closes nothing.
- Planning an inspection or a verification-by-test closure at the
  preliminary-design gate. The method is admissible, the gate is not
  reachable, and the defect stays invisible until the gate itself.
- Reading a blank record field as "record to follow". A closed
  requirement with no verification record identifier is an open
  requirement that has been marked closed.
- Treating a waiver as a closure. A waiver without a reference and a
  rationale is an untraced deviation and is counted as a finding here,
  even though the requirement leaves the open list.
- Comparing the coverage fraction with the threshold using a bare
  floating-point comparison -- an exactly-met ratio such as
  seven-over-nine can land a few units in the last place below the
  same value written as a decimal and read as a false shortfall. The
  comparison absorbs the representation error; it never relaxes the
  agreed threshold itself.

## Behavior contract (gate 3)

The method-admissibility, gate-feasibility, record-presence,
waiver-completeness and coverage logic is exercised by the gate 3
contract test: scripts/test_e20_antenna_requirement_verification.py
against scripts/e20_antenna_requirement_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_antenna_requirement_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
