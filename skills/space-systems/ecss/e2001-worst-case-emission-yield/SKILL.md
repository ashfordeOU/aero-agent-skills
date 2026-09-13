---
name: e2001-worst-case-emission-yield
description: "Use when derive the worst-case secondary-electron-emission-yield curve that a multipaction assessment has to use under ECSS-E-ST-20-01C clause 9.3: take the set of measured yield-versus-primary-electron-energy curves held for one surface condition, restrict them to the energy interval they all cover, interpolate each curve onto the shared energy grid, take the highest yield value at every primary-electron-energy, and report the resulting envelope with its peak, the first and second crossover-energies where it passes unity, and which measured curve drives each grid point. Trigger: ecss, e-st-20-01c, secondary-electron-emission-yield, sey-curve-envelope, primary-electron-energy, crossover-energy, worst-case-yield-envelope, multipaction-susceptibility."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-worst-case-emission-yield, secondary-electron-emission-yield, sey-curve-envelope, crossover-energy, primary-electron-energy, multipaction-susceptibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Worst-Case Emission Yield (space-systems/ecss/e2001-worst-case-emission-yield)

Use when the task is the clause 9.3 construction of ECSS-E-ST-20-01C:
several measured secondary-electron-emission-yield curves exist for the
same surface condition, and the multipaction assessment needs the single
worst-case curve built from them — the highest yield value at each
primary-electron-energy, not an average and not a favourite sample.

## Domain quick reference

- A measured yield curve maps primary-electron-energy (eV) to the number
  of secondary electrons released per incident electron. It rises from
  near zero at low energy, crosses unity at the first crossover-energy,
  reaches a peak, and falls back through unity at the second
  crossover-energy. Between the two crossovers the surface releases more
  electrons than it absorbs, which is the window a multipaction discharge
  can grow in; outside that window the electron population decays.
- Sample-to-sample scatter is real: two coupons of the same material and
  the same process give different curves, and no single coupon is the
  worst one everywhere. The worst-case curve is therefore built
  point-by-point — at each energy the envelope takes the largest yield any
  measured curve shows there, so different curves can drive different
  parts of the envelope. Recording which curve drives each point keeps the
  envelope traceable to real measurements.
- The envelope is only defined where every curve carries data. Outside the
  common energy interval a curve would have to be extrapolated, and an
  extrapolated yield has no measurement behind it, so the envelope is
  restricted to the overlap and the assessment energy range is checked
  against that overlap rather than against one curve.
- Because the envelope is an upper bound, its crossovers sit wider apart
  than any individual curve's and its peak is at least as high as the
  highest measured peak. That is the intended conservatism: the
  susceptibility window read off the envelope encloses the window of every
  contributing sample.

## Workflow

1. Validate every curve: an identifier, at least three points, strictly
   increasing and positive energies, finite non-negative yields. Reject a
   curve with duplicated or out-of-order energies rather than sorting it
   silently — the ordering defect usually means two runs were merged.
2. Compute the common energy interval as the highest of the curve minima
   to the lowest of the curve maxima. An empty or degenerate overlap is an
   error, not an empty envelope.
3. Build the shared energy grid from the union of every measured energy
   that falls inside the overlap, plus the two interval endpoints, with
   near-duplicate energies collapsed so a single point is not evaluated
   twice.
4. At each grid energy, interpolate every curve linearly between its
   bracketing measured points and keep the largest value, together with
   the identifier of the curve that produced it.
5. Read the envelope: peak yield and the energy it sits at; the first and
   second crossover-energies, found by interpolating the envelope to
   unity, where a grid point that already sits at unity is itself the
   crossing.
6. Compare the envelope against the assessment need — the energy range the
   analysis reads back, and any allowable peak-yield the project set — and
   state whether the surface supports sustained emission growth at all
   (an envelope that never reaches unity does not).

## Pitfalls

- Averaging the curve set, or picking the curve with the highest peak and
  using it everywhere. Both understate the envelope: the high-peak curve
  is frequently not the highest one near the first crossover, which is
  where the susceptibility window opens.
- Extrapolating a short curve to the ends of the widest one so that "all
  curves cover the range". The extra span is invented, and it lands
  exactly where the low-energy behaviour decides the first crossover.
- Reading the first grid point above unity as the first crossover-energy.
  The crossing sits between grid points and has to be interpolated; the
  grid is only as fine as the measurements behind it.
- Treating an envelope value that equals unity as already unstable. The
  comparison against unity must absorb floating-point representation
  error, so a point exactly at unity is a crossing, not an exceedance.
- Dropping the driving-curve identifier. Without it a reviewer cannot tell
  a genuine sample-to-sample spread from one bad measurement run pushing
  the whole envelope up.

## Behavior contract (gate 3)

The curve validation, overlap, interpolation, envelope, peak and
crossover logic is exercised by the gate 3 contract test:
scripts/test_e2001_worst_case_emission_yield.py against
scripts/e2001_worst_case_emission_yield_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_worst_case_emission_yield.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
