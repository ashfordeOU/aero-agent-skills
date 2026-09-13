---
name: e2008-pva-parts-and-materials-parameters
description: "Screen the parts, materials and processes list of a photovoltaic assembly against the parameters clause 5.3.2 of ECSS-E-ST-20-08C expects to be tracked: hold each entry to the parameter set its kind demands, report the share actually declared, screen a material on its total-mass-loss and condensable outgassing data, work out how much shelf life is left unspent at the planned point of use, disposition a part from the level it was procured at, and group every entry as tracked, waiver-bearing, not acceptable or incomplete. Use when a PVA declared components list, as-built record or procurement dossier has to be audited before build. Trigger: ecss, e-st-20-08c, pva-parts-materials-processes-parameters, pva-pmp-parameter-completeness, pva-material-outgassing-screening, pva-shelf-life-margin, pva-lot-traceability-parameters, pva-procurement-level-disposition."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-parts-and-materials-parameters, e-st-20-08c, pva-parts-materials-processes-parameters, pva-pmp-parameter-completeness, pva-material-outgassing-screening, pva-shelf-life-margin, pva-lot-traceability-parameters, pva-procurement-level-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Parts and Materials Parameters (space-systems/ecss/e2008-pva-parts-and-materials-parameters)

Use when the task is clause 5.3.2 of ECSS-E-ST-20-08C: the parts,
materials and processes that go into a photovoltaic assembly each carry
a parameter set that has to be tracked from procurement to the as-built
record. This leaf grades a declared list, screens what the parameters
say, and names every entry that is not yet good enough to build with.

## Domain quick reference

- The parameter set is not the same for the three kinds of entry. A
  part carries its identity, manufacturer, lot or batch, the
  specification it was bought against and the level it was procured at.
  A material carries the same identity trail plus its shelf life, the
  age it will have reached at the point of use, and its outgassing
  data. A process carries its identity, the process specification, the
  qualification behind it and the certification of the operator.
- An entry with an incomplete parameter set is not screened at all.
  There is nothing to screen, and a screen run on partial data returns
  a verdict the data cannot support -- so incompleteness is reported as
  its own outcome rather than folded into a pass or a fail.
- A material is screened twice. The outgassing data is held against the
  declared total-mass-loss and condensable limits, and the shelf life is
  held against the age the material will have reached when it is
  actually used, not the age it has today. A material that will expire
  mid-programme is caught by the second screen and nothing else.
- The screening limits are declared project policy, not physical
  constants. The defaults are the usual space-materials screening pair;
  a project with a sensitive optical surface may tighten them and the
  same entries then group differently.
- A part is dispositioned from its procurement level: space-qualified
  entries stand, upscreened commercial entries stand only on a waiver,
  and plain commercial entries do not stand. The level is a declared
  parameter, so an entry that omits it is incomplete rather than
  assumed qualified.
- The list rollup carries both a tracked fraction and a mean
  completeness fraction, because a list can be almost fully declared
  and still have every second entry waiting on a waiver.

## Workflow

1. Read each entry with its kind and its declared parameters. Reject an
   entry whose kind is not one of part, material or process rather than
   guessing which parameter set applies.
2. Hold the entry against the parameter set its kind demands, counting
   a blank string or an empty structure as undeclared. Report the
   missing names and the declared share, and stop there if anything is
   missing.
3. For a material, screen the outgassing data against the mass-loss and
   condensable limits, then compute the shelf life still unspent at the
   planned point of use as a fraction of the full span.
4. For a part, resolve the procurement level into a disposition from
   the policy table.
5. Decide the entry verdict: a failed outgassing screen or an expired
   material is not acceptable, a thin shelf life or an upscreened part
   carries a waiver, and everything else with a full parameter set is
   tracked.
6. Roll the list up: group the entries by verdict, report the tracked
   fraction, the mean completeness and every open entry by name, and
   return a list verdict that is only clean when nothing is open.

## Pitfalls

- Screening an entry whose parameter set is incomplete. A material with
  no outgassing data screens as silent rather than as failed, and a
  rollup built that way reports the cleanest sheet on the worst list.
- Reading shelf life against the age today rather than the age at the
  planned point of use. A material with a year left passes on receipt
  and is out of life by the time it reaches the laydown bench.
- Treating an expired material as a waiver case. A negative remaining
  life is not a thin margin; it is a different outcome, and merging the
  two hides it inside a waiver count that looks routine.
- Assuming a part with no declared procurement level is qualified. The
  level is one of the tracked parameters, and an absent one makes the
  entry incomplete rather than acceptable.
- Reporting only the tracked fraction. A list can be fully declared and
  still be unbuildable, which is why the completeness fraction and the
  verdict grouping are reported side by side.
- Judging an outgassing result that lands exactly on a screening limit
  by bare arithmetic. The limit is a round percentage and the result is
  read back from a report, so a value meant to sit on the limit can
  land a few units in the last place above it; the comparison absorbs
  that while the limit stays as declared.

## Behavior contract (gate 3)

The per-kind parameter set, completeness measurement, outgassing
screen, shelf-life margin, procurement disposition and the rolled-up
list verdict are exercised by the gate 3 contract test:
scripts/test_e2008_pva_parts_and_materials_parameters.py against
scripts/e2008_pva_parts_and_materials_parameters_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_pva_parts_and_materials_parameters.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
