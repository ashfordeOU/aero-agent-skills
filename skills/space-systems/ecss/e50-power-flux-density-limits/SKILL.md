---
name: e50-power-flux-density-limits
description: "Compute the power flux density a spacecraft downlink puts on the Earth's surface and grade it against the limit that applies there, under ECSS-E-ST-50C clause 5.6.12.4: the limit is a schedule over angle of arrival, not one number, and the value graded against it is referred to the limit's reference bandwidth first. Derive flux from EIRP and slant range, apply the bandwidth referral, interpolate the limit at each arrival angle, and report per-angle margin, the governing angle and a three-way verdict. Use when assessing downlink flux density for coordination. Trigger: ecss, e-st-50-communications, power-flux-density-at-earth-surface, pfd-arrival-angle-limit-schedule, pfd-reference-bandwidth-referral, downlink-pfd-coordination-margin, spacecraft-downlink-flux-limit."
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
  tags: [ecss, e-st-50-communications, e50-power-flux-density-limits, power-flux-density-at-earth-surface, pfd-arrival-angle-limit-schedule, pfd-reference-bandwidth-referral, downlink-pfd-coordination-margin, spacecraft-downlink-flux-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Power Flux Density Limits (space-systems/ecss/e50-power-flux-density-limits)

Use when a downlink's flux density at the Earth's surface is being derived or
checked, per ECSS-E-ST-50C clause 5.6.12.4 — how much flux arrives, and
whether it is under the limit that applies at the angle it arrives from.

## Domain quick reference

- Two obligations, and one of them is a units question. The flux stays
  under the limit at the angle of arrival, and the value compared against
  that limit is stated in the bandwidth the limit is written in.
- The limit is a schedule, not a number. It is flat at low arrival angles,
  rises through a transition, and is flat again above it. A downlink that
  passes at the horizon can be well over the limit at high elevation, and
  quoting a single limit hides exactly that case.
- The governing case is the smallest margin, which is not the highest
  flux. The limit moves with the angle too, so the worst angle has to be
  searched for rather than assumed to be the closest approach.
- Bandwidth referral is not a rounding detail. A measurement taken in ten
  times the reference bandwidth spreads the power across it, and only the
  reference-bandwidth share counts; skipping the referral overstates the
  flux by ten decibels and kills a compliant design.
- The referral is one-directional. A measurement taken in a bandwidth no
  wider than the reference already has all of its power inside the
  reference bandwidth, so no correction applies and inventing one
  understates the flux.
- Working in decibels keeps the comparison to a subtraction. The only
  logarithms needed are the two that spread power over a sphere or a
  bandwidth, and both belong in one place.

## Workflow

1. State the reference bandwidth the limit is written in before anything
   is measured. Every number that follows is relative to it.
2. Declare the limit schedule as arrival-angle breakpoints. Two is the
   minimum that can be interpolated; the plateaus at each end are stated
   as breakpoints too so the shape is explicit.
3. Derive the flux at the surface from EIRP and slant range where it is
   not measured directly, keeping the spreading in one helper.
4. Refer each observation to the reference bandwidth before grading it,
   and report the correction alongside the value so a reviewer can see
   the referral was applied.
5. Interpolate the limit at each observation's own arrival angle.
6. Compute margin as limit minus referred flux, decide the verdict with a
   decibel tolerance, and separate an exceedance from a margin thinner
   than the coordination case asked for.
7. Report the governing angle across the profile, not only the count of
   exceedances. Which angle governs is what the mitigation is designed
   against.

## Pitfalls

- Grading one flux figure against one limit. The limit depends on arrival
  angle, and the pass geometry sweeps through it.
- Comparing a wideband measurement to a narrowband limit. The measurement
  is high by the bandwidth ratio in decibels, and the resulting redesign
  chases a problem that does not exist.
- Applying a bandwidth correction to a measurement narrower than the
  reference. All that power is already inside the reference bandwidth, so
  the correction understates the flux and hides a real exceedance.
- Assuming the closest approach governs. The limit relaxes with elevation
  and tightens near the horizon, so the smallest margin often sits at low
  elevation with a lower flux.
- Deciding the comparison with a bare strict inequality. A logarithm is
  not correctly rounded, so a flux that should land exactly on its limit
  can pass on one platform and fail on another.
- Treating a zero-decibel margin as compliance achieved. It is compliance
  measured once, and antenna pointing, unit variation and pass geometry
  all move it the wrong way.

## Behavior contract (gate 3)

Arrival-angle and bandwidth validation, limit-schedule normalisation and
interpolation with flat plateaus beyond the end breakpoints, spreading
loss and flux from EIRP, the one-directional bandwidth referral, the
three-way verdict with a decibel tolerance at the limit, and the
governing-angle search across a profile are exercised by the gate 3
contract test: scripts/test_e50_power_flux_density_limits.py against
scripts/e50_power_flux_density_limits_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_power_flux_density_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
