---
name: e2020-lcl-requirements-verification-overview
description: "Determine which compliance method discharges each protection-device requirement under ECSS-E-ST-20-20C clause 4.1. Use when a requirement list has to become an auditable verification matrix rather than a statement of intent: refuse a method token outside the declared vocabulary, refuse a requirement carrying none at all, reject a duplicate identifier, insist that a requirement fixing a number is discharged by test or analysis and not by design review alone, take the covered and evidence-bearing shares against their policy floors, and name every requirement nobody has planned to demonstrate. Trigger: ecss, e-st-20-20c-clause-4-1, lcl-verification-method-matrix, protection-device-requirement-coverage, verification-method-vocabulary, quantitative-limit-verification-evidence, uncovered-protection-requirement, verification-matrix-coverage-floor."
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
  tags: [ecss, e-st-20-20-power-protection-device-scope, e2020-lcl-requirements-verification-overview, lcl-verification-method-matrix, protection-device-requirement-coverage, verification-method-vocabulary, quantitative-limit-verification-evidence, uncovered-protection-requirement, verification-matrix-coverage-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Protection Devices -- Requirements Verification Overview (space-systems/ecss/e2020-lcl-requirements-verification-overview)

Use when the task is the clause 4.1 overview of ECSS-E-ST-20-20C: the
standard's requirements on latching current limiters and the other
protection devices have been collected, and for each one the method by
which compliance will be shown has to be identified before anybody can
claim the set is verifiable.

## Domain quick reference

- Identifying the method is the point of the clause, not paperwork
  around it. A requirement whose method is unstated has not been
  planned, costed or scheduled, and the first person to notice is
  usually the one who needs a trip-time measurement on hardware that
  has already shipped.
- The method has to come from a declared vocabulary: test, analysis,
  review of design, inspection. "Verified", "heritage" and "by
  similarity" are not methods. A similarity argument becomes a method
  only once it is itself written up as an analysis, and until then an
  invented token cannot be audited by anyone but its author.
- A requirement may carry more than one method, and that is worth
  recording rather than collapsing to the strongest. A requirement
  resting on a single method has no fallback when that method is lost
  late -- a facility slot, a sample, a model that will not converge.
- A requirement that fixes a number needs a method that produces a
  number. Trip current, trip time, off-state leakage and voltage drop
  are demonstrated by test or by analysis. Review of design can confirm
  that the circuit intends to meet the limit; it cannot show that it
  does, so that pairing is a finding rather than a coverage entry.
- Review of design and inspection stay fully admissible where the
  requirement is not quantitative -- configuration, marking, separation
  of redundant paths -- and demoting them everywhere buys test cost
  without buying evidence.
- Coverage is judged on the whole set, not on the populated part of the
  matrix. A matrix that is ninety per cent populated is not ninety per
  cent of a compliance case; the remainder is the part nobody planned.
- The share of the set carrying test or analysis is a second, separate
  reading. A fully populated matrix that rests almost entirely on
  review and inspection is complete and still thin, and only the
  evidence-bearing share shows it.

## Workflow

1. Validate the verification policy first: the smallest covered share
   and the smallest evidence-bearing share the matrix must reach. A
   share outside zero to one is refused, as is an evidence floor above
   the coverage floor, which asks for evidence on requirements that
   carry no method at all.
2. Read the matrix reference. A requirement set with no matrix behind
   it closes the assessment on method not established, because there is
   nothing an auditor can be pointed at.
3. Validate every requirement record: a non-blank identifier, no
   duplicate identifier, a method sequence rather than a bare string,
   and a boolean saying whether the requirement fixes a number.
   Collapse a method repeated in one record so it is counted once.
4. Reduce each declared method to the agreed vocabulary, refusing a
   token outside it by name rather than dropping it quietly.
5. Grade each requirement: covered when it carries at least one method,
   and when a requirement that fixes a number carries test or analysis
   among them. Record every finding on a requirement, not the first.
6. Take the covered share and the evidence-bearing share of the whole
   set, group the requirement identifiers under the methods that
   discharge them, and name the uncovered requirements explicitly.
7. Compare both shares against their policy floors, a share landing
   exactly on a floor being admissible, and raise a single-method
   advisory for each covered requirement resting on one method.
8. Close on one verdict: verification method not established,
   verification coverage below policy floor, or matrix covers
   requirement set.

## Pitfalls

- Reporting the populated share of the matrix as the coverage figure.
  The denominator is the whole requirement set, and quoting the
  populated part makes an incomplete plan read as a complete one.
- Accepting an invented method token because everyone on the programme
  knows what it means. Nobody outside it does, and a method that cannot
  be planned or costed will not be performed.
- Letting review of design discharge a trip-current or trip-time limit.
  It confirms intent, not achievement, and the shortfall surfaces at
  qualification where it is most expensive.
- Demoting review of design and inspection everywhere. They are the
  right methods for configuration, marking and separation requirements,
  and replacing them with test buys cost rather than evidence.
- Collapsing a multi-method requirement to its strongest method. The
  second method is the fallback, and erasing it from the matrix erases
  the only route left when the first one is lost.
- Quoting a complete matrix with no evidence-bearing share beside it. A
  set discharged almost entirely by review is fully populated and still
  thin, and the verdict alone does not show it.

## Behavior contract (gate 3)

The policy validation, matrix reference check, requirement record
validation, method vocabulary reduction, per-requirement grading, the
covered and evidence-bearing shares, the grouping of requirements under
their methods, the uncovered list, the single-method advisories and the
verdict are exercised by the gate 3 contract test:
scripts/test_e2020_lcl_requirements_verification_overview.py against
scripts/e2020_lcl_requirements_verification_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_lcl_requirements_verification_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
