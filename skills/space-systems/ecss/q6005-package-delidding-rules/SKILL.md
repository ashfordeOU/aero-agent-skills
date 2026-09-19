---
name: q6005-package-delidding-rules
description: "Determine whether a sealed hybrid may be reopened under ECSS-Q-ST-60-05C clause 10.5.5, and what the reseal then owes. Use when a delid is proposed on a closed unit, for repair or for analysis: test whether that seal type can be reinstated at all, spend the reopen-cycle allowance and the sealing land each reseal consumes, read the reason to see whether the unit can return to deliverable stock, build the retest set the reseal carries, and return reopen-permitted, reopen-permitted-non-deliverable or reopen-not-permitted. Trigger: ecss, q-st-60-05c, hybrid-package-delidding, hybrid-lid-reseal-obligations, hybrid-delid-cycle-limit, hybrid-seal-land-consumption, hybrid-reseal-retest-set."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-package-delidding-rules, hybrid-package-delidding, hybrid-lid-reseal-obligations, hybrid-delid-cycle-limit, hybrid-seal-land-consumption, hybrid-reseal-retest-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Delidding and Reseal (space-systems/ecss/q6005-package-delidding-rules)

Use when the task is clause 10.5.5 of ECSS-Q-ST-60-05C: opening a hybrid that
has already been sealed, and deciding in advance whether the package supports
it, whether the unit comes back afterwards, and what testing the reseal owes
before anyone calls the unit closed again.

## Domain quick reference

- A seal is not a lid. It is a joint made once out of the package material,
  and reopening it destroys some of the material the next joint has to be
  made from. That is why reopening has a count and not just a procedure.
- Seal types differ in kind, not only in degree. A weld or a solder seal can
  be cut and remade; a fired glass seal cannot be reinstated to the condition
  it was qualified in, and a unit sealed that way is not reopened with a view
  to sending it on.
- The package carries two budgets that run down together but bind
  separately. The cycle allowance counts reopenings; the sealing land counts
  millimetres, and each reseal consumes a fixed width of it. A package can
  have a cycle left and not enough land to use it.
- Why the unit is being opened decides where it goes, and the reseal quality
  does not change that. An approved repair can put the unit back into
  deliverable stock once it is closed and retested. Opening for failure
  analysis, construction analysis or destructive physical analysis consumes
  the unit — it was opened to be looked at, not to be recovered.
- Capability is part of permission. A unit that is to return to stock must be
  reclosed by a qualified reseal process; without one, reopening it is a
  decision to scrap it, and that decision should be taken deliberately rather
  than discovered at the sealing station.
- The retest set is not fixed. It grows with what was done inside the
  package — internal work adds pre-seal visual, interconnect verification and
  a particle check — and with the route the unit takes, because returning to
  stock adds re-screening that an analysis unit never needs.
- Leak testing is the point of the reseal, not a formality attached to it. A
  reseal that has not been fine and gross leak tested has not been shown to
  be a seal at all, whatever it looks like.

## Workflow

1. Validate the package: seal type, the sealing land it started with, and how
   many times it has already been opened. An over-opened unit validates and
   is graded, rather than being refused as bad input.
2. Validate the reason against the recognised set, because the reason decides
   both the return route and what the reseal will owe.
3. Test resealability first. A seal type that cannot be reinstated makes
   every downstream budget irrelevant, and saying so plainly is more useful
   than reporting a cycle count for a package that has none.
4. Spend the cycle allowance, flooring the remainder at zero so an exhausted
   package reads as exhausted rather than as a negative count.
5. Spend the sealing land: subtract one more reseal's consumption from the
   starting land and compare the result with the minimum under a tolerance,
   because a nominal package consumed down to exactly its minimum is an
   ordinary outcome and must not flip on rounding.
6. Apply the return rule: a unit that is to go back needs a qualified reseal
   capability, and a unit opened for analysis is recorded as leaving
   deliverable stock whatever else is true.
7. Build the retest set from the seal type, the reason and whether internal
   work was done, de-duplicated and in the order it will be performed, and
   return it only where the reopening was actually permitted.

## Pitfalls

- Counting reopenings and forgetting the land. The cycle allowance is a proxy
  for material consumption, and a package that started near its minimum
  sealing land runs out of material before it runs out of cycles.
- Comparing the projected sealing land with a strict inequality. Fixed-width
  reseals subtracted from a nominal dimension land exactly on the minimum
  routinely, and without a tolerance the same package is accepted on one
  machine and scrapped on another.
- Treating a fired glass seal as a harder version of a weld. It is a
  different case: there is no reinstatement, so the answer is not a smaller
  allowance but no allowance.
- Letting a good reseal recover an analysis unit. The disposition follows the
  reason the package was opened, not the quality of the closure; a unit
  opened for construction analysis has been consumed by the act.
- Deciding to reopen before checking that the facility can reseal. Reopening
  is irreversible, and finding out afterwards that no qualified seal process
  is available converts a repair into a scrap.
- Reusing one retest set for every reseal. Internal work adds pre-seal
  verifications that a lid-only delid does not need, and a unit returning to
  stock adds re-screening that an analysis unit never will.
- Reporting the retest set for a reopening that was refused. It reads as
  authorisation, and a refused delid owes no tests because it should not
  happen.

## Behavior contract (gate 3)

The seal-type and reason validation, the reopen-cycle allowance, the
sealing-land budget, the return-to-stock rule, the retest set assembly and
the three-way disposition are exercised by the gate 3 contract test:
scripts/test_q6005_package_delidding_rules.py against
scripts/q6005_package_delidding_rules_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6005_package_delidding_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
