# Wave-37 leaf spec: type-certificate-data-sheet (systems-engineering-safety, continued-airworthiness pack)

- Path: skills/systems-engineering-safety/continued-airworthiness/type-certificate-data-sheet/
- Pack: continued-airworthiness. Closest siblings: certification-basis
  (selects the APPLICABLE regulations and the certification path - it does
  not compile or validate the data-sheet artifact), means-of-compliance
  (finding types per regulation), ica-cmr-ali-classification (reads TC
  ALS maxima as an input), in-service-safety-assessment (field rates),
  mmel-development (dispatch relief). Whole-tree grep: "type certificate
  data sheet", "TCDS", "type certificate data" have ZERO owning hits.
  ZERO owners. GENUINE gap in the CEO-named airworthiness-management
  vein.
- Standards id: far-25 (reference-only; the TCDS records the Part 25
  certification basis, weights and operating limitations for transport
  products; the leaf also handles legacy Part 23 category rules as data).
  Ledger Standard: far-25.
- Family: systems-engineering-safety

## Claim

Compile and validate a type-certificate-data-sheet style type design
record for a civil product: check that every required section is present
(models, type design, approved engines and propellers, weights,
certification basis, operating limitations, noise standards), validate
the weight block consistency (max ramp at or above max takeoff, max
landing at or below max takeoff, all positive), validate the category
airspeed limitations (transport requires VMO or MMO; normal, utility and
acrobatic categories require VNE), check the approved configuration
consistency, and diff two revisions of the record into a per-section
change summary for type certificate amendment or STC integration
review. Produces the missing-section list, the validation error list,
the summary counts, and the revision change report.

Does NOT do: selecting the applicable regulations or certification path
(certification-basis); compliance finding strategy (means-of-compliance);
ALS/CMR classification (ica-cmr-ali-classification); field event rate
assessment (in-service-safety-assessment).

## Model (implement exactly)

Module constants:
- REQUIRED_SECTIONS = ("models", "type_design", "engine_models",
  "propeller_models", "weights", "certification_basis",
  "operating_limitations", "noise_standards")
- CATEGORY_AIRSPEED_KEYS = {"transport": ("vmo", "mmo"), "normal":
  ("vne",), "utility": ("vne",), "acrobatic": ("vne",)}
  (any one listed key present and > 0 satisfies the category rule)

A record is a dict with a "category" key in the map and the section keys
above (weights is a dict with max_ramp, max_takeoff, max_landing;
operating_limitations is a dict of named limits; models/engine_models/
propeller_models are non-empty lists).

Functions (pure stdlib):
- missing_sections(record) -> [str]: REQUIRED_SECTIONS keys absent from
  the record.
- weight_errors(record) -> [str]: empty/missing weight keys, non-positive
  weights, max_ramp < max_takeoff, max_landing > max_takeoff.
- airspeed_errors(record) -> [str]: unknown category; category keys from
  CATEGORY_AIRSPEED_KEYS all absent or non-positive.
- approved_config_errors(record) -> [str]: engine_models or
  propeller_models empty (a TCDS lists the approved engine and propeller
  models); any model listed in operating_limitations engine references
  not in engine_models (skip if the record has no such reference).
- validate_tcds(record) -> dict {missing_sections: [...],
  weight_errors: [...], airspeed_errors: [...], config_errors: [...],
  valid: bool} (valid = all lists empty).
- tcds_summary(record) -> dict {models: n, engine_models: n,
  propeller_models: n, max_takeoff_weight: float, airspeed_limits:
  [key=value sorted]}.
- tcds_revision_diff(old, new) -> dict: per section key one of
  "unchanged" | "added" | "removed" | "modified"; for models lists,
  models_added / models_removed; for weights, weight deltas
  {max_takeoff_delta, ...}.

Identity to test: valid == all four error lists empty; a diff of a
record with itself is all "unchanged"; models_added and models_removed
are disjoint.

## Worked example

Record A: category "transport", models ["T-100"], type_design "T-100
basic", engine_models ["E-1", "E-2"], propeller_models ["P-1"], weights
{max_ramp 80000, max_takeoff 79000, max_landing 70000} (kg),
certification_basis ["far-25"], operating_limitations {vmo 340 (ktas),
mmo 0.84}, noise_standards ["far-36"].
- missing_sections(A) == []; weight_errors(A) == []; airspeed_errors(A)
  == [] (transport satisfied by vmo); config_errors(A) == [].
- validate_tcds(A) valid True.
- Record B: category "normal", weights {max_ramp 75000, max_takeoff
  79000, max_landing 70000}, operating_limitations {} ->
  airspeed_errors(B) = ["missing vne for category normal"],
  weight_errors(B) = ["max_ramp below max_takeoff"].
- tcds_revision_diff(A, A2) where A2 adds model "T-101" and changes
  max_takeoff to 79400: models status "modified", models_added
  ["T-101"], max_takeoff_delta 400.0.
Run your module and take the real outputs as assert targets; the error
texts above are magnitude anchors (assert the error LISTS and valid
flags; bound-check exact wording loosely or match your own deterministic
messages - your module output is the test target).

## Validation list (contract test must include)

- missing_sections on a record missing propeller_models and
  noise_standards lists exactly those two.
- weight rule: ramp below takeoff flagged; landing above takeoff
  flagged; non-positive flagged.
- airspeed rule truth table across the four categories; unknown category
  flagged.
- Revision diff: added model, removed model, weight delta, unchanged
  identical record.
- Identity: valid flag == (all error lists empty); summary counts match
  list lengths.
- Determinism; ValueError on a record without a "category" key or with a
  weights section that is not a dict.

## Corpus fragment (eval/hit1-wave37-type-certificate-data-sheet.yaml)

Query 1 (copy verbatim):
  "compile a type-certificate-data-sheet record with the models weights certification basis and operating limitations sections"
  intent: "systems-engineering-safety; TCDS record compilation and required sections"
  expected_skill: "systems-engineering-safety/continued-airworthiness/type-certificate-data-sheet"
Query 2 (copy verbatim):
  "validate the type-certificate-data-sheet weight block and category airspeed limits for the approved type design"
  intent: "systems-engineering-safety; TCDS validation checks and revision diff"
  expected_skill: "systems-engineering-safety/continued-airworthiness/type-certificate-data-sheet"
Task ids: w37-type-certificate-data-sheet-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compile and validate a type
certificate data sheet:" and include the outputs in the Claim. First
tag: type-certificate-data-sheet. Additional tags ONLY: tcds-validation,
type-design-record, approved-model-list, category-airspeed-limits,
tcds-revision-diff. NEVER single generic words (data, sheet, record,
models, weights, limits, certification). 50-150 words, <=1000 chars, no
em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): applicable regulations,
certification path, special conditions (certification-basis); compliance
finding, means of compliance (means-of-compliance); ALS coverage, CMR
(ica-cmr-ali-classification); field event rate (in-service-safety-
assessment); dispatch relief, MEL (mmel-development).
