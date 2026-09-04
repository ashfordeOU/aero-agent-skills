# Wave-36 leaf spec: ica-cmr-ali-classification (systems-engineering-safety, continued-airworthiness pack)

- Path: skills/systems-engineering-safety/continued-airworthiness/ica-cmr-ali-classification/
- Pack: continued-airworthiness. Closest siblings: in-service-safety-
  assessment (field event rates vs predicted, AD/SB route), msg3-
  maintenance-analysis (derives routine scheduled task sets from
  visibility/consequence), mmel-development (dispatch relief),
  arp4754a/configuration-management (change control). Whole-tree grep:
  word-boundary CMR / ALI / ICA / ALS / airworthiness-limitation /
  life-limited / 25.1529 / 25.981 have ZERO owning hits (only substring
  noise "totALS"/"terminALS"); the family router fence table does not
  list ICA/CMR/ALI. ZERO owners. FIRST genuine SES gap in seven waves
  (waves 30-36).
- Standards id: far-25 (reference-only; 25.1529 ICA/airworthiness
  limitations + 25.981 fuel-tank flammability context; MSG-3 named as
  routine-program context). Ledger Standard: far-25.
- Family: systems-engineering-safety

## Claim

Classify candidate maintenance and limitation items from certification
into ALI (airworthiness limitation items: life-limited parts, damage-
tolerance inspections, fuel-tank flammability checks, mandatory and
published in the Airworthiness Limitations Section of the ICA), CMR
(certification maintenance requirements, mandatory and authority-
controlled), or routine scheduled maintenance (MSG-3 driven,
non-mandatory), using a fixed certification-driver rule table; then
compute the ALS coverage of the submitted maintenance program (matched
required ALS items divided by the total required) and per-item interval
compliance against the type-certificate ALS maximum intervals. Produces
a per-item verdict and rationale, class counts, ALS coverage fraction,
and the non-compliant and missing ALS item lists.

Does NOT do: field-rate vs predicted-rate safety assessment and AD/SB
routing (in-service-safety-assessment); deriving the routine MSG-3 task
set from visibility/consequence (msg3-maintenance-analysis); dispatch
relief decisions (mmel-development); configuration change control
(configuration-management).

## Model (implement exactly)

Module constants:
- ALLOWED_DRIVERS = ("LLP", "DT", "FF", "CMR", "ROUTINE"): life-limited
  part, damage-tolerance inspection, fuel-tank flammability check,
  certification maintenance requirement, routine task.
- ALI_DRIVERS = ("LLP", "DT", "FF") (certification drivers that make an
  item a mandatory ALI).
- ALS_MAX_INTERVALS = {"APU shaft LLP": 20000.0 (flight cycles),
  "wing spar DT inspection": 4000.0 (flight cycles),
  "fuel-tank flammability check": 12000.0 (flight hours)} (type-
  certificate ALS maxima for the anchor program; intervals in the item's
  own unit, flight cycles or flight hours as labeled).

Conventions: an item is a tuple (name, driver, interval). Classification
rule: driver in ALI_DRIVERS -> ALI; driver == "CMR" -> CMR; driver ==
"ROUTINE" -> routine. ALS coverage = number of the ALS_MAX_INTERVALS
canonical items present in the program divided by the total canonical
count. Interval compliance applies only to ALS-classified items that are
canonical: compliant when program interval <= ALS maximum.

Functions (pure stdlib):
- classify_item(name, driver, interval) -> dict {name, driver, kind,
  rationale} with kind ALI/CMR/routine. ValueErrors: unknown driver
  (not in ALLOWED_DRIVERS); interval <= 0.
- als_coverage(items) -> dict {matched, required, coverage_fraction}
  where required = len(ALS_MAX_INTERVALS). ValueError on empty list.
- interval_compliance(name, interval) -> dict {name, max_interval,
  compliant} for the canonical ALS item names; ValueError for a name not
  in ALS_MAX_INTERVALS or interval <= 0.
- ica_cmr_ali_review(items) -> dict {per_item: [classify dicts],
  class_counts: {ALI: n, CMR: n, routine: n}, coverage: dict,
  non_compliant: [names], missing_als_items: [canonical names not in the
  program]}.

Identity to test: coverage fraction = matched/required exactly; class
counts sum to the number of items; an LLP item with interval under its
ALS max is compliant and one over is not.

## Worked example

Reference program items (name, driver, interval):
- ("APU shaft LLP", "LLP", 18000)
- ("wing spar DT inspection", "DT", 4500)
- ("cabin interior check", "ROUTINE", 2000)
- ("hydraulic pump CMR", "CMR", 3000)

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- classify: APU shaft LLP -> ALI; wing spar DT -> ALI; cabin interior ->
  routine; hydraulic pump CMR -> CMR.
- class_counts: ALI 2, CMR 1, routine 1.
- ALS coverage: matched 2 of 3 canonical items -> 0.6667.
- interval compliance: APU 18000 <= 20000 COMPLIANT; wing spar DT 4500
  > 4000 NON-COMPLIANT (missing: fuel-tank flammability check).
- non_compliant = ["wing spar DT inspection"]; missing_als_items =
  ["fuel-tank flammability check"].

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: unknown driver (e.g. "MSG3"); interval <= 0 (e.g. -5);
  empty items in coverage.
- Classification truth table: each driver -> expected kind.
- Coverage 0.6667 within 1e-4; class counts (2,1,1).
- Compliance: compliant and non-compliant cases; non-canonical name
  raises.
- Identity: counts sum to item count; coverage = matched/required.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-ica-cmr-ali-classification.yaml)

Query 1 (copy verbatim):
  "classify certification maintenance items into airworthiness limitation items and cmr items for the airworthiness limitations section"
  intent: "systems-engineering-safety; ALI/CMR/routine classification by certification driver"
  expected_skill: "systems-engineering-safety/continued-airworthiness/ica-cmr-ali-classification"
Query 2 (copy verbatim):
  "check the maintenance program als coverage and interval compliance against the type certificate airworthiness limitations"
  intent: "systems-engineering-safety; ALS coverage and interval compliance review"
  expected_skill: "systems-engineering-safety/continued-airworthiness/ica-cmr-ali-classification"
Task ids: w36-ica-cmr-ali-classification-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must classify certification
maintenance items:" and include the outputs in the Claim. First tag:
ica-cmr-ali-classification. Additional tags ONLY: airworthiness-
limitation-items, certification-maintenance-requirements, als-coverage,
life-limited-part-review, instructions-for-continued-airworthiness.
NEVER single generic words (maintenance, certification, airworthiness,
limitation, inspection, interval, item, task). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): field event rate, service
difficulty report, AD/SB (in-service-safety-assessment); MSG-3 task
derivation, visibility, consequence (msg3-maintenance-analysis);
dispatch relief, MEL (mmel-development); change request, impact
analysis (configuration-management).
