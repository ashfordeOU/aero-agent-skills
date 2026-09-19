---
name: e31-budget-allocation-thermal-power-mass
description: "Allocate and track the thermal control subsystem budgets of ECSS-E-ST-31C clause 4.4.2. Use when hot-case dissipation, cold-case heater demand and thermal hardware mass each have to be rolled up against an allocation rather than estimated: load every budget line with the contingency its design-maturity category earns, roll raw and loaded totals separately, apply the system-level margin, grade dissipation against the radiator rejection capacity at its hot-case and sink temperatures, grade heater demand and mass against their allocations, and name the tightest of the three. Trigger: ecss, e-st-31c, tcs-budget-allocation, thermal-rejection-budget, heater-power-budget-rollup, thermal-hardware-mass-budget, maturity-contingency-policy, radiator-rejection-capacity."
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
  tags: [ecss, e-st-31-thermal-scope, e31-budget-allocation-thermal-power-mass, tcs-budget-allocation, thermal-rejection-budget, heater-power-budget-rollup, thermal-hardware-mass-budget, maturity-contingency-policy, radiator-rejection-capacity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Thermal, Heater Power and Mass Budget Allocation (space-systems/ecss/e31-budget-allocation-thermal-power-mass)

Use when the task is the allocate-and-track discipline of ECSS-E-ST-31C
clause 4.4.2 — three thermal control budgets, each rolled up the same way
and each graded against its own allocation: the heat the radiators have to
reject, the heater power the cold case demands, and the mass the thermal
hardware costs.

Scope boundary: sizing a solar array or a battery from an eclipse profile
is a different job and belongs to the electrical power sizing skill. This
leaf is the roll-up, the contingency policy and the allocation tracking.

## Domain quick reference

- A budget line is a value plus a maturity. Contingency is not a flat
  percentage across the subsystem; it tracks how much the item can still
  grow. Off-the-shelf hardware reused as-is carries little, a modified
  item more, a new design most. A line with no maturity category is a data
  gap, not a zero-contingency line.
- Raw and loaded totals are reported separately. The difference between
  them is what the contingency policy is carrying, and hiding it inside a
  single number makes it impossible to see whether a budget is tight
  because the design is heavy or because the maturity is low.
- System-level margin sits on top of the line contingencies, not instead
  of them. Line contingency covers growth of a known item; the system
  margin covers items not yet on the list.
- The thermal budget is graded against a capacity, not an allocation
  number someone wrote down. The radiator rejects
  e * sigma * A * (T_rad^4 - T_sink^4) at its hot-case temperature against
  its hot-case sink, and that is the number the loaded dissipation has to
  fit inside. A sink at or above the radiator temperature rejects nothing
  and is refused rather than returned as a negative capacity.
- The three budgets move together. Adding radiator area to fix the thermal
  budget adds mass; adding insulation to fix the heater budget adds mass
  too; so the useful output is not three verdicts but the name of the
  tightest of the three and the margin it has left.

## Workflow

1. Validate every budget line: a name, a non-negative value under the key
   the budget uses, and a maturity category the contingency table
   recognises. Refuse an uncategorized line and refuse two lines sharing a
   name.
2. Roll the lines up twice, raw and with the per-line contingency applied,
   and keep both totals in the record.
3. Apply the system-level margin to the loaded total to get the value the
   budget is tracked at; refuse a margin fraction at or above one.
4. For the thermal budget, compute the radiator rejection capacity at the
   hot-case radiator and sink temperatures and grade the tracked
   dissipation against it.
5. For the heater power and mass budgets, grade the tracked value against
   the stated allocation, using a named tolerance so a budget landing
   exactly on its allocation is a decision, not a failure.
6. Report each budget with its raw, loaded, tracked and margin values, the
   name of the tightest of the three, and every finding.

## Pitfalls

- Applying one contingency percentage to the whole subsystem. It hides
  which lines are the growth risk, and it under-contingencies precisely
  the new designs that grow.
- Replacing line contingency with the system margin, or the reverse. They
  cover different things, and collapsing them leaves the budget with no
  cover for either unlisted items or growth in listed ones.
- Grading dissipation against a written allocation instead of the radiator
  capacity. The capacity moves with the fourth power of radiator
  temperature and with the sink, so a budget that fit at a 310 K radiator
  does not fit when the radiator requirement drops to 290 K.
- Tracking the three budgets in separate documents. A fix to one is
  usually a debit on another, and only a combined view shows that the
  radiator growth which solved the thermal budget has just broken the mass
  one.
- Reporting a raw total as the budget. The tracked value is the loaded
  total with the system margin applied; the raw total is an input to it,
  not a result.

## Behavior contract (gate 3)

Maturity-to-contingency lookup, per-line loading with the uncategorized
line refused, raw and loaded roll-ups with duplicate names refused,
system-margin application, allocation status with a boundary tolerance,
grey-body radiator rejection capacity, the three budget assessments and
the combined tightest-budget report are exercised by the gate 3 contract
test: scripts/test_e31_budget_allocation_thermal_power_mass.py against
scripts/e31_budget_allocation_thermal_power_mass_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_budget_allocation_thermal_power_mass.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
