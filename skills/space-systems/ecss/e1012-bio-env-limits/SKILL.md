---
name: e1012-bio-env-limits
description: "Use when defining the space radiation environments applicable to a crewed mission and verifying crew dose compliance with ECSS-E-ST-10C §11.3–11.4: identify which environments (galactic cosmic rays, solar energetic particles, trapped protons, trapped electrons, secondary neutrons) apply to the orbit profile, determine dose contributions to the blood-forming organ, eye lens, and skin, compare accumulated doses against the short-term (30-day and annual) and career limits for each crew member, and flag any exceedance or missing limit record as a protection finding requiring resolution before crew-hours approval. Trigger: ecss, e-st-10-system-scope, crew-dose, radiation-protection-limits, space-radiation-environment, GCR, SPE, trapped-radiation, BFO-dose, career-limit."
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
  tags: [ecss, e-st-10-system-scope, crew-dose, radiation-protection-limits, space-radiation-environment, BFO-dose, career-limit, GCR, SPE, trapped-radiation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Crew Radiation Environments and Protection Limits (space-systems/ecss/e1012-bio-env-limits)

Use when the task is to define the space radiation environments relevant to
a crewed mission (ECSS-E-ST-10C §11.3) and to establish and verify the crew
radiation protection limits for that mission (§11.4) — identifying which
radiation sources drive dose for a given orbit, determining the organ-dose
contributions, and confirming that no crew member's accumulated dose exceeds
the short-term or career limits.

## Domain quick reference

- §11.3 requires the analyst to enumerate the radiation environments that
  are physically present for the planned orbit. Five environment families
  are relevant to crewed missions: galactic cosmic rays (GCR, always
  present for crewed missions outside a planetary surface), solar energetic
  particles (SPE/SEP, transient events driven by solar flares and coronal
  mass ejections, accessible at high orbital inclinations or above the
  magnetosphere), trapped protons (inner Van Allen belt and South Atlantic
  Anomaly tail, relevant below roughly 10 000 km altitude), trapped
  electrons (predominantly the outer Van Allen belt, relevant between
  roughly 1 500 km and 65 000 km altitude), and secondary neutrons
  (produced by any of the above interacting with shielding material, always
  present as a secondary product). Orbit altitude and inclination together
  determine which subset applies; environments not present in the orbit
  profile are excluded from the dose calculation, not treated as
  conservative zero-dose contributions.
- §11.4 sets protection limits by organ and time horizon. Short-term limits
  apply over a 30-day window (blood-forming organ: 250 mGy-Eq, eye lens:
  1 000 mGy-Eq, skin: 1 500 mGy-Eq) and over an annual window (BFO:
  500 mGy-Eq, eye lens: 2 000 mGy-Eq, skin: 6 000 mGy-Eq). A career limit
  on BFO effective dose applies per crew member and varies with sex and age
  to account for the radiation-induced risk differential; it is a hard
  ceiling on cumulative career exposure, not a per-mission allocation.
  These values are paraphrased from ECSS-E-ST-10C §11.4 and the referenced
  ESA and international crew radiation protection standards.
- The protection assessment is per-crew-member, not per-mission: two
  astronauts on the same mission with different career histories can have
  different compliance statuses against the career limit.

## Workflow

1. For the planned orbit, determine altitude and inclination. Use the
   orbit environment rules (§11.3) to produce the applicable environment
   list: always include GCR and secondary neutrons; add trapped protons if
   altitude is at or below 10 000 km; add trapped electrons if altitude
   falls between 1 500 km and 65 000 km; add SPE if inclination is at or
   above 50° or the orbit is beyond the magnetosphere (altitude above
   70 000 km). Record only the environments that apply; exclude the rest.
2. For each applicable environment, obtain the dose-rate estimate from the
   radiation environment model (separate analysis, not in scope here);
   resolve the radiation quality factors for each particle species to
   convert absorbed dose (Gy) to equivalent dose (Gy-Eq); sum over all
   applicable environments to obtain the total organ-equivalent dose rate
   for each organ of interest (BFO, eye lens, skin).
3. Multiply the organ-equivalent dose rate by the mission duration to
   obtain the mission dose per organ. Add to the crew member's existing
   career BFO dose to obtain the projected career total.
4. For each crew member, check each organ dose against the applicable
   short-term limits (30-day and annual) using the limit table from §11.4.
   Flag any exceedance. Flag also any organ for which a dose estimate exists
   but no limit was recorded — a missing limit record is a protection
   finding, not a pass.
5. Check the projected career BFO dose against the career limit for each
   crew member's sex and age bracket. Flag any exceedance. If a career
   limit cannot be determined because sex or age is not on record, flag that
   as a data-gap finding, not a compliant result.
6. Aggregate the per-organ and career findings per crew member. A crew
   member receives crew-hours approval only when every finding is resolved.
   Unresolved exceedances require either a mission re-plan (reduced duration,
   increased shielding, orbit change) or a documented waiver through the
   applicable flight-safety authority.

## Pitfalls

- Applying dose-rate estimates from one orbit to a different orbit without
  re-running the environment assessment — altitude and inclination changes
  can substantially alter the trapped-belt and SPE components and invalidate
  the environment list.
- Treating an environment as absent because its dose contribution is low on
  a nominal mission — SPE events are stochastic; the SPE environment must be
  included whenever the orbit geometry permits SPE access, regardless of
  expected fluence on the nominal case.
- Mixing absorbed dose (Gy) with equivalent dose (Gy-Eq) in the limit check
  — the §11.4 short-term limits are expressed in mGy-Eq; applying them to
  absorbed doses in mGy without applying the quality factor overstates
  compliance for high-LET particle species.
- Applying the career limit as a per-mission budget rather than a cumulative
  ceiling — the career limit applies to the sum of all prior career exposure
  plus the planned mission dose; a crew member near the career ceiling may
  be excluded from a mission even if the mission dose alone would be within
  the short-term limits.
- Recording no findings when a limit field is missing — a missing limit
  record means the requirement traceability is incomplete, which is a
  protection gap, not evidence of compliance.

## Behavior contract (gate 3)

The environment-identification, dose-limit-check, career-limit-check, and
crew-member-assessment logic is exercised by the gate 3 contract test:
scripts/test_e1012_bio_env_limits.py against
scripts/e1012_bio_env_limits_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_bio_env_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
