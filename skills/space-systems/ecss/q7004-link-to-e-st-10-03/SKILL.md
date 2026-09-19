---
name: q7004-link-to-e-st-10-03
description: "Coordinate an ECSS thermal test with the equipment-level test requirements it has to sit beside. Use when ECSS-Q-ST-70-04C conditions and ECSS-E-ST-10-03C equipment testing both bear on one article: compare hot limit, cold limit, dwell and cycle count parameter by parameter, keep the more severe value and name the governing document, check whether the equipment-level set envelopes the material-level one and list every parameter it does not, then credit cycles already run at equipment level against the remaining count at a declared efficiency and under a cap. Trigger: ecss, q-st-70-04-thermal-testing-scope, e-st-10-03-equipment-test-interface, thermal-test-requirement-reconciliation, governing-standard-determination, equipment-level-envelope-coverage, thermal-cycle-credit-allocation."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-link-to-e-st-10-03, e-st-10-03-equipment-test-interface, thermal-test-requirement-reconciliation, governing-standard-determination, equipment-level-envelope-coverage, thermal-cycle-credit-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Link to the Equipment-Level Test Standard (space-systems/ecss/q7004-link-to-e-st-10-03)

Use when the task is the interface clause of ECSS-Q-ST-70-04C that points
at ECSS-E-ST-10-03C — one article carrying two sets of thermal test
requirements at once, and the question of which set governs each
parameter, what the equipment-level run actually covers, and how much of
the material-level campaign it can be credited against.

## Domain quick reference

- Two standards speaking to one article is not a conflict to be escalated.
  It is a parameter-by-parameter comparison with a fixed rule: the more
  severe value governs, and the document it came from is recorded beside
  it so a later revision of either one is traceable.
- Severity has a direction, and the direction differs per parameter. A
  higher hot limit is more severe, a lower cold limit is more severe, more
  cycles and longer dwells are more severe, and a lower chamber pressure
  is more severe. A parameter with no declared direction is refused rather
  than compared, because guessing the sense silently inverts the result.
- Enveloping is a separate question from governing. An equipment-level set
  that is more severe on three parameters and less severe on the fourth
  envelopes nothing; the fourth is a coverage gap and stays in the thermal
  test campaign. Reporting "the equipment test covers it" on a majority of
  parameters is the failure mode this check exists for.
- Credit is a third question again. A cycle run under the other standard
  is not the same cycle — the mounting, the rates and the monitoring all
  differ — so it is credited at a declared efficiency below one. The total
  credit is then capped at a fraction of the requirement, because a
  campaign that credits itself to zero has verified nothing.
- The margin the governing limits hold over the material-level values is
  worth reporting on its own. A governing hot limit only a kelvin above
  the material-level one means a small specification change flips which
  document governs, and the reconciliation has to be re-run.

## Workflow

1. Validate the reconciliation policy: a credit efficiency in (0, 1], a
   cap strictly below one, and a parameter list every entry of which has a
   declared severity direction.
2. Reconcile each required parameter, refusing a requirement set that is
   missing one rather than defaulting it.
3. Record the governing value and the governing document per parameter,
   attributing an equal pair to both rather than to whichever was read
   first.
4. Take the envelope gaps as the parameters where the material-level set
   still governs, and report the list, not a boolean alone.
5. Compute the credit from the equipment-level cycles actually run,
   flooring the earned credit and applying the cap, and report the earned,
   the cap and the remainder separately.
6. Take the hot and cold margins the governing limits hold, and close with
   the findings: coverage gaps, a capped credit, and a thin margin that
   makes the governing document unstable.

## Pitfalls

- Comparing a cold limit as though colder were weaker. The sense table
  exists because half the parameters invert, and a single inverted
  comparison produces a test that is less severe than both standards.
- Declaring the equipment-level test enveloping because it is more severe
  overall. Overall is not a parameter; the gap list is.
- Crediting equipment-level cycles one for one. The two runs differ in
  mounting and monitoring, so the efficiency is below one and is declared,
  not assumed.
- Letting the credit clear the whole requirement. A cap strictly below one
  is what keeps a campaign from verifying itself out of existence.
- Comparing an equal pair of values with bare equality on floats. Two
  specifications that agree can still differ in the last place; the
  attribution to both absorbs that representation error rather than
  awarding the parameter to a document at random.
- Reporting only the remaining cycle count. Without the efficiency and the
  cap that produced it, the number cannot be re-derived when either
  standard is revised.

## Behavior contract (gate 3)

The policy validation, severity sense table, parameter reconciliation,
envelope gap list, cycle credit with its floor and cap, and the governing
limit margins are exercised by the gate 3 contract test:
scripts/test_q7004_link_to_e_st_10_03.py against
scripts/q7004_link_to_e_st_10_03_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7004_link_to_e_st_10_03.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
