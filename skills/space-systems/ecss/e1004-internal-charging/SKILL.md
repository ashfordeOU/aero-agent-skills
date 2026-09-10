---
name: e1004-internal-charging
description: "Use when assessing internal (deep-dielectric) charging risk for a space mission under ECSS-E-ST-10-04C clause 9.2.1.3 and Annex B.4/B.5: compute the worst-case trapped electron spectrum by enveloping the FLUMIC and NASA worst-case GEO models at each modeled energy, verify the envelope is physically consistent (flux non-increasing with energy), and screen the enveloped flux at the mission's critical energy against a stated threshold to flag orbit regimes (MEO, GEO, GTO, HEO) with elevated internal charging risk. Trigger: internal charging, deep dielectric charging, worst-case electron spectrum, FLUMIC, NASA worst-case GEO spectrum, e-st-10-04, annex b.4, annex b.5, charging risk screening."
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
  tags: [ecss, e-st-10-04c, internal-charging, deep-dielectric, electron-spectrum, space-systems]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Internal Charging Worst-Case Electron Spectrum (space-systems/ecss/e1004-internal-charging)

Use when the task is computing or checking the worst-case trapped
electron spectrum that ECSS-E-ST-10-04C clause 9.2.1.3 requires as the
environment-level input for internal (deep-dielectric) charging risk:
the per-energy envelope of Annex B.4 (FLUMIC) and Annex B.5 (NASA
worst-case GEO spectrum), screened against a stated flux threshold.

## Domain quick reference

- Internal (deep-dielectric) charging is driven by penetrating trapped
  electrons depositing charge inside spacecraft dielectrics and
  floating conductors faster than it can bleed off. Clause 9.2.1.3
  requires the worst-case trapped electron spectrum for MEO/GEO/GTO/HEO
  orbit segments, built from Annex B.4 (FLUMIC) and Annex B.5 (NASA
  worst-case GEO spectrum).
- FLUMIC (Annex B.4) reports a percentile-parameterized worst-case
  spectrum (e.g. 90th/95th/99th percentile) tied to a stated averaging
  policy; the NASA worst-case GEO spectrum (Annex B.5) is a fixed
  reference envelope independent of percentile. Because neither model
  dominates at every energy, the RES-required spectrum is the
  per-energy envelope: the higher of the two fluxes at each energy.
- The envelope is only physically credible if flux is non-increasing
  as energy increases across the modeled energy grid (a harder,
  more-penetrating population cannot outnumber a softer one in a
  differential/integral spectrum). An increase between adjacent
  energies signals a modeling or transcription error that must be
  resolved before the spectrum is used for charging analysis.
- Internal charging under this clause is a design driver only for
  orbit regimes with a persistent penetrating-electron population:
  MEO, GEO, GTO, HEO. LEO, L2, and deep-magnetotail segments are out
  of scope for clause 9.2.1.3 (see the sibling applicable-component
  leaves for what does apply to those regimes).
- Risk screening compares the enveloped flux at the mission's critical
  energy against a flux threshold agreed with the electrical/EEE-parts
  engineering discipline. The numeric threshold and the material-level
  charge-accumulation response are outside clause 9.2.1.3 and outside
  this leaf; this leaf only determines whether the environment-level
  input crosses the agreed screening line.

## Workflow

1. Confirm the orbit segment's regime before modeling anything: check
   it against MEO/GEO/GTO/HEO. A regime outside that set is not
   subject to clause 9.2.1.3 and should be routed to its own
   applicable-component leaf instead of forced through this one.
2. Choose the energy grid (in MeV) and the FLUMIC percentile that
   matches the mission's stated confidence policy, then evaluate both
   models (FLUMIC and NASA worst-case GEO) across that same grid so
   they can be compared point-by-point.
3. Validate every raw model output is a finite, non-negative flux; a
   model returning a negative or non-finite value at any energy
   invalidates that spectrum and must be corrected before continuing.
4. Build the per-energy envelope by taking the higher of the two model
   fluxes at each energy, and record which model dominated at each
   point for traceability in the RES write-up.
5. Check the envelope for energy-order violations (flux increasing
   between adjacent ascending energies); treat the spectrum as
   unverified until every violation is resolved.
6. Screen the verified envelope against the agreed flux threshold at
   the mission's critical energy; flag internal charging risk only
   when the enveloped flux at that energy meets or exceeds the
   threshold.
7. Carry forward the percentile caveat when the FLUMIC percentile is
   at or above the high-percentile extrapolation threshold, and report
   the full envelope, the dominant-model breakdown, and the risk flag
   into the RES entry for clause 9.2.1.3.

## Pitfalls

- Using only one of the two models (typically defaulting to whichever
  is more familiar) instead of enveloping both; each model is
  conservative in a different energy range, so a single-model spectrum
  understates the worst case in the other model's stronger range.
- Screening against the threshold with a raw single-model flux instead
  of the envelope, which can pass a spectrum that would fail once the
  other model's contribution is included.
- Conflating this leaf's worst-case electron spectrum (already "worst
  case" at a stated percentile) with the sibling SEP-fluence leaf's
  stochastic, duration/confidence-driven proton fluence — feeding a
  duration-accumulation policy into this model keys the spectrum to
  the wrong probabilistic meaning.
- Applying clause 9.2.1.3 to LEO or L2/deep-tail segments out of habit
  because other radiation analysis was already being done there, when
  internal charging under this clause is scoped to MEO/GEO/GTO/HEO
  only.
- Treating an unverified (energy-order-violating) envelope as final
  because the risk screening step still produced a flag/no-flag
  answer — an invariant violation means the spectrum itself is
  suspect regardless of what the threshold comparison says.

## Behavior contract (gate 3)

The orbit-applicability check, per-model validation, worst-case
envelope construction, energy-order-violation checking, and risk
screening logic is exercised by the gate 3 contract test:
scripts/test_e1004_internal_charging.py against
scripts/e1004_internal_charging_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_internal_charging.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
