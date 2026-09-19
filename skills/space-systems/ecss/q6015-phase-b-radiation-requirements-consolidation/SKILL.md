---
name: q6015-phase-b-radiation-requirements-consolidation
description: "Define the consolidated radiation environment and hardness assurance requirement baseline a system review can settle. Use when the ECSS-Q-ST-60-15C clause 4.4.2 phase B work has to be produced or graded: check every requirement for an environment source, a design factor at or above the floor of its allocation level and a stated verification method, weight a dose-depth curve by the solid-angle fraction of each shielding sector to obtain the equipment location dose, screen the candidate part list by radiation design margin into accept, shield, test or reject, and name what still blocks the review. Trigger: ecss, q-st-60-15c-clause-4-4-2, phase-b-radiation-requirements-consolidation, sector-shielding-analysis, early-radiation-part-screening, radiation-design-margin-screening, requirement-allocation-design-factor."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-phase-b-radiation-requirements-consolidation, q-st-60-15c-clause-4-4-2, phase-b-radiation-requirements-consolidation, sector-shielding-analysis, early-radiation-part-screening, radiation-design-margin-screening, requirement-allocation-design-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Phase B Consolidation (space-systems/ecss/q6015-phase-b-radiation-requirements-consolidation)

Use when the task is the definition-phase step of ECSS-Q-ST-60-15C clause
4.4.2 — turning the coarse feasibility numbers into a requirement baseline
the system review can actually settle, with the first real shielding
geometry and the first pass over the candidate parts behind it.

## Domain quick reference

- A requirement is only consolidated when it carries four things: where the
  environment number came from, the design factor applied to it, the level it
  is allocated at, and how it will be verified. A number without those cannot
  be traced back when the environment model is revised, and cannot be closed
  when the hardware is built.
- The design-factor floor rises as the allocation descends. A system-level
  statement still has the subsystem, equipment and part allocations below it
  to absorb an environment error; a part-level number has nothing below it, so
  it carries the largest factor.
- Phase B is where a location stops being a point and becomes a geometry. The
  equipment dose is the solid-angle weighted average over the shielding
  sectors around it, and because the dose-depth curve falls steeply, a small
  thin sector dominates the result — which is exactly why a single equivalent
  thickness under-reports the location.
- A sector model whose solid-angle fractions do not sum to unity is not a
  conservative model, it is an arithmetic error: part of the sky has been left
  unaccounted for and the weighted dose means nothing.
- Early screening sorts parts into work packages, not into pass and fail.
  Clear margin takes the part; margin above the specified level but under the
  acceptance factor keeps the part and buys shielding or a relocation; no
  margin rejects it; and a capability with no test behind it owes one however
  comfortable the ratio looks.
- A capability carried across by similarity is a claim, not evidence. It can
  survive the screening as a candidate but it cannot close the review, so it
  is grouped with the parts that owe a test rather than with the accepted ones.

## Workflow

1. Grade each candidate requirement for the four attributes, normalising the
   allocation level and the verification method against their closed sets and
   refusing an unrecognised value rather than dropping the requirement.
2. Compare each design factor with the floor of its allocation level,
   accepting an exact equality at the floor through a named tolerance.
3. Validate the sector shielding model: positive fractions, positive
   thicknesses, and fractions summing to unity within tolerance.
4. Interpolate the dose-depth curve in log-log at each sector thickness,
   refusing a thickness the curve does not span instead of extrapolating, and
   weight the results by solid-angle fraction to get the location dose.
5. Apply the equipment design factor to obtain the specified level, then
   screen every candidate part on its margin against that level, overriding
   the disposition to a test when the capability rests on similarity.
6. Collect the requirement findings, the rejected and untested parts and any
   open shielding action; the baseline is settled only when nothing remains.

## Pitfalls

- Consolidating on the number alone. A dose with no environment source behind
  it cannot be re-derived when the mission profile moves, and the review
  cannot tell an analysis result from an inherited assumption.
- Using one equivalent aluminium thickness for a box in a corner of the
  structure. The dose-depth curve is steeply non-linear, so averaging the
  thickness and averaging the dose give different answers, and the thickness
  average is the optimistic one.
- Letting the sector fractions sum to something other than unity. The missing
  fraction is not conservatism; it silently deletes part of the incident sky
  from the result.
- Reading a screening disposition as a verdict on the part. Shield-or-relocate
  is a design action, not a rejection, and treating it as one throws away
  parts that the box could carry with a local spot shield.
- Accepting a similarity-based capability because its ratio looks large. The
  ratio is only as good as the datum under it; until a test exists the part
  belongs with the ones that owe evidence.

## Behavior contract (gate 3)

The requirement grading, allocation-level design-factor floors, sector-model
validation, dose-depth interpolation, solid-angle weighting, part screening
and the review verdict are exercised by the gate 3 contract test:
scripts/test_q6015_phase_b_radiation_requirements_consolidation.py against
scripts/q6015_phase_b_radiation_requirements_consolidation_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6015_phase_b_radiation_requirements_consolidation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
