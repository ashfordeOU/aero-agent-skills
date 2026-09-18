---
name: q7036-scc-criticality-identification
description: "Identify the stress-corrosion-cracking-critical applications in a hardware set under ECSS-Q-ST-70-36C. Use when sustained loads, alloy states and service environments have to be read together to decide which items the SCC controls actually bind: test whether a susceptible alloy state, a sustained tensile stress held past the transient boundary, and a cracking-promoting environment coexist, clear an application on the one condition that is absent and name it so a later change re-opens the question, then grade what remains on failure consequence and load-path redundancy and return the actions each grade owes. Trigger: ecss, q-st-70-36c, scc-critical-application, scc-three-condition-coexistence, sustained-tensile-stress-duration, scc-load-path-redundancy, scc-criticality-grade."
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
  tags: [ecss, q-st-70-materials-scope, q-st-70-36c, q7036-scc-criticality-identification, scc-critical-application, scc-three-condition-coexistence, sustained-tensile-stress-duration, scc-load-path-redundancy, scc-criticality-grade]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Materials — SCC Criticality Identification (space-systems/ecss/q7036-scc-criticality-identification)

Use when the task is the framework step of ECSS-Q-ST-70-36C that picks
out the stress-corrosion-cracking-critical applications from a hardware
set -- the items whose alloy, sustained load and environment together
put them inside the control, before any alloy substitution or stress
reduction is proposed.

## Domain quick reference

- Cracking needs three things at once: an alloy state that is not rated
  resistant, a tensile stress that is sustained rather than transient,
  and an environment able to promote the mechanism. Remove any one and
  the application is not SCC critical -- which is why the absent
  condition is the thing to record, not the conclusion.
- "Sustained" is a duration statement, not a load-case label. A launch
  transient at high stress is not the driver; a modest assembly stress
  locked in for months of storage is. Below a stated fraction of the
  yield strength the stress is not treated as a driver on its own
  either, so both a magnitude floor and a duration floor apply.
- The alloy condition is read from the resistance rating of the state as
  procured, not from the alloy designation. A medium-rated state counts
  towards coexistence; only a state rated resistant takes the condition
  off the table.
- Coexistence makes an application a candidate; consequence decides its
  grade. A crack in a single-load-path item whose failure is
  catastrophic is what the control exists for. The same three conditions
  on a redundant or minor-consequence item are real, but they are
  graded for monitoring rather than for design action.
- A stress ratio is a fraction of yield. A number that arrives above
  about one and a half is almost always a stress in megapascals that has
  been passed into the ratio slot, and it is refused rather than
  silently normalized.

## Workflow

1. Normalize the resistance rating, the environment severity and the
   failure consequence onto their canonical tokens, accepting the usual
   synonyms and refusing anything that maps to none of them.
2. Test the alloy condition: a state rated medium or low counts, a state
   rated resistant does not.
3. Test the stress condition against both boundaries -- the fraction of
   yield and the sustained duration -- inclusively, resolving an
   intended exact equality with a named tolerance rather than by moving
   the boundary.
4. Test the environment condition: a moderate or severe environment
   counts, a benign one does not.
5. If any condition is absent, grade the application cleared and record
   which one carried the decision.
6. If all three coexist, grade on consequence and redundancy: a
   catastrophic single-load-path item is SCC critical; everything else
   is monitored.
7. Attach the actions the grade owes, then aggregate the set into
   critical, monitored and cleared counts with a finding per critical
   item, refusing a duplicate application identifier.

## Pitfalls

- Concluding "not critical" without naming the condition that carried
  it. A stress reduction that is later given back, or a storage
  environment that turns out to be uncontrolled, silently reinstates the
  criticality nobody is watching for.
- Reading a peak transient as a sustained stress. The magnitude looks
  alarming and the duration makes it irrelevant; feeding it in grades
  benign hardware as critical and buries the items that matter.
- Grading on consequence before coexistence. A catastrophic single load
  path in a resistant alloy, dry and unstressed, is not an SCC item, and
  treating it as one spends the control budget in the wrong place.
- Taking the alloy condition off the table on a medium rating. Medium
  counts towards coexistence; only a resistant state clears it.
- Passing a stress in megapascals into the ratio. It is caught here, but
  a version that clamped it instead would have marked every application
  in the set as stressed.

## Behavior contract (gate 3)

The token normalization, the three condition tests with their inclusive
boundaries, the coexistence read, the consequence and redundancy grading
and the population aggregation are exercised by the gate 3 contract
test: scripts/test_q7036_scc_criticality_identification.py against
scripts/q7036_scc_criticality_identification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7036_scc_criticality_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
