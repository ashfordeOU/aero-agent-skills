---
name: q7029-applicability-and-purpose
description: "Scope an item for the offgassing determination of ECSS-Q-ST-70-29, whose purpose is what a material releases into breathable cabin air rather than what it loses to vacuum. Decide whether the item shares the crew atmosphere, credit only a containment with no vent path, compute the loading as exposed mass over free cabin volume, choose between a material-level test and an assembled-article test from the material count and the build processes applied, judge whether an existing report still covers the article as flown, and return the requirement areas an in-scope item takes on. Use when deciding whether crewed-compartment hardware needs testing. Trigger: ecss, q-st-70-29, offgassing-scope-eligibility, crew-atmosphere-exposure, offgassing-test-route-selection, offgassing-cabin-loading-threshold, offgassing-prior-report-reuse."
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
  tags: [ecss, q-st-70-29-offgassing-determination, q-st-70-29, q7029-applicability-and-purpose, offgassing-scope-eligibility, crew-atmosphere-exposure, offgassing-test-route-selection, offgassing-cabin-loading-threshold, offgassing-prior-report-reuse]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Applicability and Purpose (space-systems/ecss/q7029-applicability-and-purpose)

Use when the task is the scope question of ECSS-Q-ST-70-29: whether an item
needs an offgassing determination at all, by which route it would be tested,
and which requirement areas it takes on once it is inside scope.

## Domain quick reference

- The purpose is breathable air, not vacuum. Offgassing asks what a material
  releases into a cabin at living temperature and pressure; vacuum outgassing
  asks what it loses to space. A material can be excellent at one and
  unacceptable at the other, and the two screenings do not substitute.
- Scope follows the atmosphere, not the function. A bracket, a label, a
  stowage bag and a laptop strap are all in scope if they sit in the volume
  the crew breathes, and none of them are if they sit outside it.
- Containment counts only when it is real. A sealed enclosure with no vent
  path removes the exposure; a closed box, a gasketed cover or a ventilated
  housing does not, and treating the third as the first is the most common
  way an item disappears from the materials list.
- What matters is a concentration, so both the exposed mass and the free
  volume are part of the question. The same component is a negligible loading
  in a module and a significant one in a small capsule.
- A small loading is an argument for leaning on existing data, not for
  skipping the question. Without a database entry behind it the threshold has
  nothing to lean on and the item is back in scope.
- Several materials, or a process applied during the build, mean the article
  is tested as an article. Adhesive, coating, potting and cleaning residue
  offgas in their own right, exist only on the assembly, and are invisible to
  a material-level screening of any constituent.
- A prior report covers the article that was tested. A material
  substitution, a changed cure or a new supplier ends that coverage however
  recent the report is, because the article flying is no longer the one in
  the chamber.

## Workflow

1. Resolve the location and the containment into an exposure disposition, and
   stop at outside-scope when the item does not share the crew atmosphere.
2. Compute the cabin loading as exposed mass over free volume.
3. Test the loading against the negligible threshold, and require a database
   entry before letting a small loading stand in for a determination.
4. Choose the route: assembled article when the material count reaches the
   threshold or any build process was applied, material level otherwise.
5. Test an existing report for age and for changes of material, process,
   supplier, cure or surface treatment since it was issued.
6. Return the disposition — outside scope, covered by database, covered by
   prior report, or within scope — with the loading, the route and its
   reasons, and the requirement areas an in-scope item now carries.

## Pitfalls

- Reusing the vacuum outgassing screening as offgassing evidence. The test
  conditions, the analytes and the acceptance criteria are all different, and
  the compounds that matter to a crew are not the ones that condense on optics.
- Crediting a box as containment. If air can move in and out of it, so can
  everything the contents release.
- Scoping by function rather than by location. The materials list ends up
  full of equipment and empty of the soft goods, labels and cable ties that
  carry most of the exposed area.
- Judging the loading on mass alone. The same insert is negligible in a large
  module and governing in a capsule, and the free volume is the half of the
  quotient that gets left out.
- Waving an item through on a small loading with no data behind it. The
  threshold is a route into the database, not an exemption from it.
- Screening the constituents of a bonded assembly instead of the assembly.
  The adhesive and its cure are exactly what the crew will smell, and no
  constituent test contains them.
- Reusing a report across a supplier change. The formulation behind a trade
  name is not a constant, and the report describes the batch that was tested.

## Behavior contract (gate 3)

The exposure disposition for crewed and external locations, real versus
apparent containment, the cabin-loading quotient and its threshold, the
database-entry condition, the material-count and build-process route
selection, prior-report age and change invalidation and the requirement-area
set are exercised by the gate 3 contract test:
scripts/test_q7029_applicability_and_purpose.py against
scripts/q7029_applicability_and_purpose_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7029_applicability_and_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
