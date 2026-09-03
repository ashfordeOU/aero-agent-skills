# Wave-28 leaf spec: fod-control (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/fod-control/
- Pack: as9100 (existing siblings: quality, nonconformance-control,
  supplier-control, counterfeit-prevention, calibration-control,
  corrective-action, document-control, statistical-process-control,
  risk-management, measurement-systems-analysis)
- Standards ids: as9100  (Ledger Standard: as9100)
- Family: manufacturing-quality

## Claim

Build and audit a foreign object debris (FOD) prevention program for
aerospace production: classify the FOD zone from the part criticality
and the debris-generation exposure of the work area, compute the FOD
risk score, derive the required FOD sweep interval and the tool-control
and housekeeping controls for the zone, reconcile the issued and
returned tool counts, and score the program against the required
control set to produce the audit verdict with findings. Produces the
zone class, the risk score, the sweep interval, the tool-control
reconciliation result, the control completeness, and the pass or fail
verdict that gate the FOD prevention assessment.

Does NOT do: score counterfeit parts risk from sourcing and
verification (counterfeit-prevention owns the parts-provenance
program); run an FMEA risk priority number (risk-management owns
AS9100D operational-risk RPN); map audit focus areas to AS9100 clauses
(quality owns clause scoping). This leaf owns the FOD program
(debris/foreign-object controls in the production environment).

## Model (implement exactly)

Module constants:
- ZONE_CUTS = [(14, "A"), (10, "B")]; below 10 -> "C".
- SWEEP_INTERVAL_H = {"A": 8, "B": 40, "C": 160} (documented typical
  cadence; body must label it a program policy input example).
- CONTROL_SET = {
    "A": ["tool-control", "count-reconcile", "sweep-log",
          "tethering", "fod-mats", "training"],
    "B": ["tool-control", "count-reconcile", "sweep-log", "fod-mats"],
    "C": ["tool-control", "sweep-log"]}

Inputs:
- part_criticality (int 1-3: 3 flight-control or propulsion critical,
  2 structural, 1 non-flight),
- debris_exposure (int 1-3: 3 machining or cutting, 2 assembly with
  fasteners and rework, 1 inspection or bench work),
- open_cavity_exposure (int 0-2: 2 open fuel tank or engine inlet
  cavity, 1 open assembly, 0 enclosed),
- issued_tools (dict {tool_name: qty}),
- returned_tools (dict {tool_name: qty}),
- controls_present (list of strings from the CONTROL_SET vocabulary).

Functions:
- risk_score(part_criticality, debris_exposure, open_cavity_exposure)
  -> int: 3*criticality + 2*debris + 2*open_cavity. ValueError on any
  input outside its stated band.
- zone_class(score) -> str: "A" if score >= 14, "B" if score >= 10,
  else "C".
- sweep_interval_h(zone) -> int: SWEEP_INTERVAL_H[zone].
- required_controls(zone) -> list: CONTROL_SET[zone].
- reconcile_tools(issued, returned) -> dict: missing = {name: qty for
  name, qty in issued.items() if returned.get(name, 0) < qty} with the
  shortfall as the value; reconciled = not missing; return {missing,
  reconciled}. Ignore tools in returned that were not issued.
- program_audit(inputs) -> dict: zone, score, sweep interval,
  required = required_controls(zone), present = [c for c in required
  if c in controls_present], missing_controls = [c for c in required
  if c not in controls_present], reconciliation = reconcile_tools(...),
  completeness = len(present)/len(required),
  verdict = "fod-pass" if completeness == 1.0 and reconciled else
  "fod-fail"; findings = missing_controls + (["missing-tool"] if not
  reconciled else []).
ValueError on: issued with negative qty, returned with negative qty,
controls_present with an unknown control name.

## Worked example

Engine module assembly line: criticality 3, debris 3 (machining
adjacent), open cavity 2 (engine inlet open): score = 3*3 + 2*3 + 2*2
= 9 + 6 + 4 = 19 -> zone A; sweep interval 8 h; required controls the
six-item A set.
- reconcile: issued {"torque-wrench-1": 1, "drill-7": 2}, returned
  {"torque-wrench-1": 1} -> missing {"drill-7": 2}, reconciled False.
- audit with controls_present ["tool-control", "count-reconcile",
  "sweep-log", "fod-mats", "training"] (no tethering): completeness
  5/6 = 0.8333; findings ["tethering", "missing-tool"]; verdict
  "fod-fail". Assert all fields.
- Clean case: controls_present all six and full reconciliation ->
  completeness 1.0, findings [], verdict "fod-pass".
- Zone B case: criticality 2, debris 2, open 1 -> score 6 + 4 + 2 =
  12 -> zone B; required four-item set; sweep 40 h.
- Zone C case: 1/1/0 -> score 3 + 2 + 0 = 5 -> zone C, required two
  items, sweep 160 h.
- ValueErrors on criticality 4, debris 0, open -1, negative tool qty,
  unknown control "laser-guard".
Keep at least 16 test methods: score values, zone boundaries (14, 13,
10, 9), sweep intervals, required sets per zone, reconciliation exact
and partial and extra-return cases, audit pass/fail, completeness
values, findings contents, ValueErrors.

## Corpus tasks (ids w28-fod-control-1/2)

Distinctive tokens: FOD prevention, foreign object debris, FOD zone
classification, tool control count, FOD sweep interval, FOD audit.
Avoid: counterfeit parts, sourcing verification (counterfeit-
prevention); FMEA RPN, operational risk (risk-management); audit
clause mapping (quality).

1. "audit the FOD prevention program for the engine assembly line:
   classify the FOD zone from the part criticality and debris exposure,
   and reconcile the issued tool count"
2. "set the foreign object debris controls for the machining area:
   compute the risk score, pick the FOD sweep interval, and check the
   required tool control measures"

## SKILL body notes

Pair with counterfeit-prevention (the other program-level scoring
sibling in the pack) and risk-management (RPN scoring differs from the
FOD score). Zone cuts, sweep cadence, and the control sets are
documented example policy values, not AS9100 clause text; the body must
say the program parameters are user policy inputs. AS9100 cited
reference-only.
