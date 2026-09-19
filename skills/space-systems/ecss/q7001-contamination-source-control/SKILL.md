---
name: q7001-contamination-source-control
description: "Analyze the contamination sources a design carries — lubricants, adhesives, outgassing surfaces, particulate shedders — and size what each puts on the surfaces that matter under ECSS-Q-ST-70-01C. Use when a design holds a contamination allocation and the question is which items spend it and what would actually reduce them. Scales each emission rate to the source's own temperature, carries it through view factor, capture and exposure duration, credits only control measures with a verification basis behind them, and totals molecular and particulate contributions in their own currencies. Names the smallest set of sources worth redesigning. Trigger: ecss, q-st-70-01, contamination-source-control, lubricant-adhesive-outgassing-source, particulate-shedding-source, contamination-view-factor-transport, contamination-control-measure-credit, dominant-contamination-contributor."
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
  tags: [ecss, q-st-70-cleanliness-scope, q7001-contamination-source-control, lubricant-adhesive-outgassing-source, particulate-shedding-source, contamination-view-factor-transport, contamination-control-measure-credit, dominant-contamination-contributor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Contamination Source Control (space-systems/ecss/q7001-contamination-source-control)

Use when the task is the source-control half of the ECSS-Q-ST-70-01C
design clause — listing what a design emits, sizing what each source
actually delivers to the surfaces that care, and deciding which control
measures may be credited against it.

## Domain quick reference

- A source is only a problem in proportion to what reaches a receiver.
  The emission rate is the start of the chain; the geometric view
  factor, the share that sticks on arrival, the exposure duration and
  the area it is spread over all sit between the source and the number
  the budget is held to. A large emitter with no line of sight can
  matter less than a small one facing the optic.
- Emission rates are quoted at the temperature they were measured at.
  A source running hot emits far more than its data sheet says, so the
  rate is scaled to the source's own operating temperature through an
  activation temperature before anything else is done with it. Two
  successive scalings compose into the single scaling between the end
  temperatures, which is the consistency check to keep.
- Molecular and particulate contributions are different currencies. A
  deposited areal mass and an added obscured-area fraction answer
  different requirements and have separate allocations; summing them
  produces a number with no requirement to compare against.
- A control measure earns credit only with a verification basis behind
  it. A bake-out, a labyrinth seal or a debris shroud that nobody has
  demonstrated is an intention, and crediting its effectiveness removes
  from the budget an amount the hardware never removed.
- Controls that do apply compose multiplicatively on what survives, not
  additively on what is removed. Two measures at seventy and fifty per
  cent leave fifteen per cent, never zero, and no stack of finite
  measures reaches a total barrier.
- The ranking is the actionable output. A design change is worth making
  on the few sources that account for most of the total; work spent on
  the tail changes the budget by less than the uncertainty on the
  leading term.

## Workflow

1. Validate each source: name, kind, currency, specific emission rate,
   emitting area, view factor to the receiver, capture fraction,
   exposure duration and the receiving area.
2. Where a temperature scaling is given, require the operating
   temperature, the reference temperature and the activation
   temperature together; a partial set is an input error, because
   assuming any one of them silently rescales the whole source.
3. Compute the uncontrolled contribution of each source in its own
   currency.
4. For each source, take the control measures that name its kind, drop
   any without a verification basis with a finding, refuse the same
   control credited twice, and multiply the surviving retentions.
5. Total each currency separately and compare with its allocation,
   absorbing an exact landing with a named tolerance.
6. Rank the sources and identify the smallest leading set covering the
   stated share of each currency's total; report a source in that set
   carrying no credited control.
7. Report per-source uncontrolled and controlled contributions, the
   ranking, the dominant sets, the totals against allocation, and every
   finding.

## Pitfalls

- Ranking sources by emission rate. The ranking that matters is by what
  arrives, and view factor and capture fraction routinely move a source
  several places either way.
- Using a data-sheet rate at an operating temperature well above the
  measurement. The error is exponential in the temperature difference,
  so it is the one input error large enough to invert the ranking.
- Adding deposited mass to obscured area to get one contamination
  number. There is no allocation for the sum, and the composite hides
  which of the two is actually over.
- Crediting a planned control measure. The budget then closes on paper
  from the moment the measure is written down, months before anything
  demonstrates it works.
- Adding control effectiveness instead of composing retentions. Two
  sixty per cent measures come out as a total barrier, which is the
  arithmetic behind most claims of a fully controlled source.
- Attacking the tail of the ranking because those changes are easy. The
  leading source keeps the budget where it was, and the effort is spent
  below the uncertainty of the term that dominates.

## Behavior contract (gate 3)

The temperature scaling and its composition property, emission and
transport to the receiver, verified-control crediting with
multiplicative retention, per-currency totalling against allocation,
ranking and dominant-set identification are exercised by the gate 3
contract test: scripts/test_q7001_contamination_source_control.py
against scripts/q7001_contamination_source_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7001_contamination_source_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
