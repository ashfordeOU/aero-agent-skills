# Wave-37 leaf spec: acceptance-sampling (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/acceptance-sampling/
- Pack: as9100. Closest siblings: statistical-process-control (monitors
  an in-control process with control charts - not lot acceptance),
  quality (QMS overview), key-characteristic-management (KC selection and
  control, not sampling plans), nonconformance-control (disposition of
  rejected lots), first-article-inspection (FAI of the first article, not
  lot sampling). Whole-tree grep: "acceptance sampling", "AQL",
  "sampling plan" have ZERO owning hits. ZERO owners. GENUINE MQ gap
  (fresh probe).
- Standards id: as9100 (reference-only; product acceptance context).
  The body names ANSI/ASQ Z1.4 style attribute sampling by name only,
  no verbatim tables. Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Design and evaluate an attribute acceptance-sampling plan for incoming
or final lots: choose the sample size code letter from the lot size and
inspection level, look up the single-sampling plan (sample size n,
accept number Ac, reject number Re) for the required AQL from a small
embedded reference table, decide accept or reject from the number of
nonconforming units found, and compute the operating-characteristic
probability of acceptance across incoming fraction nonconforming with
the binomial model. Produces the code letter, sample size, accept and
reject numbers, the lot verdict, and the OC curve points that quantify
the plan's discrimination. Does NOT do: control-chart monitoring of a
process over time (statistical-process-control); FAI of the first
article (first-article-inspection); disposition of a rejected lot
(nonconformance-control); measurement-system studies
(measurement-systems-analysis).

## Model (implement exactly)

Module constants:
- INSPECTION_LEVELS = ("I", "II", "III")
- CODE_LETTER_TABLE = {("II", "small"): "F", ("II", "medium"): "H",
  ("II", "large"): "J", ("II", "very-large"): "L", ("I", "medium"):
  "F", ("III", "medium"): "K"} (documented reduced table; lot-size
  bands: small 51-90, medium 281-500, large 1201-3200, very-large
  10001-35000 - anchor plan uses medium/II)
- PLAN_TABLE = {("J", "1.0"): (80, 2, 3), ("H", "1.0"): (50, 1, 2),
  ("L", "1.0"): (200, 5, 6)} keyed (code_letter, aql_string) ->
  (n, Ac, Re) with Re == Ac + 1 (single sampling).

Functions (pure stdlib):
- code_letter(lot_size, inspection_level) -> str: band lookup from the
  documented bands; ValueError on lot_size <= 0 or unknown level.
- sampling_plan(code_letter, aql) -> (n, Ac, Re): lookup in PLAN_TABLE;
  ValueError when the (code, aql) pair is not in the embedded table.
- lot_decision(nonconforming_found, plan) -> "accept" if
  nonconforming_found <= Ac else "reject". ValueErrors: negative count.
- oc_acceptance_probability(n, ac, p) -> float:
  sum_{d=0..ac} C(n, d) p^d (1-p)^(n-d) (math.comb).
- oc_curve(n, ac, p_values) -> [ (p, prob), ... ] for the input list.
  ValueErrors: p outside [0, 1].

Identity to test: lot_decision accepts exactly at Ac and rejects at
Ac + 1; oc at p=0 is 1.0; oc at p=1 is 0 when Ac < n.

## Worked example

Lot size 500 (medium band), level II: code letter J; AQL 1.0 -> plan
(80, 2, 3). A sample of 80 yields 1 nonconforming unit -> accept; 3
nonconforming -> reject. OC anchors (independently verified at prep):
oc(80, 2, 0.01) = 0.9534; oc(80, 2, 0.04) = 0.3748.
Run your module and take the real outputs as assert targets.

## Validation list (contract test must include)

- ValueError: lot_size <= 0; unknown inspection level; unknown (code,
  aql) pair; p outside [0,1]; negative nonconforming count.
- Code letter truth table across the bands.
- Decision truth table: Ac accepts, Ac+1 rejects.
- OC anchors 0.9534 and 0.3748 within 1e-3.
- Identity: oc(p=0) = 1.0; oc(p=1) = 0 for Ac < n.
- Determinism.

## Corpus fragment (eval/hit1-wave37-acceptance-sampling.yaml)

Query 1 (copy verbatim):
  "select an attribute acceptance-sampling plan with the lot size code letter and aql accept and reject numbers"
  intent: "manufacturing-quality; attribute acceptance sampling plan selection"
  expected_skill: "manufacturing-quality/as9100/acceptance-sampling"
Query 2 (copy verbatim):
  "evaluate the acceptance-sampling operating characteristic curve probability of acceptance for the sampling plan"
  intent: "manufacturing-quality; acceptance sampling OC curve"
  expected_skill: "manufacturing-quality/as9100/acceptance-sampling"
Task ids: w37-acceptance-sampling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design an attribute acceptance
sampling plan:" and include the outputs in the Claim. First tag:
acceptance-sampling. Additional tags ONLY: attribute-sampling-plan,
aql-acceptance-quality-limit, lot-size-code-letter, operating-
characteristic-curve, accept-reject-numbers. NEVER single generic words
(sampling, inspection, quality, lot, accept, reject). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): control chart, in-control
process (statistical-process-control); first article (first-article-
inspection); disposition, MRB (nonconformance-control); key
characteristic (key-characteristic-management); gage, GRR
(measurement-systems-analysis).
