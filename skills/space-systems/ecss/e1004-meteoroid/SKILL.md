---
name: e1004-meteoroid
description: "Use when computing the meteoroid flux environment for a mission profile under ECSS-E-ST-10-04C clause 10.2.2.2/10.2.4 and Annex C: determine which meteoroid model components apply (the Grun-type sporadic background model plus any meteoroid stream active on the mission epoch), compute the background cumulative mass flux, apply Earth-shielding geometry for Earth-orbiting cases, and combine them into the total incident flux consumed by the downstream impact-risk assessment. Trigger: ecss, e-st-10-04c, meteoroid environment, grun model, meteoroid streams, sporadic background flux, earth shielding, space environment, impact risk input."
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
  tags: [ecss, e-st-10-04c, meteoroid, grun-model, meteoroid-streams, space-environment, background-flux]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Meteoroid Environment Model Selection (space-systems/ecss/e1004-meteoroid)

Use when the task is selecting and applying the meteoroid environment
models of ECSS-E-ST-10-04C clause 10.2.2.2 (model selection) and
clause 10.2.4 (model application), backed by the Annex C meteoroid
flux reference data, to produce the total incident meteoroid flux for
a mission profile.

## Domain quick reference

- The meteoroid environment has two components: a sporadic background
  (the Grun-type interplanetary meteoroid flux model, giving cumulative
  flux as a function of particle mass, isotropic at 1 AU) and
  meteoroid streams (time-limited, direction-concentrated flux
  enhancements tied to specific calendar windows, e.g. annual
  showers).
- For Earth-orbiting missions, the background flux must be reduced by
  Earth-shielding: the fraction of the sky blocked by the Earth's disc
  as seen from the spacecraft, which depends on orbit altitude (close
  to half the sky blocked at low altitude, approaching none blocked
  far from Earth). Interplanetary missions carry no shielding body.
- A stream only contributes for the calendar window it is active
  (start, peak, end); outside that window only the background applies.
  Where a stream is active, the flux is taken as the worst-case (peak)
  enhancement rather than summed across every active stream, since
  streams are transient and largely independent.
- Model selection precedes model application: first decide which
  components are applicable to the mission profile (regime, orbit
  altitude for Earth-orbit cases, and the epoch date), then compute a
  flux. The resulting flux is the input to the impact-risk assessment
  (sibling e1004-impact-risk leaf), not the risk result itself.

## Workflow

1. Capture the mission profile inputs: regime (`interplanetary` or
   `earth_orbit`), the particle mass of interest, the orbit altitude
   (required only for `earth_orbit`), and the epoch date to be
   analyzed. Flag missing or invalid inputs (unknown regime,
   non-positive mass, missing altitude for an Earth-orbit case,
   missing date) before computing anything.
2. Determine which meteoroid streams are active on the epoch date via
   the stream activity table (start/peak/end calendar windows); an
   epoch outside every stream's window carries no stream enhancement.
3. Compute the sporadic background cumulative flux from the Grun-type
   mass-flux curve for the requested particle mass.
4. For `earth_orbit` missions, compute the Earth-shielding factor from
   orbit altitude and apply it to the background flux. Interplanetary
   missions use a shielding factor of 1 (no blocking body).
5. Apply the worst-case (peak) enhancement factor of any stream active
   on the epoch date to the shielded background flux.
6. Report the total incident flux together with its breakdown
   (background flux, shielding factor, stream enhancement, active
   streams) as this leaf's output, and hand it to the impact-risk
   assessment (sibling e1004-impact-risk leaf), which converts flux
   into a damage probability.

## Pitfalls

- Applying the Grun-type background flux unshielded to an
  Earth-orbiting mission -- this overstates the flux, since a
  spacecraft close to Earth has roughly half its sky blocked by the
  Earth's disc.
- Treating a meteoroid stream as always active -- a stream only adds
  flux during its calendar window; applying its enhancement outside
  the shower overstates the environment.
- Summing every active stream's enhancement when several overlap --
  the model takes the worst-case (peak) contributor, not a sum, since
  streams are transient and independent phenomena.
- Confusing the sporadic background (isotropic, always present) with a
  stream (directional, time-limited) -- these are two components of
  the same clause, not alternative models to pick between; both are
  evaluated and combined for every epoch.
- Skipping the model-selection input validation (missing altitude for
  an Earth-orbit case, non-positive mass, missing epoch date) and only
  discovering the gap when the flux computation raises.

## Behavior contract (gate 3)

The model-selection validation, Grun-type background flux, Earth-
shielding, and stream-activity logic is exercised by the gate 3
contract test: scripts/test_e1004_meteoroid.py against
scripts/e1004_meteoroid_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_meteoroid.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml. The background-flux anchor points
  and stream table in this leaf are an illustrative, simplified
  parameterization of the sporadic-background and stream-activity
  shape used for offline testing -- a certified analysis substitutes
  the normative Annex C flux data and stream parameters.
- compliance: STANDARDS-REF, gated: false.
