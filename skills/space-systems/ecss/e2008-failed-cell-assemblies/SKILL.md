---
name: e2008-failed-cell-assemblies
description: "Determine whether an inspected solar cell assembly is treated as failed under ECSS-E-ST-20-08C clause 6.5.2, where any single listed mode condemns the unit. Use when an assembly or a whole inspection lot needs a disposition rather than a score: resolve the mode catalogue and the limits its measured modes are graded against, read each observation as present, absent or never examined, refuse a boolean where a measurement belongs and the reverse, let one present mode settle the unit whatever the rest showed, hold a clean-looking unit unevaluated while any mode stays unexamined, and tally the units into the lot. Trigger: ecss, e-st-20-08c, clause-6-5-2, failed-cell-assembly-disposition, sca-failure-mode-catalogue, any-listed-mode-condemns-rule, unexamined-failure-mode-handling, sca-inspection-lot-failure-tally."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-failed-cell-assemblies, e-st-20-08c, clause-6-5-2, failed-cell-assembly-disposition, sca-failure-mode-catalogue, any-listed-mode-condemns-rule, unexamined-failure-mode-handling, sca-inspection-lot-failure-tally]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Failed Cell Assemblies (space-systems/ecss/e2008-failed-cell-assemblies)

Use when the task is the clause 6.5.2 treatment of ECSS-E-ST-20-08C: a solar
cell assembly has been inspected against the listed failure modes, and whether
that unit counts as failed has to be settled on the evidence rather than on an
impression of how bad it looked.

## Domain quick reference

- The rule is disjunctive, not a score. One listed mode found on the unit is
  the whole answer. The modes are not weighted against each other, a mode is
  not offset by the seven that came out clean, and there is no threshold count
  of modes below which a unit survives.
- That makes the verdict short-circuit. A unit with a present mode is failed
  whatever the remaining modes did, so an examination that stopped early
  because the first mode was found is still a complete answer for this clause.
- The same short circuit does not run the other way. A unit with no present
  mode and a mode nobody looked at has not been shown to be sound; it is
  unevaluated. Reading an absent observation as a clean result is how an
  incomplete inspection passes as a pass.
- The catalogue mixes two bases. Some modes are seen and take a yes or no;
  others exist only as a quantity crossing a limit and take a measurement.
  Handing one basis the other's evidence is an input defect, because a truthy
  number would condemn every unit that was measured at all.
- Measured modes face the limit in a direction. A degradation and a
  delamination are modes by rising above a limit; an insulation resistance is
  a mode by falling below one, and a single comparison cannot serve both.
- Limits are inclusive. A measurement landing exactly on the limit is not the
  mode, so the comparison absorbs representation error instead of the limit
  being nudged to make the arithmetic tidy.
- The lot tally is a separate arithmetic. The failed share is taken over the
  units actually settled, so units left unevaluated neither dilute the share
  nor quietly count as good.

## Workflow

1. Resolve the mode catalogue and merge any project limit overrides onto the
   declared defaults, refusing an unrecognized limit, a non-positive one, or a
   fraction above unity.
2. Normalize every observation onto a listed mode, refusing an unlisted mode
   and a mode observed twice under two spellings.
3. Reduce each mode in the catalogue to present, absent or never examined,
   validating the evidence against the mode's basis in both directions.
4. Grade each measured mode against its limit in the direction that mode
   crosses it, treating a value exactly on the limit as absent.
5. Settle the unit: failed the moment any mode is present, unevaluated when
   nothing is present but something was never examined, sound only when every
   listed mode was examined and came out absent.
6. Report every present mode and every unexamined mode, so the disposition
   names what drove it rather than delivering a bare verdict.
7. Roll the units into the lot, taking the failed share over the settled units
   and carrying the unevaluated units through as their own list.

## Pitfalls

- Scoring the modes. Counting three minor modes as worse than one major one
  reintroduces a judgement the clause does not have; the count is reported,
  but the verdict turns on the first present mode alone.
- Reading an unexamined mode as a clean one. Nothing was submitted, so nothing
  was found, so the unit looks sound -- and the one mode that mattered is the
  one nobody looked for.
- Waiting for a complete examination before condemning. A found mode is enough,
  and holding the disposition open for the remaining modes keeps a known-bad
  unit in the flow.
- Passing a boolean to a measured mode. It reads as a small number, sits under
  every rising limit, and turns a mode that was never measured into a pass.
- Using one comparison for both directions. An insulation resistance is a mode
  by being too low; graded as though it were a degradation, a dead unit reads
  clean.
- Widening a limit so a measurement exactly on it counts. The edge is already
  inclusive; the tolerance belongs inside the comparison.
- Taking the lot failed share over every unit presented. Units that were never
  settled belong outside the denominator, not silently in the good column.

## Behavior contract (gate 3)

The catalogue split by basis, the limit resolution and its refusals, the three
per-mode statuses, the basis-mismatch refusals in both directions, the
inclusive limit edges on a rising and a falling mode, the one-mode-condemns
rule with its short circuit past unexamined modes, the unevaluated verdict for
a clean but incomplete unit, and the lot tally with its settled-unit
denominator are exercised by the gate 3 contract test:
scripts/test_e2008_failed_cell_assemblies.py against
scripts/e2008_failed_cell_assemblies_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_failed_cell_assemblies.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
