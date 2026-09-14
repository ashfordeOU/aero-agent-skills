---
name: q6013-class-1-material-restrictions
description: "Determine which declared materials and constructions bar a commercial EEE part from Class 1 space use. Use when ECSS-Q-ST-60-13C clause 4.2.2.2 is applied to a part's finishes, plating, encapsulation and vacuum outgassing data: cadmium and zinc barred outright, a pure-tin finish cleared only by a lead mass fraction reaching the declared whisker threshold, silver by a barrier underplate, plastic encapsulation by moisture level, bake record and dose environment, and mass loss and condensable material against their limits. Returns accepted, mitigation-required or prohibited per axis and rolls the worst into one construction verdict. Trigger: ecss, q-st-60-13c, class-1-restricted-part-materials, pure-tin-whisker-mitigation, cadmium-and-zinc-finish-bar, plastic-encapsulated-package-moisture, part-vacuum-outgassing-limits, lead-mass-fraction-threshold."
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
  tags: [ecss, q-st-60-commercial-eee-scope, q6013-class-1-material-restrictions, class-1-restricted-part-materials, pure-tin-whisker-mitigation, plastic-encapsulated-package-moisture, part-vacuum-outgassing-limits, lead-mass-fraction-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Material and Construction Restrictions (space-systems/ecss/q6013-class-1-material-restrictions)

Use when the task is the material screen of ECSS-Q-ST-60-13C clause
4.2.2.2 — deciding whether what a commercial part is actually made of
keeps it out of a Class 1 design. A part can satisfy every baseline
selection rule and still be unusable here, because those rules grade the
supply chain and this one grades the finishes, the package and the
material's behaviour in vacuum.

## Domain quick reference

- Finishes split three ways, not two. Most are accepted as declared.
  Cadmium and zinc are barred outright: the failure mechanism is the
  metal itself, so no process applied afterwards clears them and no
  mitigation is offered. A pure-tin finish is restricted rather than
  barred — it is admissible when enough lead is alloyed into the finish
  to suppress whisker growth, measured as a mass fraction against a
  declared threshold. Reporting restricted and barred as one state
  either costs a programme a part it could have kept or lets through one
  it could not.
- Silver sits in the same restricted band on a different mitigation: a
  declared barrier underplate against migration and tarnish.
- Encapsulation is conditional. A hermetic metal or ceramic package is
  accepted. A plastic-encapsulated part is not barred, but carries three
  conditions that are themselves data: a moisture sensitivity level at
  or below the declared limit, a bake-and-dry-pack record, and a total
  ionising dose environment within the declared limit for an unscreened
  plastic package. An undeclared package construction is barred, because
  no condition on it can be shown met.
- A missing condition is not a failed condition. The two are
  dispositioned by different people through different paperwork, so
  absence is carried in its own list and never merged into a failure.
- Outgassing is arithmetic: total mass loss and collected volatile
  condensable material are each compared with a declared limit, and a
  value sitting exactly on a limit is inside it. Those limits are round
  decimals that a measured value lands on often enough that the
  comparison absorbs representation error rather than deciding the case
  on the last bit.

## Workflow

1. Validate the part: a non-empty identifier, at least one declared
   finish, and a surface name unique across the part. The same surface
   declared twice is an input error, not two data points to merge.
2. Grade each finish against the material table — accepted, barred
   outright, or restricted with a named mitigation — and record the
   mitigation state separately from the verdict so a reviewer can see
   what would clear it.
3. For a pure-tin finish, compare the declared lead mass fraction with
   the declared threshold, absorbing representation error at the
   boundary. No declared fraction is unevidenced mitigation, which is
   its own state, not a failure.
4. Grade the encapsulation, splitting each condition into met, open or
   absent, and bar an undeclared construction.
5. Compare the declared mass loss and condensable material with their
   limits and return the margins, so a near-limit material is visible
   before it becomes a waiver.
6. Roll the three axes to the worst verdict: prohibited outranks
   mitigation-required, which outranks accepted.
7. Report the construction verdict, the worst axis, the surfaces grouped
   by verdict, the mitigations owed, and every finding with its numbers.

## Pitfalls

- Merging barred and restricted into one rejection. Cadmium and zinc
  have no mitigation at all, while pure tin and silver do; a single
  rejected state hides which of the two the project is looking at.
- Treating a plastic package as automatically barred. It is conditional,
  and the conditions are real data a supplier can produce — barring it
  up front throws away a part the clause would have admitted.
- Recording an undeclared moisture level as a failed one. Nobody has
  answered yet, and that is a different piece of work from a level that
  came back too high.
- Screening the finishes and stopping there. Outgassing can bar a part
  whose every finish is clean, and an undeclared package construction
  bars a part with no bad finish at all.
- Relaxing a declared limit to clear a value sitting exactly on it. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the declared limit stays as
  specified.

## Behavior contract (gate 3)

The material table split, the pure-tin lead mass fraction against its
threshold including the exact-boundary case, the silver barrier
underplate, the conditional encapsulation with absence kept apart from
failure, the outgassing limits at their exact bounds and the three-axis
roll-up are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_material_restrictions.py against
scripts/q6013_class_1_material_restrictions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_material_restrictions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
