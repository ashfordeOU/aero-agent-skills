---
name: e2020-line-voltage-drop-budget
description: "Calculate the voltage a protected distribution line loses at its class current. Use when an ECSS-E-ST-20-20C clause 5.4.5.1.1 power line has to be shown inside the drop its class allows: take the class current from the class table, raise every resistive contributor to its hot value, sum the limiter switch element, the sense shunt, the harness, the connector contacts and any series blocking device, apply the declared tolerance factor, then compare against the ceiling and report the margin, the split between resistive and fixed loss and the element carrying most of it. Refuses a class declaring two budgets, a duplicated element and a load drawing more than its class. Trigger: ecss, e-st-20-20c, line-voltage-drop-budget, protection-line-drop, lcl-class-current, harness-hot-resistance, connector-contact-drop, load-input-voltage-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-line-voltage-drop-budget, protection-line-drop, lcl-class-current, harness-hot-resistance, connector-contact-drop, load-input-voltage-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Protection Line Voltage Drop Budget (space-systems/ecss/e2020-line-voltage-drop-budget)

Use when the task is the line-drop limit of ECSS-E-ST-20-20C clause
5.4.5.1.1 — showing that everything between the bus and the load, taken
at the current the line's protection class is rated for, stays inside
the voltage the class is allowed to lose.

## Domain quick reference

- The load never sees the bus. It sees the bus minus the conducting
  element of the limiter, the shunt the limiter senses current on, the
  harness out and back, every connector contact in the path, and any
  series blocking device. The clause puts its ceiling on the sum,
  because it is the sum that decides whether the load is still inside
  its input range at the far end.
- The current the budget is evaluated at is the class current, not the
  load's quiet operating point. A line sized on the operating current
  has spent its whole budget the moment the load draws what its class
  permits, which is a condition the design has already agreed to allow.
- A load drawing more than its class current is not a drop problem at
  all. It is the wrong class, and it is refused before anything is
  summed rather than reported as a large drop.
- Resistance is temperature dependent. A copper path at the hot end of
  its range carries appreciably more resistance than the same path on
  the bench, so every resistive contributor is raised to its hot value
  before it enters the sum. Parts with their own coefficient carry their
  own; the copper default only applies where nothing else is declared.
- Fixed drops and resistive drops are different animals. A junction's
  forward voltage hardly moves with current while a resistance scales
  with it, so the two are summed and reported separately: a line
  dominated by a fixed drop is fixed by changing the part, and one
  dominated by resistance by shortening or fattening the path.
- Parts are not their typicals for ever, so the summed drop carries a
  declared tolerance factor before it meets the ceiling. The comparison
  is always against the worst-case number, never the nominal one.
- The budget may be declared absolutely or as a fraction of the bus.
  Exactly one of the two is the budget; a class carrying both is a data
  error, because the two will disagree the first time the bus voltage
  moves.
- A total alone is not a useful answer. The breakdown, grouped by
  element kind with the dominant contributor named, is what tells a
  designer whether the fix is a thicker harness or a different part.
- The temperatures, tolerance factor and advisory floors are declared
  project policy rather than physical constants; the defaults in the
  logic module are a starting point a project substitutes its own values
  into.

## Workflow

1. Validate the policy and the class table: a hot case at or above the
   reference temperature, a tolerance factor of at least one, ascending
   sanity on the class rows, unique class names, and exactly one budget
   form per class.
2. Take the class the line is assigned to and read its class current.
   That current, and not the operating current, is what the whole budget
   is evaluated at.
3. Where an operating current is declared, check it against the class
   before going further and refuse the line that is on the wrong class.
4. Raise each resistive contributor from its reference temperature to
   the hot case using its own coefficient where one is declared, then
   take its drop at the class current. Carry fixed forward drops through
   unscaled.
5. Sum the contributions, keep the resistive and fixed halves apart, and
   give each element its share of the total.
6. Apply the tolerance factor to reach the worst-case drop, compare that
   against the ceiling the class allows, and report the margin in volts
   and as a fraction of the budget together with the voltage the load
   actually sees.
7. Group the contributions by element kind, name the dominant element,
   and raise an advisory — not a finding — when one element carries more
   of the budget than the policy share allows.

## Pitfalls

- Budgeting at the operating current. It is the number on the load's
  data sheet and it is the wrong one: the class current is the current
  the protection has agreed the line may carry.
- Summing bench resistances. The hot path is the one that flies, and the
  temperature coefficient of copper turns a comfortable budget at 20 °C
  into a marginal one at the hot end of the range.
- Applying the copper coefficient to everything. A shunt built for a low
  coefficient, or a semiconductor element, is misrepresented by it; each
  part carries its own where one is declared.
- Forgetting the return path. The harness is out and back, and a budget
  that counts one leg is half a budget.
- Rolling fixed drops into an equivalent resistance. It reports a
  junction as though it scaled with current, which hides how the line
  behaves at any other current and points the fix at the wrong element.
- Reporting only the total. The ceiling says whether the line passes;
  the breakdown says what to change, and the second is the thing the
  designer came for.
- Comparing a summed drop with the ceiling by bare arithmetic. A line
  meant to land exactly on the budget, or exactly on the thin-margin
  floor, can fall a few units in the last place the wrong side of it;
  the comparison absorbs that representation error while the ceiling and
  the tolerance factor stay as specified.

## Behavior contract (gate 3)

The policy validation, class-table validation, budget-form selection,
hot resistance, per-element drop, breakdown with shares and kind
grouping, dominant-element advisory and the full line judgement are
exercised by the gate 3 contract test:
scripts/test_e2020_line_voltage_drop_budget.py against
scripts/e2020_line_voltage_drop_budget_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e2020_line_voltage_drop_budget.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
