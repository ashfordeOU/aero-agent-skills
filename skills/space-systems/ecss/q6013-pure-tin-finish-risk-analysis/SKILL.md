---
name: q6013-pure-tin-finish-risk-analysis
description: "Assess the whisker risk of a pure tin termination and derive the controls it needs under ECSS-Q-ST-60-13C clause 9.2: decide from the lead content by mass whether a tin finish counts as pure tin at all, bound the whisker length reachable over the mission from the finish type, underplate, substrate, plating thickness and any conformal coat, divide the minimum conductor spacing by that bound for a bridging margin, double the margin required where the circuit could strike and hold a metal vapour arc, place the outcome in a risk category judged at the boundary under a named tolerance, and name the refinish, barrier, coating, spacing and current-limit controls it demands. Use when a part carries pure tin terminations. Trigger: ecss, q-st-60-13c-clause-9-2, pure-tin-termination-whisker-risk, tin-whisker-bridging-margin, nickel-underplate-whisker-barrier, whisker-mitigation-control-selection."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-pure-tin-finish-risk-analysis, q-st-60-13c-clause-9-2, pure-tin-termination-whisker-risk, tin-whisker-bridging-margin, nickel-underplate-whisker-barrier, matte-tin-refinish-control, metal-vapour-arc-sustaining-circuit, whisker-mitigation-control-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Pure Tin Finish Risk Analysis (space-systems/ecss/q6013-pure-tin-finish-risk-analysis)

Use when the task is the pure tin provision of ECSS-Q-ST-60-13C clause 9.2 —
a commercial electrical, electronic and electromechanical part whose
terminations are plated in tin with little or no lead, the whiskers that
finish can grow over a mission, and what the design has to do about them.

## Domain quick reference

- The provision only bites on pure tin, and pure tin is a composition
  question with a numeric answer. Lead content by mass decides it; a finish
  carrying enough lead is outside the provision entirely and gets no controls
  from it.
- A whisker is a growth, not a defect rate. It appears on a finish that
  passed every test, years after delivery, which is why the assessment is
  made against the mission duration rather than against incoming inspection.
- Risk is a geometry question. What matters is not how long a whisker gets
  but whether it reaches the next conductor, so the length bound is only half
  the calculation and the minimum spacing is the other half.
- The bound is built from named multiplicative factors — deposit type,
  barrier underplate, the substrate under the plating, the plating thickness
  and any conformal coat. Every factor is separately arguable, and the
  product is reproducible wherever it is evaluated.
- Bright tin over brass with thin plating and no barrier is the worst case
  the model can express, and it is also the cheapest commercial part on the
  catalogue page. The two facts are related.
- A bridge that can strike and hold a metal vapour arc does not clear itself,
  so a circuit with the voltage and the current to sustain one has to hold
  more clearance than a circuit that would simply blow the whisker away.
- Controls are ordered, not alternatives. A declared-component-list entry
  records the risk, a barrier and a refinish reduce the growth, a coat and
  spacing reduce the bridging, and only rework takes the part out of pure tin
  altogether.

## Workflow

1. Validate the part: the termination finish, the circuit around it and the
   mission duration the assessment covers.
2. Decide from the lead content by mass whether the finish counts as pure
   tin; stop and report not-applicable when it does not.
3. Bound the whisker length over the mission from the finish, underplate,
   substrate, plating thickness and coating factors.
4. Divide the minimum conductor spacing by that bound to get the bridging
   margin, in whisker lengths of clearance.
5. Set the margin required: the base value, doubled where the circuit could
   sustain a metal vapour arc once a bridge forms.
6. Place the outcome in a risk category from the ratio of the two, judged at
   each boundary under a named tolerance, and name the controls that follow
   with every finding behind them.

## Pitfalls

- Treating lead-free as a yes or no label off a datasheet. The threshold is a
  mass fraction, and a finish just under it is inside the provision while one
  just over it is not.
- Bounding the whisker and stopping. A 300 micrometre whisker is harmless at
  a millimetre of spacing and fatal at 200 micrometres; only the ratio is a
  result.
- Treating a conformal coat as a cure. It reduces bridging, it does not stop
  growth, and a whisker can still penetrate a thin or badly covered coat.
- Ignoring what the circuit does after a bridge. Low-energy circuits often
  clear a whisker; a circuit that can hold an arc turns a momentary short
  into a permanent one.
- Assessing at delivery rather than at end of life. The growth is slow, so
  the shorter the horizon assumed the safer every part looks.
- Reporting a risk with no controls, or controls with no risk. The category
  and the control list are produced together so the two cannot drift apart.

## Behavior contract (gate 3)

The pure tin composition decision, finish and circuit validation, the
thickness band factor, the multiplicative whisker length bound, the bridging
margin, the arc-sustaining margin uplift, the boundary-tolerant risk category
and the derived control list are exercised by the gate 3 contract test:
scripts/test_q6013_pure_tin_finish_risk_analysis.py against
scripts/q6013_pure_tin_finish_risk_analysis_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q6013_pure_tin_finish_risk_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
