---
name: e20-array-fed-reflector-antennas
description: "Use when verify that an array-fed reflector antenna satisfies both provision families of ECSS-E-ST-20C clause 7.2.2.2.4 at once: confirm the dossier declares and verifies a reflector provision and a radiating-array provision, categorize each beam as single-feed-per-beam or multiple-feed-per-beam, turn the reflector profile error into a ruze-surface-efficiency, trade the feed-cluster edge-taper between illumination and spillover, fold in the feed-cluster excitation efficiency, convert a laterally displaced feed into a beam-deviation-factor, a beam squint and an offset in beamwidths, charge the resulting scan-loss and beam-forming-network loss, and grade every realized beam gain against its requirement. Trigger: ecss, e-st-20c-clause-7-2-2-2-4, array-fed-reflector-antenna, dual-provision-coverage, feed-cluster-illumination, ruze-surface-efficiency, beam-deviation-factor, multiple-feed-per-beam, beam-scan-loss-budget."
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
  tags: [ecss, e-st-20-electrical-scope, e20-array-fed-reflector-antennas, array-fed-reflector-antenna, dual-provision-coverage, feed-cluster-illumination, ruze-surface-efficiency, beam-deviation-factor, multiple-feed-per-beam, beam-scan-loss-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Array-Fed Reflector Antennas (space-systems/ecss/e20-array-fed-reflector-antennas)

Use when the task is the clause 7.2.2.2.4 case of ECSS-E-ST-20C -- an
antenna whose feed is itself a radiating array illuminating a
reflector. The clause point is that such an antenna is not a reflector
with an unusual feed, nor an array with an unusual load: both the
reflector provisions and the radiating-array provisions apply to it,
simultaneously, and the design closes only when both families are
declared, verified and reconciled in one gain budget.

## Domain quick reference

- Provision coverage is the first check, before any number. The design
  dossier carries provisions tagged to a family: reflector (profile
  accuracy, illumination, rim spillover, focal geometry) and
  radiating-array (element excitation, feed-cluster control, network
  loss, beam formation). A dossier carrying one family is incomplete by
  construction, and a provision that is declared but not verified is a
  finding, not a pass.
- Reflector side. The profile error of the dish costs a
  ruze-surface-efficiency term that falls exponentially with the square
  of the RMS error measured in wavelengths; beyond a small-error ratio
  the exponential model stops being trustworthy and a dedicated
  scattering assessment replaces it. The feed-cluster edge-taper then
  sets two competing terms: illumination efficiency, which is best when
  the rim is illuminated as strongly as the centre, and spillover
  efficiency, which is best when the rim is illuminated as weakly as
  possible. Their product has an interior optimum, so neither term is
  optimised alone.
- Feed-array side. The cluster of radiating elements that forms one
  beam carries its own excitation efficiency -- a non-uniform cluster
  taper costs gain exactly as a non-uniform lattice taper does -- and
  the beam-forming-network that drives it carries a dissipative loss
  that is charged once, on every beam it feeds.
- Offset feeds. A beam is steered by exciting a cluster displaced from
  the focal point. The displacement does not map one-to-one to beam
  angle: a beam-deviation-factor, set by the focal-length-to-diameter
  ratio, scales it, and the deeper the dish the further the realized
  beam falls short of the geometric prediction. The squint is then
  expressed in beamwidths of the reflector and charged as a scan-loss
  that grows with the square of that offset.
- Every beam is graded separately. A multi-beam array-fed reflector
  passes only when its worst beam -- normally the most displaced one --
  still meets its own gain requirement with its own losses charged.

## Workflow

1. Read the provision list and resolve coverage: both the reflector
   family and the radiating-array family must be present, with no
   duplicate provision identity, no unrecognised family, and no
   unverified entry.
2. Categorize the feed arrangement of each beam as single-feed-per-beam
   or multiple-feed-per-beam; reject a beam declared with no feed.
3. Compute the reflector-side efficiency terms: ruze-surface-efficiency
   from the RMS profile error, illumination efficiency and spillover
   efficiency from the feed-cluster edge-taper.
4. Compute the feed-array-side term: the excitation efficiency of the
   cluster amplitudes. Multiply all terms into one total efficiency and
   convert it into the on-axis gain of the reflector at its diameter in
   wavelengths.
5. For each beam, convert the lateral feed displacement into a
   beam-deviation-factor, a squint angle, and an offset expressed in
   beamwidths; charge the scan-loss that offset implies.
6. Subtract the scan-loss and the beam-forming-network loss from the
   on-axis gain to get the realized gain of that beam, and compare it
   with the gain the beam is required to deliver.
7. Aggregate: the antenna is compliant only when both provision
   families are complete and verified and every beam holds its
   requirement.

## Pitfalls

- Assessing the antenna under one provision family. Applying only the
  reflector provisions leaves the cluster excitation and the
  beam-forming-network loss uncharged; applying only the
  radiating-array provisions leaves the profile error and the rim
  spillover uncharged. Clause 7.2.2.2.4 exists because both omissions
  are common.
- Optimising the edge-taper for illumination alone. Illuminating the
  rim hard maximises the taper term and wastes the radiation that
  misses the dish; the quantity to maximise is the product, and it
  peaks well inside the range either term prefers.
- Mapping feed displacement straight to beam angle. Without the
  beam-deviation-factor the predicted squint is optimistic, and the
  error grows as the dish gets deeper, so the beams furthest off axis
  are exactly the ones mispredicted most.
- Charging scan-loss linearly. The loss grows with the square of the
  offset in beamwidths, so a cluster placed twice as far off axis costs
  four times the gain, and a budget built on a linear extrapolation
  from a near-axis beam understates the edge-of-coverage beam.
- Reporting an average beam gain. The requirement is per beam; an
  average hides the displaced beam that fails, which is the one the
  coverage depends on.

## Behavior contract (gate 3)

The provision-family coverage, feed-arrangement categorisation,
surface, illumination, spillover and feed-cluster efficiency terms,
beam-deviation-factor, squint, scan-loss, per-beam gain budget and the
aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e20_array_fed_reflector_antennas.py against
scripts/e20_array_fed_reflector_antennas_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e20_array_fed_reflector_antennas.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
