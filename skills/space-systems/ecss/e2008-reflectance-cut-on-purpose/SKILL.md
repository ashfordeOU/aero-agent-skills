---
name: e2008-reflectance-cut-on-purpose
description: "Use when a coating reflectance report has to justify the cut-on figure it quotes. Determine why the cut-on wavelength is recorded when a high reflectance band of a coverglass coating is characterised under ECSS-E-ST-20-08C clause 8.7.5.2.2: group the declared drivers that want the band edge and map each to the budget it feeds, test whether the plateau is tall enough for a band to exist at all, check the scan brackets the edge it claims to place, and hold the cut-on against the edge the thermal and power budgets assume, naming which way an out-of-tolerance edge moved. Trigger: ecss, e-st-20-08c-clause-8-7-5-2-2, reflectance-cut-on-purpose, high-reflectance-band-edge-placement, coating-plateau-reflectance-trigger, cut-on-scan-bracket-coverage, coverglass-coating-band-budget."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-on-purpose, reflectance-cut-on-purpose, high-reflectance-band-edge-placement, coating-plateau-reflectance-trigger, cut-on-scan-bracket-coverage, coverglass-coating-band-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Reflectance Cut-On Purpose (space-systems/ecss/e2008-reflectance-cut-on-purpose)

Use when the task is to state and defend why the cut-on wavelength is
recorded during the high reflectance band characterisation of
ECSS-E-ST-20-08C clause 8.7.5.2.2 -- which budgets want the band edge,
whether there is a band to place an edge on, whether the scan can place
it, and whether the edge landed where the design assumed.

## Domain quick reference

- A reflecting coating is bought for where its band sits, not only for
  how tall the band is. The plateau reflectance says how well the
  coating rejects inside the band; it says nothing at all about where
  the band starts, and the cut-on is the one number that does.
- Three budgets are written against that edge and they pull in opposite
  directions. Thermal control wants the rejection band wide enough to
  cover the load; array power wants it to stop short of the wavelengths
  the cell converts; lot acceptance wants it in the same place run
  after run. A single plateau figure satisfies none of them.
- The direction of a miss matters more than its size. A cut-on below
  the required edge widens the rejection band into the cell's
  photo-response and is paid in array current; a cut-on above it leaves
  the low end of the rejection band uncovered and is paid in thermal
  margin. The two have opposite fixes and a bare magnitude hides which
  one happened.
- The cut-on is only worth recording when a band exists. Halving a
  reflectance that never rises to a high reflectance level puts an edge
  on a feature that is not a band, and the resulting wavelength is an
  artefact of the arithmetic.
- A scan has to bracket the edge before it can place it. A curve that
  starts already inside the edge, or stops before the band plateau,
  cannot supply either half of the definition, and a plateau recorded
  below the cut-on means the curve read was not a rising edge at all.
- Inadequate and out of tolerance are different outcomes. A scan that
  cannot place the edge has not shown the edge is wrong; reporting it
  as a placement shortfall accuses the coating of a defect the
  measurement never demonstrated.
- Two lots with the same plateau and a fifteen nanometre edge shift are
  two different coatings. Without the cut-on the acceptance record
  cannot tell them apart, and the drift only surfaces after
  environmental exposure when it can no longer be traced to a run.
- Coverage is a separate question from placement. An edge inside
  tolerance can still leave part of the required rejection band
  uncovered if the band ends early, so the covered fraction is reported
  alongside the edge offset.

## Workflow

1. Validate the declared policy first: the plateau a band has to reach,
   the tolerance the edge is judged against, and the margin the scan
   has to extend beyond the edge.
2. Group the declared drivers, refusing an unrecognised one rather than
   ignoring it, and map each to the budget the cut-on feeds it. Append
   the shared objective whenever any driver is present.
3. Report the in-band absorbed fraction from the plateau whatever the
   verdict, because that is the thermal number the plateau alone was
   ever able to give.
4. Decide whether the cut-on is required at all: a declared driver
   present and a plateau at or above the band threshold. A plateau
   landing exactly on the threshold earns the characterisation; the
   comparison tolerance absorbs representation error and the threshold
   does not move.
5. When it is required and no cut-on was measured, say so as its own
   outcome rather than defaulting the edge to the band requirement.
6. When a cut-on exists, check the scan first: far enough below the
   edge, reaching the band plateau, and with the plateau above the
   cut-on. An inadequate scan closes the assessment before the edge is
   judged.
7. Only then take the signed offset against the required edge, the
   margin against the tolerance, the direction the edge moved and the
   fraction of the required rejection band the measured band covers,
   and close on one verdict.

## Pitfalls

- Accepting a coating on its plateau. The plateau is the easy half of
  the characterisation and the half that does not move much between
  runs; the edge is the half the budgets are written against.
- Reporting the magnitude of an edge miss without its direction. Twenty
  nanometres low and twenty nanometres high read identically on a
  summary line and are fixed by opposite changes to the deposition.
- Reading an inadequate scan as an out-of-tolerance edge. A curve that
  cannot bracket the edge has demonstrated nothing about where the edge
  is, and turning that into a coating defect raises a non-conformance
  against the wrong article.
- Placing a cut-on on a coating with no high reflectance band. Half of
  a low reflectance is still a number, and it will be quoted as an edge
  by anyone who reads the report without the plateau beside it.
- Treating a declared driver as sufficient reason to characterise. A
  coating whose plateau never reaches the band threshold buys nothing
  from a cut-on that the plateau measurement did not already give.
- Assuming an in-tolerance edge means the band is covered. Placement
  and coverage are separate: a band that ends early leaves part of the
  requirement uncovered with its edge perfectly placed.
- Comparing an offset with its tolerance by bare arithmetic. The offset
  is a difference of two measured wavelengths, so an edge meant to sit
  exactly on the tolerance can evaluate a few units in the last place
  to either side; the comparison absorbs that representation error
  while the tolerance stays untouched.

## Behavior contract (gate 3)

The policy validation, the driver grouping and budget mapping, the
in-band absorbed fraction, the band-existence threshold, the scan
bracket check, the signed edge offset with its direction and margin,
the required-band coverage fraction and the purpose verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_reflectance_cut_on_purpose.py against
scripts/e2008_reflectance_cut_on_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_reflectance_cut_on_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
