---
name: e2008-bare-cell-acceptance-measurement-purpose
description: "Determine what the bare-cell electrical measurement of ECSS-E-ST-20-08C clause 7.3.2.2.1 has to deliver before the bench is switched on: map each declared acceptance decision onto the parameter that feeds it, derive the operating-point power and the fill-factor proxy from the short-circuit and on-load currents, combine the irradiance, temperature, area and instrument uncertainties in quadrature, then judge whether the result is narrow enough against the source control drawing band to separate a conforming cell from a rejected one. Use when scoping or reviewing a bare-cell acceptance measurement. Trigger: ecss, e-st-20-08c-clause-7-3-2-2-1, bare-cell-acceptance-measurement-purpose, bare-cell-short-circuit-current, bare-cell-current-at-test-voltage, bare-cell-measurement-uncertainty-budget, source-control-drawing-acceptance-band, bare-cell-acceptance-discrimination-ratio."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-acceptance-measurement-purpose, bare-cell-acceptance-measurement-purpose, bare-cell-short-circuit-current, bare-cell-current-at-test-voltage, bare-cell-measurement-uncertainty-budget, source-control-drawing-acceptance-band, bare-cell-acceptance-discrimination-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Bare Cell Acceptance Measurement Purpose (space-systems/ecss/e2008-bare-cell-acceptance-measurement-purpose)

Use when the task is to state and defend why the electrical parameters
of a bare cell are measured during acceptance testing under
ECSS-E-ST-20-08C clause 7.3.2.2.1 -- which acceptance decisions the
currents feed, what those currents imply about the cell, and whether
the measurement as planned can resolve the band it is being asked to
judge against.

## Domain quick reference

- A bare cell is the photovoltaic cell on its own, before a coverglass,
  an interconnector or a substrate is attached to it. Measuring it at
  this point isolates the cell's own behaviour from everything the
  assembly later adds, which is the only reason the measurement sits
  this early in the flow.
- The currents are not measured for their own sake. They feed lot
  conformity against the source control drawing, the on-load current an
  array string is sized from, the pre-environment baseline that later
  degradation is read against, and the grouping of a delivered batch
  into cells that may be laid down and cells that may not.
- Each decision leans on a particular parameter. A plan that records
  the short-circuit current alone can fix a degradation baseline and
  cannot size a string; a plan that records only the on-load current
  can size a string and has no baseline to compare against later.
- Two quantities follow immediately from the pair of currents and are
  what the decisions actually respond to. The on-load current times the
  stated test voltage is the operating point power. Divided by the
  product of short-circuit current and open-circuit voltage it becomes
  a fill-factor proxy -- the share of the current-voltage rectangle the
  cell occupies, and the first place a resistive or shunted cell shows
  itself.
- An acceptance limit defines a band between the drawing minimum and
  the nominal cell, and that band is what the measurement has to see
  into. Irradiance setting, cell temperature, illuminated area and
  instrument each contribute a relative uncertainty; being independent,
  they combine in quadrature rather than by addition.
- A run whose combined uncertainty is a large share of that band
  produces a record that looks like a decision and is not one. The
  ratio of band to uncertainty is the discrimination the plan has, and
  it is decided before the first cell is illuminated or not at all.

## Workflow

1. Validate the scoping policy first: the minimum discrimination ratio
   and the largest share of the acceptance band the uncertainty may
   occupy. A share above one, or a ratio below one, is refused rather
   than used.
2. Group the declared acceptance decisions, rejecting an unrecognised
   or duplicated one rather than ignoring it, and map each to the
   parameter it leans on. Append the shared objective -- a reproducible
   record with its illumination and temperature stated -- whenever any
   decision is present.
3. Take the union of the parameters those decisions need and compare it
   against what the plan measures. Report every missing parameter, not
   only the first, because each one is a decision left unserved.
4. Derive the operating point power and, where an open-circuit voltage
   is on record, the fill-factor proxy. Refuse an on-load current above
   the short-circuit current or a test voltage above the open-circuit
   voltage: neither describes a cell.
5. Combine the declared relative uncertainty components in quadrature.
   An empty budget is refused rather than treated as zero, because a
   plan with no declared uncertainty has been assumed perfect rather
   than scoped.
6. Compute the acceptance band as the shortfall of the drawing minimum
   below nominal, take the discrimination ratio, and compare it against
   the policy. A ratio landing exactly on the policy value is
   admissible; the comparison tolerance absorbs representation error
   and the policy value does not move.
7. Close on one verdict: no acceptance decision declared, measurement
   plan not established, parameter coverage incomplete, measurement
   cannot discriminate, or purpose established.

## Pitfalls

- Scoping the measurement from the instrument's capability instead of
  the drawing band. The band is fixed by the acceptance limit; a bench
  that resolves a per-cent when the band is a fraction of a per-cent
  cannot be argued into sufficiency by its datasheet.
- Adding the uncertainty components arithmetically. Independent
  contributions combine in quadrature, and adding them inflates the
  budget enough to reject plans that would have worked.
- Treating a zero uncertainty as the absence of a budget. An empty
  budget means nobody has looked, and it is the one case where a
  discrimination ratio is guaranteed to come out flattering.
- Quoting a fill factor computed from a stated test voltage as the
  cell's true fill factor. The maximum-power point is somewhere else;
  the proxy is a consistent indicator across a lot and not a
  performance figure to carry off the page.
- Reporting a single current and calling the acceptance decision fed.
  Conformity leans on both currents, and a record with one of them is a
  record the next reviewer has to go back to the bench to complete.

## Behavior contract (gate 3)

The policy validation, decision inventory and objective mapping, the
parameter coverage check, the operating point power and fill-factor
proxy, the quadrature uncertainty budget, the acceptance band and
discrimination ratio, and the purpose verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_bare_cell_acceptance_measurement_purpose.py against
scripts/e2008_bare_cell_acceptance_measurement_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_acceptance_measurement_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
