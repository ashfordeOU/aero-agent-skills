---
name: e2008-reflectance-cut-on-requirement
description: "Determine whether a coverglass coating's cut-on sits on its source control drawing figure. Use when a coverglass lot is offered for acceptance and its band edge has to be reconciled with the drawing under ECSS-E-ST-20-08C clause 8.7.5.2.3: take the cut-on from the rising edge at half of absolute measured reflectance, compare it against the drawing nominal and tolerance, report the signed deviation, and keep a drawing carrying no cut-on entry apart from a lot nobody measured. Trigger: ecss, e-st-20-08c-clause-8-7-5-2-3, coverglass-reflectance-cut-on, coverglass-source-control-drawing-match, cut-on-tolerance-band-deviation, reflectance-half-of-absolute-crossing, coverglass-coating-band-edge-acceptance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reflectance-cut-on-requirement, coverglass-reflectance-cut-on, coverglass-source-control-drawing-match, cut-on-tolerance-band-deviation, reflectance-half-of-absolute-crossing, coverglass-coating-band-edge-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reflectance Cut-On Requirement (space-systems/ecss/e2008-reflectance-cut-on-requirement)

Use when the task is to hold the cut-on of a coverglass reflectance
coating against the figure frozen into its source control drawing under
ECSS-E-ST-20-08C clause 8.7.5.2.3 -- what the drawing asks for, what the
measured spectrum delivers, and how far apart the two are allowed to be.

## Domain quick reference

- The coating is bought to a drawing, not to a preference. One cut-on
  figure sits in the source control drawing, and the requirement is that
  the coating the lot delivers puts its short-wavelength band edge on
  that figure inside the tolerance the drawing allows.
- The cut-on is taken the same way its long-wavelength partner is: the
  half level is half of the ABSOLUTE measured reflectance peak, and the
  cut-on is the short-wavelength point at which the rising edge crosses
  it. The level follows the coating, not a nominal 100 percent.
- Normalising the trace to a reference before taking the half level
  moves that level and therefore moves the reported cut-on. A coating
  compared on one basis to a drawing written on another is not compared
  at all.
- A drawing carrying no cut-on entry, a lot nobody measured, a band too
  weak for a half level to mean anything, and a rising edge that never
  crosses inside the scan are four distinct outcomes with four different
  owners. Only the last of them is an optical result.
- An absent drawing entry is not a cut-on of zero and an unmeasured lot
  is not a lot at the nominal. Each is reported as the gap it is.
- The deviation is signed. A cut-on long of the drawing figure and one
  short of it fail the same tolerance and mean opposite things about the
  deposition run, so the sign is carried through to the report.
- The tolerance is the drawing's, not the assessor's. A tighter window
  turns the same measured lot around, which is why the figure is read
  out of the drawing block rather than assumed.

## Workflow

1. Validate the acceptance policy first: default tolerance, minimum
   usable peak, scan-point floor and reflectance ceiling. A peak floor
   above the ceiling is refused rather than used.
2. Read the drawing block. A drawing with no cut-on entry, or an absent
   drawing, closes immediately on its own verdict; a missing drawing key
   in the case is an error, because it is not the same statement.
3. Read the measurement block. No block, or a block with no trace, is a
   data gap and closes on its own verdict with the drawing window still
   reported.
4. Validate the trace: increasing wavelengths, reflectance between zero
   and the ceiling, enough points to interpolate. Take the absolute peak
   and halve it.
5. Refuse a band whose peak is under the usable floor before taking any
   edge from it, and refuse a half level taken on a normalised basis
   rather than the absolute one.
6. Interpolate the rising-edge crossing to get the cut-on, then derive
   the signed deviation from the drawing figure and test it against the
   tolerance. A deviation landing exactly on the tolerance edge passes;
   the comparison tolerance absorbs representation error.
7. Close on one verdict: drawing entry missing, cut-on not measured,
   band too weak, cut-on not resolved, half-level basis misapplied,
   cut-on outside tolerance, or cut-on matches drawing.

## Pitfalls

- Taking the half level from a normalised trace. Half of a nominal 100
  percent is not half of what the coating reflects, and the two move the
  cut-on in opposite directions on a band that under- or over-performs.
- Reading a missing drawing entry as a pass. Nothing was compared; the
  procurement gap is the finding, and it belongs to a different desk
  than an optical deviation does.
- Treating an unmeasured lot as a lot at the nominal. The drawing figure
  describes what was ordered, never what arrived.
- Quoting the deviation unsigned. Which side of the drawing the edge
  landed on is what tells the deposition run what moved.
- Taking a cut-on from a scan that starts inside the band. The rising
  edge is below the shortest wavelength measured, so the number is an
  extrapolation wearing a decimal point.
- Assuming a tolerance. The drawing carries one; a default is what a
  policy lends when the drawing block genuinely omits it, and that
  substitution is reported rather than buried.

## Behavior contract (gate 3)

The policy validation, trace validation, absolute peak and half level,
band strength floor, rising-edge resolvability, cut-on interpolation,
drawing figure and tolerance readback, tolerance band, signed deviation,
half-level basis handling and the requirement verdict are exercised by
the gate 3 contract test:
scripts/test_e2008_reflectance_cut_on_requirement.py against
scripts/e2008_reflectance_cut_on_requirement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_reflectance_cut_on_requirement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
