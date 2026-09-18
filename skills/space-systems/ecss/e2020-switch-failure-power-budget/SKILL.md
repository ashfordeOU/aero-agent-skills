---
name: e2020-switch-failure-power-budget
description: "Evaluate whether a limiter switch stuck in the on state is paid for by the spacecraft power budget where no further switching can open the channel, per clause 5.2.13.1.1 of ECSS-E-ST-20-20C. Use when a channel has no second means of isolation: decide which provisions genuinely shed a stuck-on load and which only add a second path into it, turn the stuck-on current into continuous power at bus voltage, charge only what the failure adds over the draw already budgeted, take the worst single channel rather than the sum, and keep the required margin instead of spending it. Trigger: ecss, e-st-20-20c-clause-5-2-13-1-1, limiter-switch-stuck-on, spacecraft-power-budget-coverage, no-additional-switching-provision, stuck-on-continuous-power, power-budget-margin-shortfall."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-13-1-1, e2020-switch-failure-power-budget, limiter-switch-stuck-on, spacecraft-power-budget-coverage, no-additional-switching-provision, stuck-on-continuous-power, power-budget-margin-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Stuck-On Switch Power Budget Coverage (space-systems/ecss/e2020-switch-failure-power-budget)

Use when the task is clause 5.2.13.1.1 of ECSS-E-ST-20-20C: a limiter
switch that fails in the on state is covered inside the spacecraft power
budget, in the case where the channel carries no additional switching
that could remove the load. Nothing can open the channel, so the failure
is not an event to be handled -- it is a load that stays on, and the
budget is the only place it can go.

## Domain quick reference

- The question only exists for channels nothing can shed. An upstream
  isolation switch or a downstream load switch still opens the channel,
  so the stuck limiter costs the budget nothing and the channel drops
  out of the charge entirely.
- A redundant limiter branch is not a switching provision. It is a
  second way into the same load, so it changes which limiter carries the
  current and not whether the current can be stopped; reading it as
  relief is the common way a channel escapes the charge it should carry.
- The channel's nominal draw is already in the budget. What the failure
  costs is the increment on top of that, and where the stuck-on draw
  sits below the nominal one the increment is zero rather than a credit
  handed back to the budget.
- The charge is a worst case under the declared failure count, not a
  sum. One stuck switch is one stuck switch; adding every channel's
  increment together prices a scenario the failure hypothesis never
  claimed and buys generation nobody needed.
- Margin is not the place a stuck-on load is meant to land. A budget
  that only closes by consuming its required margin has covered the
  failure with the allowance held for everything still unknown, so that
  case is reported apart from a budget that simply does not close.
- A channel with no declared stuck-on current is the channel nobody
  sized, not a channel costing nothing, and it outranks a budget that
  came out short, because the two need different work.

## Workflow

1. Validate the policy: the required margin is a fraction below one, and
   at least one channel is assumed stuck at a time.
2. Read each channel into its switching provision, its nominal draw and
   its stuck-on current at bus voltage; refuse a duplicate channel, an
   unrecognised provision and a negative power, and keep a missing
   stuck-on current as unsized rather than as zero.
3. Separate the channels a provision can shed from the channels nothing
   can, and carry only the second group into the budget question.
4. Turn each remaining stuck-on current into continuous power at bus
   voltage, then into the increment it adds over the draw already
   budgeted, floored at zero.
5. Charge the largest increments up to the declared simultaneous failure
   count, add them to the nominal demand and compare the total with the
   power available in the sizing mode.
6. Compute the margin left on the available power and compare it with
   the requirement, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by relaxing the
   requirement.
7. Rank the spacecraft at its worst standing: an unsized unsheddable
   channel first, then a demand past the available power, then a margin
   shortfall, then covered -- and name the channels actually charged.

## Pitfalls

- Charging a channel that a load switch can still open. The clause is
  about the case where no extra switching exists; pricing the others
  inflates the budget and hides the channel that genuinely has no way
  out.
- Accepting a redundant limiter branch as a means of removing the load.
  Two paths into a load are still a load, and the stuck switch on one of
  them keeps the draw exactly where it was.
- Charging the full stuck-on power rather than the increment. The
  nominal draw is already carried in the demand, and double counting it
  makes a covered case look like a shortfall.
- Handing the budget a credit when the stuck draw is below nominal. A
  failure that draws less than planned does not free power for anything
  else; the increment floors at zero.
- Summing every unsheddable channel's increment under a single-failure
  hypothesis. That prices a scenario nobody claimed and sizes the array
  for it.
- Reporting a budget that closes only on its margin as covered. The
  margin is held for what is not yet known, and a known stuck-on load
  spending it leaves nothing for the rest.
- Reading a channel with no declared stuck-on current as costing
  nothing. Nothing was sized for it, so it cannot have passed.

## Behavior contract (gate 3)

The policy validation, the switching provision vocabulary and which
provisions genuinely shed a load, the stuck-on power at bus voltage, the
increment floored at the draw already budgeted, the worst-case charge
under the declared simultaneous failure count, the margin on the
available power with its boundary handling and the worst-standing
spacecraft verdict are exercised by the gate 3 contract test:
scripts/test_e2020_switch_failure_power_budget.py against
scripts/e2020_switch_failure_power_budget_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_switch_failure_power_budget.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
