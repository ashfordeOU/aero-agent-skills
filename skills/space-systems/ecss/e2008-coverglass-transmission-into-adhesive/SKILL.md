---
name: e2008-coverglass-transmission-into-adhesive
description: "Use when a bonded-stack coverglass transmission scan must be reduced and dispositioned. Compute the into-adhesive spectral transmission of a coverglass from a scan taken through a fused-silica or uncoated backing piece bonded behind the sample per ECSS-E-ST-20-08C clause 8.7.9: qualify the backing piece and its bond, check the scan covers the specified band with ascending, closely spaced points and a referenced baseline, divide the backing reference scan out, integrate the band average by trapezoid, and test the gain over the into-air figure against the Fresnel loss the removed rear air interface accounts for. Trigger: ecss, e-st-20-08c-clause-8-7-9, coverglass-transmission-into-adhesive, coverglass-backing-piece-bond, coverglass-bonded-stack-scan, coverglass-band-average-transmittance, coverglass-rear-interface-fresnel-loss."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-transmission-into-adhesive, coverglass-backing-piece-bond, coverglass-bonded-stack-scan, coverglass-band-average-transmittance, coverglass-rear-interface-fresnel-loss, coverglass-backing-reference-scan, solar-cell-assembly-optical-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Transmission Into Adhesive (space-systems/ecss/e2008-coverglass-transmission-into-adhesive)

Use when the task is the transmission measurement of ECSS-E-ST-20-08C
clause 8.7.9 -- a spectrophotometer scan taken with a silica or uncoated
backing piece bonded behind the coverglass, so the light leaves into an
adhesive rather than into air, reduced to the band figure that closes the
clause.

## Domain quick reference

- The backing piece exists to remove an interface. A coverglass alone in
  the instrument has an air interface on its far face and the scan
  carries the Fresnel reflection there. Bonded to a cell it does not. A
  silica or uncoated backing piece bonded on with the flight adhesive
  reproduces the flight interface, and the figure that comes out is the
  one the assembly will actually have.
- The backing piece is part of the instrument, not part of the sample.
  The stack scan carries the backing's own bulk absorption and its own
  rear air interface. A reference scan of the backing bonded in the same
  configuration divides both out. The raw stack figure understates the
  coverglass by whatever the backing costs.
- A coated backing piece is not a backing piece. It puts a second
  coating in the beam and the two coatings cannot be separated
  afterwards; the same goes for a backing whose index sits far from the
  adhesive, which reintroduces the very interface the method removes.
- A void in the bond is an air gap wearing the adhesive's name. The
  measurement it produces is a partial into-air scan and belongs to
  neither clause.
- The result is checkable. Removing the rear air interface buys a
  Fresnel ratio of a few percent, computable from the glass, adhesive
  and air indices. A corrected figure that beats the into-air figure by
  far more than that is a reduction with the wrong reference scan in it,
  not a better coverglass.
- Sampling interval and band coverage bind here exactly as they do on
  the into-air scan: a band average taken from a scan that stops short
  is extrapolation, and a gap wide enough to step over a coating feature
  reports an average the stack does not have.

## Workflow

1. Validate the stack policy: band, sampling interval, the three
   refractive indices, the bond void limit and the gain tolerance. An
   index below one or a coverglass index at the ambient index is refused
   rather than used.
2. Qualify the backing piece -- recognised material, uncoated, real
   thickness -- and check its index sits close enough to the adhesive.
   A coated or mismatched piece closes the assessment.
3. Check the bond void fraction against the policy limit before any
   optics are read.
4. Validate the stack scan and confirm a baseline calibration reference
   is attached; without one the reduction stops.
5. Compare the scan span against the band and the widest adjacent gap
   against the specified interval. Either failure stops the reduction.
6. Divide the backing reference scan out point by point, refusing a
   corrected transmittance above one rather than clipping it quietly.
   With no reference scan, report the stack figure and say what is still
   inside it.
7. Integrate the corrected band average by trapezoid with interpolated
   band edges.
8. When an into-air band figure for the same part is supplied, take the
   observed gain and compare it against the Fresnel prediction within
   the declared tolerance.
9. Judge the band average against the declared minimum and report the
   margin either way.

## Pitfalls

- Reporting the raw stack transmittance as the coverglass figure. The
  backing's absorption and its rear air interface are still in it.
- Using a coated backing piece because it was the coverglass to hand.
  The scan then describes two coatings and neither separately.
- Accepting a corrected transmittance above one by clipping it to one.
  That value is evidence the two scans were taken in different
  configurations, and clipping it destroys the evidence.
- Taking the gain over the into-air figure as proof of a good
  coverglass. The gain is bounded by the Fresnel ratio; anything much
  larger indicts the reduction.
- Comparing a band average with a required minimum by bare arithmetic.
  The average is a trapezoidal sum divided by a band width, so a stack
  exactly on the requirement can evaluate a few units in the last place
  below it; the comparison absorbs that representation error while the
  requirement stays untouched.
- Treating a void fraction the supplier did not state as zero. An
  unstated void is unknown, and the validator refuses it.

## Behavior contract (gate 3)

The stack policy validation, the backing qualification and bond void
check, the scan validation, band coverage and sampling-interval checks,
the backing reference division, the trapezoidal band average with
interpolated edges, the Fresnel interface gain and its plausibility
comparison, and the verdict against the declared minimum are exercised
by the gate 3 contract test:
scripts/test_e2008_coverglass_transmission_into_adhesive.py against
scripts/e2008_coverglass_transmission_into_adhesive_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_transmission_into_adhesive.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
