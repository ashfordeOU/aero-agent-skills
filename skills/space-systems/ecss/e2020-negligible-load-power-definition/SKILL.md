---
name: e2020-negligible-load-power-definition
description: "Define which load consumptions a power budget may carry as negligible. Use when an ECSS-E-ST-20-20C clause 5.2.13.2.1 budget needs the integrator's negligibility rule written as numbers and shown to hold: apply the tighter of the declared absolute watt figure and the declared share of the reference power, screen every consumer against it, sum what the rule excuses and compare that total against the aggregate cap, and confirm one excused consumer cannot on its own eat the budget uncertainty. Reports the unbudgeted residual and flags consumers sitting just under the threshold. Refuses an undeclared figure, a share at or above unity and a negative consumption. Trigger: ecss, e-st-20-20c, negligible-load-power-definition, power-budget-negligibility-threshold, negligible-load-aggregate-cap, unbudgeted-residual-power, budget-uncertainty-allowance."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-negligible-load-power-definition, power-budget-negligibility-threshold, negligible-load-aggregate-cap, unbudgeted-residual-power, budget-uncertainty-allowance, negligible-load-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Negligible Load Power Definition (space-systems/ecss/e2020-negligible-load-power-definition)

Use when the task is the negligible-consumption declaration of
ECSS-E-ST-20-20C clause 5.2.13.2.1 — the system integrator stating what
a load has to draw before the power budget is allowed to stop tracking
it as its own line, and showing that the rule it just stated does not
quietly hide a real amount of power.

## Domain quick reference

- A power budget cannot carry every consumer as its own line. Pull-up
  networks, status dividers, bleed resistors and latch-sense taps each
  draw a fraction of a watt, and tracking them individually costs more
  review effort than the watts are worth. The clause's answer is a
  declaration: the integrator writes down the figure below which a
  consumer is excused, and everything above it stays budgeted.
- The declaration is two numbers, not one. An absolute watt figure that
  is sensible on a large bus is absurd on a small one, so the rule also
  carries the same idea as a share of the reference power the budget is
  drawn against. The TIGHTER of the two binds. Declaring both and then
  applying whichever is looser is the usual way a negligibility rule
  stops meaning anything.
- The individual check is against the budget's own uncertainty
  allowance. If one excused consumer may draw as much as the allowance
  itself, the rule has licensed a load that matters, and the excusing is
  no longer a bookkeeping convenience.
- The collective check is the one that actually catches designs. Small
  consumers are numerous by construction, and forty of them sitting just
  under the threshold are an unbudgeted load, not a rounding error. The
  total the rule excuses is therefore compared against an aggregate cap
  expressed as a share of the same reference power.
- The excused total is the budget's unbudgeted residual. Reporting it as
  a share of the reference power and as a share of the uncertainty
  allowance is what lets a reviewer see whether the rule is a convenience
  or a hiding place.
- The threshold figures, the aggregate cap and the near-threshold
  advisory band are declared project policy rather than physical
  constants; the defaults in the logic module are a starting point a
  project substitutes its own values into.

## Workflow

1. Validate the declaration: an absolute watt figure and a relative
   share both present, the share and the aggregate cap below unity, and
   the advisory band a share rather than a watt figure. A rule with a
   missing half is undeclared, not permissive.
2. Validate the budget context: the reference power the shares are taken
   against and the uncertainty allowance the per-load threshold is
   graded against. Neither can be assumed.
3. Apply the tighter of the absolute figure and the share of the
   reference power, and carry that one number as the threshold.
4. Screen every consumer against the threshold, grouping the list into
   what stays budgeted and what the rule excuses. Raise an advisory, not
   a finding, for a consumer sitting inside the band just below the
   threshold — it is the one a later mass or duty-cycle change pushes
   back into the budget.
5. Compare the threshold against the budget uncertainty allowance and
   report a finding when a single excused consumer could consume it.
6. Sum what the rule excused, compare it against the aggregate cap, and
   report a finding when the collective residual is above the cap even
   though every consumer passed individually.
7. Report the unbudgeted residual in watts, as a share of the reference
   power and as a share of the uncertainty allowance, together with the
   slack on both checks so a reviewer sees which is nearest its edge.

## Pitfalls

- Applying the looser of the two declared figures. The absolute watt
  figure and the relative share are both live at once and the tighter
  one binds; taking the looser turns a two-number rule into whichever
  number happened to suit the load being excused.
- Checking consumers one at a time and never summing them. Every
  consumer can pass the per-load threshold while the list as a whole
  leaves watts outside the budget; the aggregate cap is the check that
  catches it, and it is the one most often left out.
- Declaring a per-load threshold at or above the budget uncertainty
  allowance. A consumer excused under such a rule can on its own absorb
  the margin the budget was relying on, so the excusing is no longer
  bookkeeping.
- Treating the excused total as zero. It is the budget's unbudgeted
  residual and it belongs in the report as a number, not as an absence;
  a reviewer cannot grade a residual that was never printed.
- Writing the rule as a fixed watt figure with no reference power. The
  same figure that is negligible against a several-hundred-watt bus is a
  budget line on a small platform, and a rule that does not scale gets
  copied onto the platform it does not suit.
- Comparing a threshold or an excused total by bare arithmetic. The
  threshold is a product of a share and a reference power and the
  excused total is a running sum, so a case meant to sit exactly on a
  bound can land a few units in the last place the wrong side of it; the
  comparison absorbs that representation error while the declared
  figures stay as specified.

## Behavior contract (gate 3)

The declaration validation, budget validation, consumer validation,
tighter-of-two threshold, aggregate cap, per-consumer screening, excused
and budgeted totals and the full evaluation are exercised by the gate 3
contract test:
scripts/test_e2020_negligible_load_power_definition.py against
scripts/e2020_negligible_load_power_definition_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2020_negligible_load_power_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
