---
name: q7036-heat-treatment-state-control
description: "Verify that the temper or heat-treatment state governing stress-corrosion-cracking resistance is the one actually delivered, per ECSS-Q-ST-70-36C. Use when a drawing calls an overaged or tempered-back condition and only a conductivity or hardness reading evidences what arrived: read the resistance rating the specified state carries, grade the reading against that state's acceptance window with both edges inclusive, and when it falls outside, search the same alloy's other registered states for the window it does fall in so a temper substitution is named with the rating it costs rather than reported as a bare out-of-limit. Trigger: ecss, q-st-70-36c, scc-temper-state-control, overaged-temper-verification, scc-conductivity-acceptance-window, temper-substitution-detection, scc-hardness-window."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-heat-treatment-state-control, scc-temper-state-control, overaged-temper-verification, scc-conductivity-acceptance-window, temper-substitution-detection, scc-hardness-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Heat-Treatment State Control (space-systems/ecss/q7036-heat-treatment-state-control)

Use when the task is the selection step of ECSS-Q-ST-70-36C that ties
stress-corrosion-cracking resistance to the temper or heat-treatment
condition of the alloy, and then has to establish that the condition on
the drawing is the condition in the hardware.

## Domain quick reference

- Resistance belongs to the state, not the alloy. The peak-aged temper
  of a high-strength aluminium carries the lowest rating of its family
  and the fully overaged temper of the same alloy carries the highest;
  the same split runs through the quench-and-tempered steels and the
  precipitation-hardened stainless grades. Naming the alloy without the
  temper names nothing the clause can act on.
- Overaging buys resistance with strength. That trade is the reason a
  substitution back towards the peak-aged condition is attractive on the
  shop floor and disastrous for the control, which is why the state is
  verified rather than assumed from the certificate.
- The verification property is state-dependent: electrical conductivity
  for the age-hardened aluminium tempers, hardness for the tempered
  steels and the precipitation-hardened grades. Each registered state
  carries an acceptance window in the units of its own property, and the
  windows of one alloy do not overlap, so a reading identifies a state.
- An out-of-window reading is rarely random. It usually sits squarely
  inside the window of a neighbouring temper of the same alloy, and
  saying which one -- and what rating that delivered state carries --
  is what turns an inspection number into an actionable finding.
- Window edges belong to the window. A reading an inspector records
  exactly on the edge is accepted, and the equality is resolved by a
  named tolerance rather than by widening the edge for everyone.

## Workflow

1. Normalize the declared alloy and temper, accepting the stress-relief
   and procurement suffixes that do not change the aged condition, and
   refuse a state the registry does not hold.
2. Read the resistance rating, the verification property and the
   acceptance window that the specified state carries.
3. Grade the reading against that window inclusively at both ends,
   resolving an intended exact equality with the named tolerance.
4. On a reading inside the window, disposition the state as evidenced.
5. On a reading outside it, search the other registered states of the
   same alloy for one whose window contains the reading. A hit is a
   temper substitution: report it with the rating of the delivered state
   against the rating of the specified one.
6. A reading that matches no registered state of the alloy is reported
   as out of window in its own right -- the treatment, the measurement
   or the material identity is wrong, and none of the three may be
   silently chosen for the reviewer.
7. Aggregate a list into evidenced, substituted and out-of-window
   counts, refusing a duplicate identifier.

## Pitfalls

- Accepting the certificate as the state. The certificate records what
  was ordered; the conductivity or hardness reading records what was
  delivered, and the whole control rests on the second.
- Reporting an out-of-window reading without naming the temper it
  matches. "Out of limits" sends the part back for re-inspection; "this
  reads as the peak-aged temper, which is rated susceptible" sends it
  back for re-treatment or rejection.
- Quoting a family rating for a part in a different condition. It moves
  the alloy a full grade in the selection that follows and nothing
  downstream can detect the substitution.
- Comparing a hardness reading against a conductivity window, or the
  reverse. The numbers are in similar ranges for some of these states,
  so the mix-up passes a plausibility glance and grades the state on the
  wrong property entirely.
- Nudging a window edge to admit a borderline reading. That relaxes the
  acceptance for every future part; the boundary equality is a
  representation question and is handled inside the comparison.

## Behavior contract (gate 3)

The state normalization, the registry lookup and its error paths, the
inclusive window grading, the same-alloy substitution search and the
population aggregation are exercised by the gate 3 contract test:
scripts/test_q7036_heat_treatment_state_control.py against
scripts/q7036_heat_treatment_state_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7036_heat_treatment_state_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
