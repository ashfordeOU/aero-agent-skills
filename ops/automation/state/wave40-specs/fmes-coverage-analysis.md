# Wave-40 leaf spec: fmes-coverage-analysis (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/fmes-coverage-analysis/
- Pack: arp4761a. Closest siblings: fta-fmea (owns the failure-mode
  catalogue, the fault tree logic and the severity-to-DAL mapping: "FMEA
  catalogues failure modes and effects; severity classes map to
  development assurance levels: A = Catastrophic, B = Hazardous, C =
  Major, D = Minor, E = No safety effect"; its pitfall "Severity mapped
  without the FHA-to-PSSA-to-SSA chain" shows it stops at the mapping, it
  does not trace FMEA rows back onto the FHA condition set),
  failure-mode-criticality (per-item rate ranking: "This leaf is rate-
  based only. It does not reduce fault trees, map severity categories to
  development assurance levels, rank fault-tree basic events by
  importance, model item states over time, or apply ordinal rating
  scales"; its C_m numbers rank modes of one item, they say nothing about
  which FHA conditions those modes cover), functional-hazard-assessment
  (defines the condition table this leaf consumes: it "identifies, rates,
  and targets failure conditions" and populates the per-row worksheet;
  no row-to-row coverage check exists there), fta-fmea and
  failure-mode-criticality both assume the FMEA and the FHA refer to the
  same condition set. Whole-tree greps at prep: "fmes" = 0 hits in
  skills/ and eval/; no leaf computes a coverage ratio between failure-
  mode rows and failure-condition ids. GENUINE SES gap (fresh probe): the
  ARP4761A failure modes and effects summary step, the FMEA-to-FHA
  coverage loop, is unowned.
- Standards id: arp4761a (reference-only). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Check the coverage of the failure-mode effect rows over the
functional-hazard condition set (the ARP4761A failure modes and effects
summary function, name and paraphrase only): map every FMEA row to the
failure condition it demonstrates through its condition_id, list the
conditions that own at least one row (covered) and the conditions with no
row at all (uncovered), flag the rows that carry no condition link
(orphans), and report the coverage ratio covered / total conditions;
break the same coverage down per severity class when the conditions carry
severity, and suggest candidate condition ids for unlinked rows with a
deterministic text-match score between row text and condition text.
Produces the covered and uncovered condition id lists, the orphan row
list, the coverage ratio, the per-severity-class coverage dict and the
text-match suggestions that gate the FMEA-to-FHA loop before the
assessment closes. Does NOT do: per-mode or per-item rate-based
criticality ranking and criticality numbers (failure-mode-criticality);
fault tree cut sets, severity-to-DAL mapping or the failure-mode catalogue
itself (fta-fmea); severity classification, probability target lookup or
worksheet population (functional-hazard-assessment); ordinal RPN rating
scales (manufacturing-quality risk-management).

## Model (implement exactly)

Functions (pure stdlib, re only):
- normalize(text) -> list of tokens: lowercase the text and split it into
  alphanumeric tokens with re.findall(r"[a-z0-9]+", text.lower()); strips
  punctuation, case and whitespace runs deterministically.
- condition_match_score(row_text, condition_text) -> float Jaccard
  similarity |A and B| / |A or B| over the normalized token sets of the
  row text and the condition text, in [0, 1]; both token sets empty gives
  0.0 (no evidence to match on, documented). Deterministic text-only
  helper for suggesting candidate condition ids to the analyst, not a
  substitute for the analyst's condition_id assignment.
- coverage_score(conditions, rows) where conditions is a list of dicts
  {id, description} and rows a list of dicts {row_id, condition_id} with
  condition_id None for an orphan row -> dict {"covered_conditions":
  condition ids with at least one row, in conditions input order,
  "uncovered_conditions": condition ids with no row, in conditions input
  order, "orphan_rows": row ids whose condition_id is None, in rows input
  order, "coverage": len(covered) / len(conditions), a float in [0, 1]}.
  Decision, documented: a row whose condition_id is not an id in
  conditions raises ValueError, so a typo in a row link is caught instead
  of silently degrading coverage (an analyst who means "no link" writes
  condition_id None explicitly). ValueError also on an empty conditions
  list (there is no condition table to cover); an empty rows list is
  valid and reports every condition uncovered with coverage 0.0. Rows
  with missing row_id or condition_id keys raise ValueError.
- coverage_by_severity(conditions, rows) -> dict {severity: {"covered":
  count, "uncovered": count, "coverage": covered / (covered +
  uncovered)}} over the same linkage rules; every condition must carry a
  severity field, ValueError otherwise; severities with no conditions are
  omitted; dict order follows first appearance in conditions. ValueErrors
  as in coverage_score plus the missing-severity case.
Module constants: none beyond the literals above.

Identity to test: coverage_score over the worked example equals 0.7; a
full-coverage rows set gives 1.0 and every condition covered; an empty
rows list gives 0.0 with all conditions uncovered; condition_match_score
of a text with itself is 1.0, of disjoint texts 0.0; normalize is
idempotent on its own output.

## Worked example

Ten FHA conditions FC-01..FC-10 (ids with severity: FC-01 and FC-02
catastrophic, FC-03 and FC-04 hazardous, FC-05..FC-07 major, FC-08..FC-10
minor) and 14 FMEA rows R-01..R-14: R-01 and R-02 map to FC-01, R-03 and
R-04 to FC-02, R-05 to FC-03, R-06 and R-07 to FC-04, R-08 and R-09 to
FC-05, R-10 and R-11 to FC-06, R-12 to FC-07, and R-13 and R-14 are
orphans (condition_id None):
- coverage_score: covered_conditions [FC-01, FC-02, FC-03, FC-04, FC-05,
  FC-06, FC-07], uncovered_conditions [FC-08, FC-09, FC-10], orphan_rows
  [R-13, R-14], coverage 0.7 (7 of 10 conditions demonstrated by at least
  one row; the three minor-class conditions and two rows are unlinked, so
  the FMEA does not yet close the FHA).
- coverage_by_severity: catastrophic covered 2 of 2 (coverage 1.0),
  hazardous 2 of 2 (1.0), major 3 of 3 (1.0), minor 0 of 3 (0.0).
- condition_match_score anchors (row text vs condition description):
  "loss of all pitch control authority" vs "loss of pitch control" gives
  0.666667; "flap asymmetry drives uncommanded roll" vs "uncommanded roll
  excursion" gives 0.333333; "autopilot disengages without crew
  annunciation" vs "loss of autopilot engagement" gives 0.125; identical
  texts give 1.0, disjoint texts give 0.0. normalize("Loss of
  PITCH-control, authority!") returns the tokens [loss, of, pitch,
  control, authority].
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor script
/tmp/w40spec/anchor_fmes_coverage.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- coverage_score on the worked example: coverage 0.7 exactly, covered
  list FC-01..FC-07, uncovered FC-08..FC-10, orphan rows R-13 and R-14.
- Duplicate rows for one condition count once in covered_conditions.
- Full coverage: every condition referenced gives coverage 1.0 and an
  empty uncovered list; empty rows gives coverage 0.0 with every
  condition uncovered and no orphans.
- ValueError on a row whose condition_id names an unknown condition (typo
  guard); the same row written with condition_id None is accepted as an
  orphan.
- ValueErrors: empty conditions list, missing row_id key, missing
  condition_id key.
- coverage_by_severity on the worked example: catastrophic 1.0, hazardous
  1.0, major 1.0, minor 0.0 with covered 0 and uncovered 3.
- coverage_by_severity ValueError when a condition has no severity field.
- normalize("Loss of PITCH-control, authority!") = [loss, of, pitch,
  control, authority]; normalize strips digits-adjacent punctuation and
  is idempotent.
- condition_match_score identical text 1.0, disjoint text 0.0, empty text
  pair 0.0; worked anchors 0.666667, 0.333333, 0.125 within 1e-6.
- Determinism: covered, uncovered and orphan lists preserve input order;
  dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave40-fmes-coverage-analysis.yaml)

Query 1 (copy verbatim):
  "run the fmes-coverage-analysis to compute the fmea-fha-coverage of the failure-mode rows and list every uncovered-failure-condition id"
  intent: "systems-engineering-safety; fmea-row to fha-condition coverage ratio and uncovered condition ids"
  expected_skill: "systems-engineering-safety/arp4761a/fmes-coverage-analysis"
Query 2 (copy verbatim):
  "use the fmes-coverage-analysis to flag the orphan rows and the uncovered-failure-condition entries in the fmea-fha-coverage summary"
  intent: "systems-engineering-safety; orphan row flags and uncovered conditions in the fmea-fha coverage summary"
  expected_skill: "systems-engineering-safety/arp4761a/fmes-coverage-analysis"
Task ids: w40-fmes-coverage-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must verify the coverage of the
failure-mode effect rows over the functional-hazard condition set:" and
include the outputs in the Claim. First tag: fmes-coverage-analysis.
Additional tags ONLY: fmea-fha-coverage, uncovered-failure-condition,
orphan-row-flag, condition-match-score. NEVER single generic words (fmea,
fha, fmes, coverage, condition, failure, mode, row, orphan, summary,
matrix, effect). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): criticality-number, mode-ratio,
failure-effect-probability, item-criticality, dominant-mode
(failure-mode-criticality); minimal-cut-set, cut-set-probability,
and-or-gate, severity-to-dal, dal-mapping (fta-fmea); fha-worksheet,
severity-classification, probability-target band, A-FHA, S-FHA
(functional-hazard-assessment); rpn, ordinal-rating-scale,
occurrence-rating, detection-rating (manufacturing-quality risk-
management).
