---
name: fmes-coverage-analysis
description: "Use when you must verify the coverage of the failure-mode effect rows over the functional-hazard condition set: map every FMEA row to the failure condition it demonstrates through its condition_id, list the covered and the uncovered condition ids, flag the rows that carry no condition link as orphan rows, and report the coverage ratio of covered over total conditions. Breaks the coverage down per severity class when conditions carry severity, and suggests candidate condition ids for unlinked rows with a deterministic text-match score. Produces the covered and uncovered condition id lists, the orphan row list, the coverage ratio, the per-severity-class coverage dict and the match suggestions that gate the FMEA-to-FHA loop before the assessment closes. Trigger: fmes-coverage-analysis, fmea-fha-coverage, uncovered-failure-condition, orphan-row-flag, condition-match-score."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4761a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags: [fmes-coverage-analysis, fmea-fha-coverage, uncovered-failure-condition, orphan-row-flag, condition-match-score]
  version: 0.1.0
  author: AeroSkills
---

# FMEA-to-FHA Coverage Analysis (systems-engineering-safety/arp4761a/fmes-coverage-analysis)

Use when you must verify the coverage of the failure-mode effect rows
over the functional-hazard condition set, the ARP4761A failure modes and
effects summary step that closes the FMEA-to-FHA loop before the
assessment is done. Every FMEA row is mapped to the failure condition it
demonstrates through its condition_id; conditions with at least one row
are covered, conditions with no row at all are uncovered, and rows that
carry no condition link are flagged as orphans. The coverage ratio
covered over total conditions, the per-severity-class breakdown and the
deterministic text-match suggestions for unlinked rows gate whether the
failure modes really demonstrate the whole condition set. Pure Python,
stdlib only. It pairs with systems-engineering-safety/arp4761a/fta-fmea
and systems-engineering-safety/arp4761a/failure-mode-criticality, which
build and rate the failure-mode catalogue, and with
systems-engineering-safety/arp4761a/functional-hazard-assessment, which
defines the condition table and its severities.

## Domain quick reference

- Row-to-condition mapping: every failure-mode effect row carries a
  condition_id naming the failure condition the row demonstrates; a row
  with no link writes condition_id None and is an orphan row
  (coverage_score).
- Coverage ratio: coverage = number of conditions with at least one row
  over the total number of conditions, a float in [0, 1]; empty rows
  give 0.0 with every condition uncovered and no orphans.
- Typo guard: a condition_id that is not an id in the condition table
  raises ValueError instead of silently degrading coverage; an analyst
  who means no link writes condition_id None explicitly.
- Token normalization: normalize(text) returns the lowercase
  alphanumeric tokens of the text via re.findall(r"[a-z0-9]+",
  text.lower()), stripping punctuation, case and whitespace runs.
- Text-match score: condition_match_score(row_text, condition_text) is
  the Jaccard similarity over the normalized token sets, in [0, 1];
  both token sets empty scores 0.0 because there is no evidence to
  match on. A text-only suggestion helper, never a substitute for the
  analyst's condition_id assignment.
- Per-severity class coverage: coverage_by_severity reports covered and
  uncovered counts and the class coverage for every severity present in
  the condition table, in first-appearance order.
- This leaf checks condition coverage only. It does not rank per-mode
  rates or compute criticality numbers, reduce fault trees, map
  severities to development assurance levels, or classify severities
  and populate FHA worksheets.
- ARP4761A frames the failure modes and effects summary step of the
  safety assessment, name and paraphrase only.

## Workflow

1. Gather the condition table and the row links: every FHA condition
   with its id, description and severity, and every failure-mode row
   with its row_id and condition_id (None when the row is unlinked).
2. Normalize row and condition text with normalize(text) into lowercase
   alphanumeric tokens for the matching step.
3. Score row-to-condition text similarity with
   condition_match_score(row_text, condition_text) to suggest candidate
   condition ids for rows that have no link yet.
4. Map every row to the condition it demonstrates with
   coverage_score(conditions, rows): read the covered_conditions list,
   the uncovered_conditions list, the orphan_rows flags and the
   coverage ratio from the returned dict.
5. Break the same coverage down per severity class with
   coverage_by_severity(conditions, rows) when the conditions carry
   severity, to see which classes the uncovered conditions fall into.
6. Read the covered and uncovered condition id lists and the orphan row
   flags to gate the FMEA-to-FHA coverage loop: rows still unlinked and
   conditions still uncovered mean the assessment does not close.
7. Confirm the deterministic checks with the contract test: python3
   scripts/test_fmes_coverage_analysis.py.

## Worked example

Ten FHA conditions FC-01..FC-10 (FC-01 and FC-02 catastrophic, FC-03
and FC-04 hazardous, FC-05..FC-07 major, FC-08..FC-10 minor) and 14
FMEA rows R-01..R-14: R-01, R-02 to FC-01; R-03, R-04 to FC-02; R-05 to
FC-03; R-06, R-07 to FC-04; R-08, R-09 to FC-05; R-10, R-11 to FC-06;
R-12 to FC-07; R-13 and R-14 are orphans (condition_id None).

Step 4 coverage_score returns covered_conditions [FC-01, FC-02, FC-03,
FC-04, FC-05, FC-06, FC-07], uncovered_conditions [FC-08, FC-09,
FC-10], orphan_rows [R-13, R-14] and coverage 0.7: 7 of 10 conditions
are demonstrated by at least one row, and the three minor-class
conditions plus two rows are unlinked, so the FMEA does not yet close
the FHA.

Step 5 coverage_by_severity returns catastrophic covered 2 of 2
(coverage 1.0), hazardous 2 of 2 (1.0), major 3 of 3 (1.0) and minor 0
of 3 (0.0): the entire coverage gap sits in the minor class.

Step 3 anchors: "loss of all pitch control authority" against "loss of
pitch control" scores 0.666667, "flap asymmetry drives uncommanded
roll" against "uncommanded roll excursion" 0.333333, "autopilot
disengages without crew annunciation" against "loss of autopilot
engagement" 0.125; identical texts score 1.0, disjoint texts 0.0.
normalize("Loss of PITCH-control, authority!") returns [loss, of,
pitch, control, authority].

## Verification

- Confirm coverage_score on the worked example returns coverage 0.7
  exactly with covered FC-01..FC-07, uncovered FC-08..FC-10 and orphan
  rows R-13, R-14, lists in input order.
- Confirm duplicate rows for one condition count once in
  covered_conditions, full coverage gives 1.0 with no uncovered ids,
  and an empty rows list gives 0.0 with every condition uncovered.
- Confirm the rejections: a row whose condition_id names an unknown
  condition, an empty conditions list, and rows missing the row_id or
  condition_id key all raise ValueError, while the same row written
  with condition_id None is accepted as an orphan.
- Confirm coverage_by_severity on the worked example (catastrophic 1.0,
  hazardous 1.0, major 1.0, minor 0.0 with covered 0 and uncovered 3)
  and its ValueError when a condition has no severity field.
- Confirm normalize strips digits-adjacent punctuation and is idempotent
  on its own output, and condition_match_score of a text with itself is
  1.0, of disjoint texts 0.0 and of the empty pair 0.0.
- Run the contract test offline: python3
  scripts/test_fmes_coverage_analysis.py (35 tests, deterministic).

## Related leaves

- systems-engineering-safety/arp4761a/fta-fmea: owns the failure-mode
  catalogue and maps severity categories to development assurance
  levels; this leaf checks that the catalogue rows cover the FHA
  condition set rather than building the modes themselves.
- systems-engineering-safety/arp4761a/functional-hazard-assessment:
  identifies, rates and targets the failure conditions that form the
  condition table this leaf consumes.
- systems-engineering-safety/arp4761a/failure-mode-criticality: ranks
  the modes of one item by rate-based criticality; its numbers say
  nothing about which FHA conditions those modes cover.
- manufacturing-quality/as9100/risk-management: owner of the ordinal
  1 to 10 product rating scales, a different risk treatment than the
  condition-coverage check here.

## Pitfalls

- Closing the FHA while rows still carry no condition link: the orphan
  row flags and the uncovered condition list are the gate, and a
  coverage ratio below 1.0 with orphans means rows are unaccounted for
  in the failure modes and effects summary.
- Writing a mistyped condition_id instead of None: the typo guard
  raises ValueError so a wrong link cannot silently inflate the
  coverage ratio; deliberate no-links are written as condition_id None.
- Treating the text-match score as the assignment: condition_match_score
  only suggests candidate condition ids for the analyst to review, it
  never assigns the condition_id by itself.
- Reporting the single coverage ratio without the severity breakdown:
  in the worked example the ratio 0.7 hides that the whole gap sits in
  the minor class, which the per-severity dict makes visible.
- Counting duplicate rows as extra coverage: two rows to one condition
  cover that condition once, so coverage counts conditions, not rows.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fmes_coverage_analysis.py

The test covers the normalize() tokenization and idempotency of
workflow step 2, the condition_match_score() anchors and symmetry of
step 3, the coverage_score() worked example with coverage 0.7, covered
FC-01..FC-07, uncovered FC-08..FC-10 and orphan rows R-13, R-14 of
step 4, duplicate-row handling, full coverage at 1.0, empty rows at
0.0, input-order preservation, and every ValueError rejection listed
in the spec, plus the coverage_by_severity() class breakdown and
missing-severity rejection of step 5.

## Compliance

- Standards referenced, not reproduced: ARP4761A is a SAE standard
  (sae.org/standards); the failure modes and effects summary step is
  named and paraphrased, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
