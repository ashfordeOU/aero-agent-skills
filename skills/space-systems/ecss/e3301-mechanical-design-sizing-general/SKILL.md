---
name: e3301-mechanical-design-sizing-general
description: "Size a mechanism part so it meets its mechanical performance and withstands every specified environment over the design lifetime, under ECSS-E-ST-33-01C clause 4.7.5.1. Use when the task is combining axial, bending and shear stress into a von Mises value for each load case, knocking the material allowable down for temperature, ageing, radiation and surface condition before any margin is taken, computing separate yield and ultimate margins against their own safety factors, accumulating Miner damage over the mission load spectrum, grading the first-mode stiffness allocation, and naming the governing case and check. Trigger: ecss, e-st-33-01c, mechanism-part-sizing, mechanism-margin-of-safety, environment-knockdown-allowable, von-mises-combined-stress, mechanism-miner-cumulative-damage, mechanism-first-mode-stiffness, governing-load-case."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mechanical-design-sizing-general, mechanism-part-sizing, mechanism-margin-of-safety, environment-knockdown-allowable, mechanism-miner-cumulative-damage, mechanism-first-mode-stiffness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — General Mechanical Design and Sizing (space-systems/ecss/e3301-mechanical-design-sizing-general)

Use when the task is the general part-sizing requirement of ECSS-E-ST-33-01C
clause 4.7.5.1 — designing a mechanism part so it delivers the mechanical
performance asked of it and survives every environment specified for it, for
as long as the design life runs.

## Domain quick reference

- The clause is two requirements in one sentence: performance and endurance.
  A part can meet every static margin and still fail the clause, because the
  lifetime and the environments are part of the same requirement as the
  strength.
- Stresses combine before they are graded. Axial and bending stress add on
  the extreme fibre, shear enters weighted by three under a von Mises
  combination, and a part graded on the largest single component rather than
  on the combination has been graded optimistically.
- The environment belongs in the allowable, not in an extra factor. A
  temperature, ageing, radiation or surface-condition knockdown reduces what
  the material can carry; folding those into a safety factor instead hides
  which environment drove the design and double-counts against the factor the
  project actually specified.
- Yield and ultimate are separate checks with separate factors. The ultimate
  factor is normally the larger, so the governing check is not always the
  same one, and reporting a single margin loses which of the two it was.
- Cumulative damage is the lifetime half of the clause. A log-log S-N line
  and a Miner sum over the mission spectrum is the cheapest check that will
  catch a part sized entirely on the launch quasi-static case and then cycled
  for years by the mechanism it belongs to.
- Stiffness is a requirement in its own right. A first-mode allocation exists
  so the part does not couple with its neighbours, and a strong part below
  that allocation has failed a real requirement.

## Workflow

1. Validate the section properties and refuse a non-positive area, section
   modulus or shear area.
2. Knock the yield and ultimate allowables down for every declared
   environment. Refuse a factor above unity — an environment cannot
   strengthen a part — and refuse an unrecognised environment name rather
   than dropping it. Refuse an ultimate allowable that has fallen below the
   yield allowable.
3. For each load case, form the axial and bending stress on the section, add
   them, form the shear stress, and combine into a von Mises equivalent.
   A case that produces no stress at all is an input error, not a benign one.
4. Take the yield and ultimate margins of safety separately, each against its
   own factor, absorbing an exact zero margin with a named tolerance rather
   than by relaxing the factor.
5. Where a mission spectrum is given, read the allowable cycles for each
   block off the S-N line and accumulate the Miner damage, then grade it
   against the damage limit. Refuse a spectrum offered without the S-N line
   that would be needed to interpret it.
6. Where a stiffness allocation is given, grade the achieved first mode
   against it; refuse one half of the pair without the other.
7. Report both allowables, every case with both margins, the governing case
   and which check governs it, the cumulative damage, the stiffness margin
   and every finding.

## Pitfalls

- Grading the largest stress component instead of the combination. Bending
  and axial add, and shear enters the von Mises value weighted by three; a
  part passed on its bending stress alone can be well past yield.
- Putting the environment knockdown into the safety factor. The factor is a
  project quantity and the knockdown is a material one; merging them hides
  the driving environment and double-counts whichever of the two was already
  conservative.
- Reporting one margin. Yield and ultimate carry different factors, so which
  of them governs is information, and a single worst-of number thrown over
  the wall makes the next reader recompute both.
- Sizing on the launch case and stopping. A mechanism part is cycled for the
  whole mission; the static case usually sets the section and the spectrum
  usually sets the detail, and only one of the two is visible in a margin.
- Reading an S-N line at a stress it does not cover, or treating a spectrum
  as self-describing. The line, its reference point and its slope have to
  come with the spectrum or the damage sum means nothing.
- Treating the first-mode allocation as a guideline. It exists to keep the
  part from coupling with its neighbours, and a part below it has failed a
  requirement no strength margin can compensate for.

## Behavior contract (gate 3)

The stress combination, environment knockdown of both allowables, separate
yield and ultimate margins, log-log S-N allowable cycles and Miner damage
accumulation, first-mode grading and the governing-case selection are
exercised by the gate 3 contract test:
scripts/test_e3301_mechanical_design_sizing_general.py against
scripts/e3301_mechanical_design_sizing_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_mechanical_design_sizing_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
