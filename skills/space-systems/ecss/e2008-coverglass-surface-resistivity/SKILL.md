---
name: e2008-coverglass-surface-resistivity
description: "Determine whether a coverglass build obliges the resistivity measurement of ECSS-E-ST-20-08C clause 8.7.7 and whether its record discharges that obligation: decide from the declared coating stack whether a conductive layer forms part of the glass, refuse a layer whose conductivity nobody characterised rather than reading it as insulating, reduce each concentric-ring or four-point site through its geometry factor into ohms per square, hold the drive current and the bench ambient inside their bands, and judge the worst site against the drawing ceiling. Use when a coated coverglass lot is offered with no surface resistivity record. Trigger: ecss, e-st-20-08c-clause-8-7-7, coverglass-conductive-coating-applicability, coverglass-surface-resistivity-ohms-per-square, coverglass-concentric-ring-geometry-factor, coverglass-four-point-collinear-reduction, coverglass-resistivity-drawing-ceiling."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-surface-resistivity, coverglass-conductive-coating-applicability, coverglass-surface-resistivity-ohms-per-square, coverglass-concentric-ring-geometry-factor, coverglass-four-point-collinear-reduction, coverglass-resistivity-drawing-ceiling, coverglass-coating-charge-bleed-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Surface Resistivity (space-systems/ecss/e2008-coverglass-surface-resistivity)

Use when the task is clause 8.7.7 of ECSS-E-ST-20-08C -- the resistivity
measurement a coverglass owes whenever a conductive coating forms part
of it. The clause is conditional, and the condition is where it goes
wrong. A bare coverglass owes nothing here. A coverglass whose stack
includes a transparent conducting oxide owes a measurement from the day
the stack changed, not from the day someone remembers to add a line to
the test plan, and the coating exists to bleed surface charge, so the
number is the evidence that the bleed path works.

## Domain quick reference

- The obligation follows the build state, not the test plan. Ask the
  coating stack whether a conductive layer is present, then ask the
  record whether the measurement that answer demands was made.
- The two failure directions are not symmetric. Calling the measurement
  unnecessary on a stack nobody characterised ships a coverglass whose
  charge bleed was never shown. Calling it necessary on a plainly
  insulating stack costs bench time. Only one of those is recoverable.
- A material in neither the conductive nor the non-conductive list, with
  no declared conductivity, is an unknown. An unknown read as insulating
  is how the obligation disappears quietly, so an uncharacterised layer
  stops the judgement instead of defaulting to the easy answer.
- Surface resistivity is quoted in ohms per square because it does not
  depend on how big the square is. Getting there needs the fixture
  geometry: a concentric ring contributes 2 pi over the log of the
  diameter ratio, a collinear four-point array contributes pi over
  log 2 while the film continues well past the probes.
- That thin-film factor assumes a semi-infinite film. On a coverglass
  the article is small, so the probe span has to be checked against the
  specimen rather than assumed from the instrument's data sheet.
- A coating is rarely even. Several sites are read, the ceiling belongs
  on the worst of them because the slowest bleed path is the one that
  sets the discharge risk, and the spread across the sites is what says
  whether the deposition itself was under control.
- Oxide coating resistivity moves with adsorbed moisture, and the drive
  current has to sit inside the electrometer's usable band. A dry bench
  or a current at the end of the scale produces an instrument artefact
  that reads exactly like a coating figure.

## Workflow

1. Read the declared coating stack and decide, layer by layer, whether
   any of them conducts. Refuse an uncharacterised layer here rather
   than downstream, because everything after this depends on the answer.
2. If nothing conducts, close as not required and say so explicitly, so
   the absence of a measurement is a recorded decision rather than a
   gap.
3. If something conducts, ask the record for the evidence the
   measurement owes. A missing ceiling, route, ambient or site list
   leaves the obligation open rather than producing a partial verdict.
4. Reduce every site through the geometry of the fixture that read it,
   into ohms per square, and keep the per-site values rather than an
   average, since an average hides the worst path.
5. Hold the drive current of each site inside the electrometer band and
   the bench ambient inside the humidity band, because a reading taken
   outside either is not a coating property.
6. Judge the worst site against the drawing ceiling, report the spread
   across the sites, and close with a verdict that stays open while any
   finding stands.

## Pitfalls

- Reading an unlisted coating material as insulating. Nothing in the
  arithmetic that follows will look wrong, and the coverglass ships
  without the measurement the clause asked for.
- Deciding applicability from the test plan. The plan reflects the build
  someone wrote it against; a stack change after that date leaves the
  plan correct about the old article and silent about the new one.
- Averaging the site readings before applying the ceiling. A mean of a
  good site and a bad one passes a ceiling the bad site fails, and it is
  the bad site that holds the charge.
- Quoting a measured resistance as a surface resistivity. Without the
  fixture geometry factor the number is an ohm reading tied to one
  electrode pattern, and it does not transfer between benches.
- Using the collinear thin-film factor on a probe array that spans the
  specimen. The factor assumes the film continues past the probes; on a
  small coverglass it does not, and the derived figure is biased.
- Taking the measurement on a dry bench. An oxide coating reads a
  different resistivity with less adsorbed moisture, and the direction
  of that bias flatters a marginal coating.
- Comparing a reduced site value against a ceiling by bare arithmetic.
  A geometry factor is a ratio of logarithms and a ceiling is written in
  round numbers, so a value meant to land on the limit can miss it by a
  few units in the last place; the comparison absorbs that while the
  limit itself is never relaxed.

## Behavior contract (gate 3)

The conductive-layer decision, the refusal of an uncharacterised layer,
the not-required close, the missing-evidence hold, the concentric-ring
and four-point geometry factors, the probe-span check, the per-site
reduction, the worst-site ceiling comparison, the site spread ratio, and
the drive-current and ambient-humidity bands are exercised by the gate 3
contract test: scripts/test_e2008_coverglass_surface_resistivity.py
against scripts/e2008_coverglass_surface_resistivity_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_surface_resistivity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
