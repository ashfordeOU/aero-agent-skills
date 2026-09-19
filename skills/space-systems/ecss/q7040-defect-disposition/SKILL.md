---
name: q7040-defect-disposition
description: "Plan the disposition of a braze defect that has failed acceptance, choosing between re-braze, local repair, a use-as-is deviation and scrap. Use when an indication has already been graded against its class limit and somebody has to pick a route the assembly can survive and the rules permit. Scores how far past the limit the defect sits, refuses a further thermal cycle once the re-braze budget or the cumulative exposure allowance is spent, never re-brazes a crack that has run into the parent metal, routes eroded parent metal away from more heat, demands an approved deviation before any use-as-is, and attaches the re-inspection each route owes. Trigger: ecss, q-st-70-40-brazing-scope, braze-defect-disposition, braze-rebraze-budget, braze-local-repair-route, braze-use-as-is-deviation, braze-cumulative-thermal-exposure, braze-rework-reinspection."
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
  tags: [ecss, q-st-70-40-brazing-scope, q7040-defect-disposition, braze-rebraze-budget, braze-local-repair-route, braze-use-as-is-deviation, braze-cumulative-thermal-exposure, braze-rework-reinspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Brazing — Defect Disposition (space-systems/ecss/q7040-defect-disposition)

Use when the task is what happens after a brazement fails acceptance --
choosing between re-brazing the joint, repairing it locally, carrying
it on an approved deviation, or scrapping it, and stating what has to
be re-inspected afterwards.

## Domain quick reference

- Disposition starts with how far past the limit the defect actually
  sits. A joint a few percent outside its class is a rework
  candidate; one several times outside is evidence the process ran
  wrong, and reworking it only buys a second defective joint with
  more heat in it.
- Re-brazing is a thermal cycle, and thermal cycles are a finite
  resource. Each one re-melts the filler, coarsens the joint
  microstructure, grows the diffusion zone into the parent metal and
  consumes part of the assembly's declared exposure allowance. The
  budget is counted, and once it is spent the route is closed
  whatever the defect looks like.
- A crack that has run into the parent metal is not a braze defect.
  Re-melting the filler does nothing to a crack in the base material
  and adds heat to its tip; that case leaves the rework routes
  entirely.
- Eroded parent metal is made worse by more heat. Erosion happens
  because molten filler dissolved the base metal, so a second cycle
  attacks the remaining wall; the route is mechanical, and where the
  erosion sits in the load path there is no route at all.
- Mechanical defects want mechanical repairs. Entrapped flux and
  excess filler are removed, not re-melted, and a local repair spends
  no part of the thermal budget.
- Use-as-is is a paperwork route with an engineering precondition. It
  needs an approved deviation on file and a defect that is not in the
  load path; without both it is a reject wearing a signature.
- Rework restarts the inspection, it does not inherit the old result.
  Whatever method found the defect has to find it gone, visual
  inspection is repeated, and a hermetic joint owes its leak test
  again, because the rework cycle can open a path the original test
  had already passed.
- The bound is a comparison, and a defect sitting exactly on it is
  within it. The ratio of a measurement to its limit is a quotient of
  measured quantities, so the comparison absorbs representation
  error rather than scrapping hardware on the last bit.

## Workflow

1. Normalise the defect: type, location, joint class, the measured
   value with its limit and direction, the re-braze count already
   spent, the thermal cycles used against the allowance, whether a
   deviation is approved, whether the joint is hermetic, and the
   method that found it.
2. Score the severity ratio in the direction the criterion runs, and
   dispose the defect as accept-as-is where it is in fact within its
   limit and is not one of the defects rejected on existence.
3. Take the defects that leave the rework routes first: a crack in
   the parent metal, and eroded parent metal in the load path.
4. Send the mechanical defects to local repair, which costs no
   thermal cycle.
5. For the remaining braze defects, test the rework bound, then the
   re-braze budget, then the cumulative exposure allowance, in that
   order, and take the first route still open.
6. Where no rework route is open, test the deviation route: an
   approved deviation and a defect out of the load path. Otherwise
   reject and scrap.
7. Attach the re-inspection the chosen route owes and report the
   re-braze attempts remaining.

## Pitfalls

- Re-brazing a joint that is far outside its limit. The severity
  ratio is telling you the gap, the fixture, the cleaning or the
  filler placement was wrong; a second run with the same setup
  reproduces the defect and spends a cycle doing it.
- Counting only the re-braze attempts and not the cumulative thermal
  exposure. An assembly that has been through a braze cycle, a
  post-braze heat treatment and a repair cycle can be out of exposure
  allowance while its re-braze counter still reads one.
- Re-melting a joint to chase a crack that started in the parent
  metal. The filler was never the problem, and the cycle puts heat
  into a crack tip in material that has no filler to reflow.
- Adding heat to an eroded joint. The erosion is dissolved parent
  metal; another molten cycle dissolves more of what is left, and the
  wall that was marginal becomes a hole.
- Treating an approved deviation as a route for any defect. A
  deviation covers a defect nobody needs to be sound; a defect in the
  load path is not that, however senior the signature.
- Releasing reworked hardware on the original inspection record. The
  rework changed the joint, so the record describes a joint that no
  longer exists, and a leak path opened during the repair cycle is
  invisible to it.

## Behavior contract (gate 3)

Defect normalisation, the severity ratio in both criterion directions,
the parent-metal and erosion exits, the mechanical repair route, the
re-braze budget and exposure allowance tests, the deviation
precondition and the re-inspection duty are exercised by the gate 3
contract test: scripts/test_q7040_defect_disposition.py against
scripts/q7040_defect_disposition_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7040_defect_disposition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
