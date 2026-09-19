---
name: q7040-rebrazing-and-repair
description: "Determine whether a rejected brazement may be re-brazed or has to be remade. Use when a post-braze inspection has turned a joint down and someone must choose between a repair cycle and a new part: separate the flow defects a second heating can cure from the losses of parent metal it only deepens, count the repair cycles the joint category still allows, add the planned dwell above the filler liquidus into the cumulative erosion budget the material pair tolerates, refuse a repair that has no qualified procedure behind it, and hand a permitted repair back with the re-inspection set it owes. Trigger: ecss, q-st-70-40-brazing, braze-repair-cycle-limit, braze-rebraze-dwell-budget, braze-defect-reflow-curability, braze-repair-procedure-qualification, brazement-post-repair-reinspection."
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
  tags: [ecss, q-st-70-40-brazing, q7040-rebrazing-and-repair, braze-repair-cycle-limit, braze-rebraze-dwell-budget, braze-defect-reflow-curability, brazement-post-repair-reinspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Re-brazing and Repair (space-systems/ecss/q7040-rebrazing-and-repair)

Use when the task is the repair clause of ECSS-Q-ST-70-40: deciding
whether a brazement that failed inspection may be put back through a
braze cycle, how many such cycles it has left, and what the repaired
joint owes before it can be offered again.

## Domain quick reference

- A rejected brazement is not automatically a repair. The defect has to
  be one a second heating can actually cure.
- Short fillets, entrapped flux residue, fillet porosity, incomplete
  wetting and filler run-out are wetting and flow problems. Re-melting
  the filler re-forms the fillet, so these are the repairable set.
- Base-metal erosion, filler depletion into the parent, a crack that has
  run out of the fillet into the parent metal and thermal distortion are
  losses of parent material or geometry. A second heating deepens them.
  They are remake findings, not repair findings.
- The repair budget is counted twice. A joint category allows a number
  of re-braze cycles, and a base-metal and filler pair allows a
  cumulative dwell above the filler liquidus. A joint can sit inside the
  cycle count and outside the dwell budget, or the reverse, so both are
  evaluated and neither substitutes for the other.
- The dwell budget exists because every excursion above liquidus
  dissolves more parent metal into the filler and diffuses more filler
  into the parent. That is progressive and it is not undone by cooling.
- Aluminium pairs have the tightest budget: the filler and the parent
  melt within a narrow interval, so a long dwell takes the parent with
  it.
- A repair is a process in its own right and needs its own qualified
  procedure. Working a repair to the original braze procedure is an
  unqualified process, whatever the joint looks like afterwards.
- The repaired joint owes the original inspection again. A repair that
  consumes the last permitted cycle owes a destructive metallographic
  check as well, because nothing else evidences what the accumulated
  heat did to the parent.

## Workflow

1. Take the defect and decide whether it is reflow-curable or a loss of
   parent material. A loss of parent material ends the assessment at a
   remake, whatever the cycle count says.
2. Count the re-braze cycles already taken from the thermal history and
   subtract them from the limit the joint category allows.
3. Sum the dwell each recorded cycle spent above the filler liquidus,
   add the dwell the planned repair will spend, and compare the total
   with the budget the material pair tolerates. Absorb representation
   error at the boundary with a named tolerance rather than by rounding
   the budget.
4. Confirm a qualified repair procedure covers the joint. An absent
   qualification is a nonconformance route, not a remake.
5. Set the disposition: a remake when the defect is a parent-material
   loss or the dwell budget is spent; a nonconformance board when the
   cycle count is exhausted or the procedure is unqualified; a repair
   otherwise.
6. Report every finding, not only the deciding one, so the board sees
   the whole picture rather than the first rule that fired.
7. Hand a permitted repair back with the re-inspection set for its
   category and its cycle number.

## Pitfalls

- Reading the cycle count as the whole limit. A joint on its first
  repair can already be out of dwell budget if the original braze ran
  long, and the cycle count will happily say there is room.
- Repairing an eroded joint because the fillet still looks short. The
  short fillet is a symptom; the filler went into the parent and a
  further heating takes more of it.
- Working the repair to the original braze procedure. The thermal
  condition of a repair is different from that of a first braze, which
  is exactly why the repair procedure is qualified separately.
- Widening the dwell budget to let an exact-equality case through. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the budget stays as qualified.
- Offering a repaired critical joint on a visual inspection alone. The
  defects a repair cycle introduces are internal, and the inspection
  that found the original defect is the minimum the repair owes.
- Treating a missing repair-procedure qualification as a scrap decision.
  It is a paperwork route with a real part at the end of it; scrapping
  the part closes the finding by destroying the evidence.

## Behavior contract (gate 3)

The defect curability split, the cycle limit by joint category, the
cumulative dwell accumulation with its liquidus check, the material-pair
dwell budget with its boundary tolerance, the re-inspection set and the
repair, remake and nonconformance dispositions are exercised by the gate
3 contract test:
scripts/test_q7040_rebrazing_and_repair.py against
scripts/q7040_rebrazing_and_repair_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7040_rebrazing_and_repair.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
