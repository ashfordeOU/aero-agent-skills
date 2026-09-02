---
name: key-characteristic-management
description: "Use when you must identify and manage key characteristics for aerospace production variation management: rate each drawing and process-history characteristic record as key or non-key against the documented decision rules, compute the 0-100 KC risk score from the weighted safety, fit/function, tight-tolerance, historical, and downstream signals, assign each KC a variation plan with control method, Cpk target (1.33 default, 1.67 safety-critical), sampling frequency, and verification gate, and decide whether tooling, process, design, supplier, or personnel changes trigger KC revalidation with the evidence needed. Produces KC verdicts with reasons, the risk-ranked KC list, the variation plan, and the revalidation decision. Trigger: key characteristic, AS9103, variation management, KC identification, critical characteristic, characteristic accountability, Cpk target, revalidation trigger."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9103
  tags: [key-characteristic-management, as9103, variation-management, kc-identification, critical-characteristic, characteristic-accountability, cpk-target, revalidation-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# Key Characteristic Management (manufacturing-quality/as9103/key-characteristic-management)

Use when you must decide which characteristics on a drawing are key
characteristics (KCs) and what variation management applies to them in
aerospace production. A key characteristic is a feature whose variation
affects fit, function, performance, or safety, so it gets a tighter control
strategy than an ordinary characteristic. This leaf opens the as9103 pack
directory under manufacturing-quality. KCs flow from design (GD&T
callouts, toleranced in millimeters) through first article inspection
(AS9102) into production variation management (AS9103 practice) and SPC.
It pairs with the delta-fai leaf for change scoping, the
first-article-inspection leaf for form 3 characteristic accountability, the
statistical-process-control leaf for the chart and capability math, and the
nonconformance-control leaf for escapes.

## Domain quick reference

- AS9103 (IAQG/SAE) frames key characteristic identification and variation
  management of aerospace production processes; name plus paraphrase only,
  the standard text is proprietary and is not reproduced here.
- Decision rule table: a characteristic is a key characteristic when any
  single rule fires: (1) safety-critical flag, (2) customer designation,
  (3) fit/function impact with a mate, seal, or performance downstream
  impact, (4) a position or profile feature at or below the 0.1 mm tight
  tolerance threshold, or (5) two or more historical failures in process
  history. The reasons list the fired rules in table order.
- Risk score weights (0-100, full set sums to 100): safety 30, fit/function
  25, tight tolerance 20, historical 15, downstream 10. The score is the
  sum of the weights whose signal fires; an override weight set may replace
  entries as long as it still sums to 100. Customer designation gates KC
  status by rule but carries no weight, so a customer-only KC ranks at 0.
- Cpk targets mirror common aerospace practice: 1.33 default, 1.67 for a
  safety-critical characteristic. This leaf assigns the target only; the
  X-bar/R chart and Cpk index math live in the statistical-process-control
  leaf.
- Control method rule table, first match wins: electrical features get 100
  percent inspection (every-unit functional test), assembly-mate features
  get attribute control (go/no-go fit gage), two or more historical
  failures escalate to 100 percent inspection, a characteristic whose
  process capability is not yet demonstrated gets a gage study first, and
  everything else runs SPC variable charts (X-bar/R).
- Revalidation trigger table: tooling, process, and design changes
  revalidate a KC (delta FAI scoped to the affected characteristic plus a
  capability re-study); supplier and personnel changes do not, because they
  route to external-provider qualification and training control unless the
  controlled process itself changes.
- Units: tolerance_mm is millimeters throughout, one unit stated.

## Workflow

1. Collect the characteristic records from the drawing callouts (GD&T
   tolerances, mm) and the process history (prior failures, known
   capability).
2. Validate the batch: classify_characteristic and the batch functions
   raise ValueError on a negative tolerance, an unknown feature type, a
   non-physical field, or an empty list.
3. Rate each record with classify_characteristic: verdict KC or non-KC
   with the fired-rule reasons.
4. Score the KCs with kc_risk_score (default weights, or pass an override
   weight set) and rank them with rank_key_characteristics.
5. Assign the variation plan with variation_management_plan: per-KC control
   method, Cpk target, sampling frequency, and verification gate.
6. For any production change, call change_trigger to decide whether the KC
   must be revalidated and what evidence is needed.
7. Produce the report lines with produce_kc_report.

## Worked example

Six characteristic records from an actuator housing drawing and process
history:

- BRG-BORE-01, bearing bore, hole, tolerance 0.025 mm, safety-critical,
  fit/function with performance downstream, capability known: KC (safety
  flag, fit/function), risk 65/100, plan SPC variable chart Xbar-R with Cpk
  target 1.67.
- HSNG-POS-02, mount hole position, position, tolerance 0.05 mm, fit with
  mate downstream, capability not yet demonstrated: KC (tight tolerance at
  or below 0.1 mm, fit/function), risk 55/100, plan gage study, Cpk target
  1.33.
- CASE-EDGE-03, cosmetic edge break, other, tolerance 0.8 mm, no flags:
  non-KC, no rule fires.
- SEAL-FACE-04, seal face flatness, flatness, tolerance 0.05 mm, fit with
  seal downstream, capability known: KC (fit/function), risk 35/100, plan
  SPC variable chart Xbar-R, Cpk target 1.33.
- GROOVE-W-05, o-ring groove width, thickness, customer-designated, no
  other flags: KC (customer designation only), risk 0/100, plan SPC
  variable chart Xbar-R, Cpk target 1.33.
- PIVOT-PIN-06, pivot pin diameter, assembly-mate, tolerance 0.02 mm, fit
  with mate downstream, three historical failures: KC (fit/function,
  historical failures), risk 50/100, plan attribute go/no-go fit gage, Cpk
  target 1.33.

The ranked KC order is BRG-BORE-01 (65), HSNG-POS-02 (55), PIVOT-PIN-06
(50), SEAL-FACE-04 (35), GROOVE-W-05 (0); the report shows 5 key
characteristics and 1 non-key. A tooling change on BRG-BORE-01 revalidates
it: delta FAI scoped to the bore plus a capability re-study, so the
contract test asserts the 1.67 target lands on the safety-critical bore.

## Verification

- Confirm classify_characteristic(bore_record) returns KC with the safety
  reason, and classify_characteristic(edge_record) returns non-KC.
- Confirm the worked-example risk scores: 65, 55, 50, 35, 0, in that rank
  order.
- Confirm variation_management_plan assigns Cpk 1.67 to the
  safety-critical bore and 1.33 elsewhere, and that the gage study lands on
  the capability-unknown position feature.
- Confirm change_trigger(bore_record, "tooling") returns verdict True with
  delta FAI and capability re-study evidence, while "supplier" and
  "personnel" return verdict False.
- Confirm a negative tolerance, an unknown feature type, an empty batch,
  and an unknown change type raise ValueError.
- Run the contract test offline: python3
  scripts/test_key_characteristic_management.py (35 tests,
  deterministic).

## Related leaves

- manufacturing-quality/as9102/delta-fai: change classification and delta
  FAI scope that a KC revalidation calls on.
- manufacturing-quality/as9102/first-article-inspection: form 3
  characteristic accountability where every KC is verified at first
  article.
- manufacturing-quality/as9100/statistical-process-control: owns the
  X-bar/R chart limits and the Cpk math; this leaf sets the target only.
- manufacturing-quality/as9100/nonconformance-control: disposition when a
  KC variation escapes control.
- cross-cutting/tolerancing/gdandt-basics: GD&T callouts and tolerance
  interpretation feeding the KC record (cross-cutting).

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_key_characteristic_management.py

The test covers the five-rule decision table (safety flag, customer
designation, fit/function with mate/seal/performance downstream, tight
position/profile tolerance boundary at 0.1 mm, historical failure
threshold), the worked-example verdicts and risk scores, the 0-100 score
with override weight sets, ranking with ties broken by id, the per-KC plan
with Cpk 1.67 for the safety-critical bore and the method rule table
(Xbar-R, gage study, attribute, 100 percent inspection), the change
revalidation rule table with evidence, the report content contract, and
ValueError rejection of negative tolerance, unknown feature type, empty
batches, duplicate ids, non-physical fields, and invalid weights.

## Compliance

- Standards referenced, not reproduced: AS9103 is named for context but is
  not yet in standards-map.yaml, so the frontmatter standards id is the
  parent QMS standard AS9100 (production process control frame). AS9103
  wording and tables are not reproduced.
- compliance: STANDARDS-REF, gated: false.
