---
name: means-of-compliance
description: "Use when you must select the means of compliance for each certification item in a civil aircraft certification program: assign the acceptable MOC class (moc-1 engineering analysis, moc-2 ground test, moc-3 flight test, moc-4 simulation tool, moc-5 similarity, moc-6 safety assessment) from deterministic suitability rules over item kind, severity class, DAL and a novelty screen, gate top-severity systems items on moc-6, and score the compliance matrix coverage per item kind. Produces the per-item MOC assignment, the coverage score, and a certification plan readiness verdict. Trigger: means of compliance, moc-1, moc-2, moc-3, moc-4, moc-5, moc-6, compliance matrix, certification item, coverage score, certification plan, novelty screening."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: certification
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: certification
  tags: [means-of-compliance, moc-1, moc-2, moc-3, moc-4, moc-5, moc-6, compliance-matrix, certification-item, coverage-score, novelty-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# Means of Compliance (systems-engineering-safety/certification/means-of-compliance)

Use when the task is selecting the acceptable means of compliance for
each certification item of a civil aircraft program and building the
per-item compliance matrix: which of the six MOC classes (MOC 1
engineering/analysis, MOC 2 ground test, MOC 3 flight test, MOC 4
simulation/analysis tool, MOC 5 certification by similarity, MOC 6
safety assessment) shows compliance with an applicable regulation
paragraph, whether the chosen method is acceptable for the item kind,
failure severity and development assurance level, and whether the
matrix covers every certification item.

This leaf owns the per-certification-item MOC matrix and the coverage
method. It pairs with certification-basis (the leaf that determines the
applicable paragraphs this leaf assigns MOC for) and with the
program-level certification sequencing leaves. It does NOT determine
the certification basis and does NOT scope ARP4754A verification method
assignment.

## Domain quick reference

- The MOC six-class scheme, summarized at reference level from public
  certification guidance (EASA and FAA style MOC categories):
  MOC 1 engineering/analysis, MOC 2 ground test, MOC 3 flight test,
  MOC 4 simulation/analysis tool, MOC 5 certification by similarity,
  MOC 6 safety assessment.
- Suitability by item kind (deterministic summary, ordered primary
  first):
  - structure: MOC 1 analysis primary with MOC 2 static/ground test
    evidence; a novel structural item adds flight test MOC 3.
  - systems (electronic): MOC 1 plus MOC 6 for catastrophic or
    hazardous failures; MOC 4 simulation is acceptable for DAL C-E.
  - powerplant: MOC 2 bench/ground test and MOC 3 flight test typical,
    MOC 1 analysis supporting.
  - equipment: MOC 2 environmental qualification test (DO-160 style)
    with MOC 1 analysis support.
  - software: MOC 1 lifecycle data per DO-178C plus MOC 4 tool
    qualification where tools are used; the software MOC is the
    DO-178C process assurance, not a test article.
  - hardware: MOC 1 plus MOC 2 (DO-254 style verification).
  - performance and handling: MOC 3 flight test with MOC 1 analysis
    and MOC 4 simulation.
- Acceptance rules: a catastrophic systems item requires MOC 6 in its
  compliance set; a novel structure or systems item requires a test
  MOC (2 or 3) in addition to analysis; MOC 5 similarity is rejected
  for any novel item (similarity is reserved for minor changes and is
  never auto-recommended by this leaf).
- Coverage: overall score = (items with at least one accepted MOC) /
  (all items); per-kind scores reported alongside.
- Readiness verdict: PASS when coverage is 1.0 and no catastrophic
  systems item lacks MOC 6, otherwise FAIL with the item-level reasons.

## Workflow

1. Enumerate the certification items: for each applicable regulation
   paragraph record item_id, regulation_paragraph, item_kind (one of
   structure, systems, powerplant, equipment, software, hardware,
   performance, handling), failure_severity, development_assurance_level
   and the novelty screen flag.
2. Recommend the MOC set per item with moc_suitability(item_kind,
   severity, dal, novel); the function returns the ordered list with the
   primary MOC first, or raises ValueError on an unknown kind, severity
   or DAL string.
3. Gate each assigned set with accept_item(item, recommended): confirm
   the MOC 6 requirement for catastrophic systems items, the test MOC
   requirement for novel structure or systems items, and the MOC 5
   rejection for novel items. Pass item["assigned_mocs"] to evaluate a
   team-proposed set against the suitability recommendation.
4. Assemble the matrix with build_compliance_matrix(items): one row per
   certification item with recommended MOCs, the MOC set under
   evaluation, the primary MOC, the acceptance result and reason, plus
   the collected issues list.
5. Score coverage with coverage_score(matrix): overall ratio of items
   with at least one accepted MOC, and the per-kind ratios.
6. Close with compliance_verdict(matrix): PASS only when coverage is
   1.0 and every catastrophic systems item carries MOC 6; the reasons
   list names every rejected item.
7. Confirm the deterministic checks with the contract test
   scripts/test_means_of_compliance.py.

## Worked example

Three certification items from a transport category program:
1. FCS-1 (25.671, systems, catastrophic, DAL A, novel true): the
   fly-by-wire flight control system.
2. STR-1 (25.307, structure, hazardous, novel false): primary structure
   static strength.
3. PP-1 (25.901, powerplant, major, novel false): powerplant
   installation.

- FCS-1 recommendation: moc_suitability("systems", "catastrophic", "A",
  True) returns [1, 6, 2]: analysis primary, the MOC 6 safety
  assessment mandated by the catastrophic severity, and ground test
  MOC 2 from the novelty screen, so a test MOC is present.
- STR-1 recommendation: moc_suitability("structure", "hazardous", "n/a",
  False) returns [1, 2]: MOC 1 analysis primary with static test
  evidence; hazardous severity on a structural item does not trigger
  any MOC 6 requirement.
- PP-1 recommendation: moc_suitability("powerplant", "major", "n/a",
  False) returns [2, 3, 1]: bench/ground test and flight test with
  supporting analysis.
- Matrix: all three rows accepted, zero issues, primary MOCs 1, 1, 2;
  coverage_score returns overall 1.0 and 1.0 for each of systems,
  structure and powerplant; compliance_verdict returns PASS.
- Negative check: assigning FCS-1 only MOCs 1 and 4 makes
  accept_item return False with the MOC 6 reason, and
  compliance_verdict returns FAIL for the matrix: the catastrophic
  flight control system must carry the safety assessment MOC 6.

## Verification

- Confirm the three worked example recommendations: FCS-1 [1, 6, 2]
  with MOC 6 and a test MOC present, STR-1 [1, 2] with MOC 1 primary
  and no MOC 6, PP-1 [2, 3, 1].
- Confirm compliance_verdict PASS for the full three item matrix and
  FAIL with the MOC 6 reason when FCS-1 is assigned only MOCs 1 and 4.
- Confirm coverage_score returns overall 1.0 for the full set and 0.5
  with per-kind ratios when one of two items is rejected.
- Confirm ValueError rejection of item_kind "quantum", severity
  "very-bad", unknown DAL strings, and an empty item list.
- Run the contract test offline: python3
  scripts/test_means_of_compliance.py (34 tests, deterministic).

## Related leaves

- systems-engineering-safety/certification/certification-basis: names
  the applicable regulation paragraphs this leaf assigns MOC for.
- avionics/far-cs25/airworthiness (program-level): the coarse four-way
  analysis/test/inspection/similarity selection and program sequencing
  around this per-item matrix.
- avionics/far-cs25/special-conditions: the special condition scope for
  the novel features screened by the novelty flag.
- systems-engineering-safety/arp4754a/verification-planning: ARP4754A
  verification method assignment, the development activity this leaf
  does not cover.

## Pitfalls

- Releasing a catastrophic systems item without MOC 6: the safety
  assessment is mandated for catastrophic (and hazardous) systems
  failures, so FCS-1 assigned only MOCs 1 and 4 is rejected with the
  MOC 6 reason and the compliance verdict FAILs even if other items
  pass.
- Accepting similarity for a novel item: MOC 5 is rejected for any
  novel item — similarity is reserved for minor changes and is never
  auto-recommended — and a novel structure or systems item needs a
  test MOC (2 or 3) in addition to analysis.
- Using simulation where it is not allowed: MOC 4 simulation is
  acceptable for systems items at DAL C-E, so it neither substitutes
  for the test MOC of a novel item nor for the MOC 6 of a
  catastrophic one.
- Reading the overall score without the verdict gates: coverage 1.0
  alone is not readiness — PASS requires coverage 1.0 AND every
  catastrophic systems item carrying MOC 6, with the reasons list
  naming each rejected item.
- Recommending a MOC set out of the suitability order: the function
  returns the ordered list with the primary MOC first (FCS-1 [1, 6,
  2], STR-1 [1, 2], PP-1 [2, 3, 1]), and unknown kinds, severities or
  DAL strings raise ValueError instead of scoring.
- Confusing this matrix with neighboring scopes: this leaf assigns
  per-item MOC but does not determine the certification basis
  (certification-basis owns that) and does not scope ARP4754A
  verification method assignment (verification-planning owns that).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_means_of_compliance.py

The test covers suitability per item kind (structure, systems,
powerplant, equipment, software, hardware, performance, handling), the
MOC 6 severity gating and DAL C-E MOC 4 allowance for systems items,
novelty upgrades and MOC 5 rejection, acceptance gating, matrix
construction with the worked example items FCS-1, STR-1 and PP-1,
coverage math overall and per kind, PASS and FAIL verdict logic with
the MOC 6 reason, and ValueError rejection of unknown kinds,
severities, DALs and an empty item list.

## Compliance

- FAR-25 and CS-25 are cited as reference only: regulation paragraph
  numbers such as 25.671, 25.307 and 25.901 identify the certification
  items in the worked example. The MOC six-class scheme and the
  suitability table are deterministic summaries at reference level
  derived from public certification guidance; no verbatim AMC or
  regulatory text is reproduced and no standard is reproduced.
- compliance: STANDARDS-REF, gated: false.

