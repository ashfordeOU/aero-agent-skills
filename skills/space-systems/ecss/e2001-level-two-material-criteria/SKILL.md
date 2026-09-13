---
name: e2001-level-two-material-criteria
description: "Use when evaluate candidate secondary-emission records and select the one that feeds the second multipactor-analysis-level of ECSS-E-ST-20-01C clause 5.3.2.3.2: screen every secondary-electron-yield dataset against the electrode-material of the susceptible gap, against a flight surface-condition the measured sample is no cleaner than, against the representative temperature-window, and against the impact-energy-range the tracked electrons actually reach. Rank the qualifying records by conservatism - lowest first-crossover-energy, then highest peak-yield - take the leading one, and reconcile its declared cross-over energies with the yield-curve model before the detailed run starts. Trigger: ecss, e-st-20-electrical-scope, secondary-electron-yield, first-crossover-energy, yield-curve-selection, surface-condition-representativeness, electrode-material-match, impact-energy-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-level-two-material-criteria, secondary-electron-yield, first-crossover-energy, yield-curve-selection, surface-condition-representativeness, electrode-material-match]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Second-Level Secondary-Emission Criteria (space-systems/ecss/e2001-level-two-material-criteria)

Use when the task is choosing the secondary-emission properties that the
detailed second multipactor-analysis-level of ECSS-E-ST-20-01C clause
5.3.2.3.2 consumes — which measured yield record is representative of the
flight surface, which is optimistic and must be refused, and which of the
qualifying ones is the conservative choice.

## Domain quick reference

- The second analysis level tracks electrons against a measured
  secondary-electron-yield curve rather than against a chart. That curve is
  summarised by its peak yield, the impact energy at which the peak occurs,
  and the two impact energies at which the yield passes unity: the
  first-crossover-energy, below which an impacting electron cannot multiply,
  and the second-crossover-energy, above which it again cannot. A record
  whose peak yield never exceeds unity has no cross-over at all and cannot
  describe a multipacting surface.
- Representativeness is the whole selection criterion. Yield falls as a
  surface is cleaned, so a record measured on a surface cleaner than the
  flight surface predicts fewer secondaries than flight hardware produces.
  Rank the conditions — as-received, air-exposed, solvent-cleaned,
  vacuum-baked, electron-conditioned, atomically-clean — and admit only a
  record whose surface is no cleaner than the flight surface.
- Three further filters apply before a record qualifies: the electrode
  material must match the material of the susceptible gap, the measurement
  temperature must sit inside the window around the representative flight
  temperature, and the measured energy span must cover the whole
  impact-energy-range the tracked electrons reach. A record extrapolated
  outside its measured span is not data.
- Among the qualifying records the conservative one is the one that starts
  multiplying earliest and hardest: lowest first-crossover-energy first, and
  where those tie, the highest peak yield. Deterministic tie-breaking on the
  record identifier keeps the selection reproducible across runs.
- The declared cross-over energies and the curve parameters come from the
  same measurement, so they can be reconciled: build the yield curve from the
  peak yield, the peak energy and the low-energy threshold, find where it
  passes unity, and compare against the declared values. A wide disagreement
  means the record is internally inconsistent and must not be trusted.

## Workflow

1. Normalize the electrode material and the surface condition of the target
   gap and of every candidate record; reject an unrecognized label.
2. Validate each candidate physically: peak yield above unity, positive
   energies, first-crossover below the peak energy, peak energy below the
   second-crossover, an increasing measured energy span, and a low-energy
   threshold below the peak energy.
3. Screen each candidate against the four criteria — material match, surface
   condition no cleaner than flight, measured span covering the
   impact-energy-range, measurement temperature inside the window — and
   record every failed criterion as a named reason, not a silent drop.
4. Rank the survivors by conservatism and take the leading record.
5. Reconcile that record's declared cross-over energies against the curve
   model; a relative disagreement beyond the tolerance is a finding.
6. If nothing qualifies, report the fallback explicitly: the run cannot use a
   non-representative record, so either new measurement data or a bounding
   assumption has to be agreed before the detailed analysis proceeds.

## Pitfalls

- Taking the cleanest available laboratory record because it looks like the
  best data. A sputter-cleaned sample yields fewer secondaries than an
  air-exposed flight surface, so that record hides the multipactor risk.
- Using a record whose measured energy span stops short of the impact
  energies the tracking actually produces, and extrapolating the curve into
  the gap. The extrapolated part carries no measurement behind it.
- Reading "no violation" from an empty qualifying set. No representative
  record is a finding that blocks the run, not a pass.
- Ranking on peak yield alone. A surface with a modest peak but a very low
  first-crossover-energy multiplies over a far wider operating band and is
  the more conservative choice.
- Comparing a relative deviation against its tolerance with a bare
  inequality. The deviation is a quotient of floats and can land a unit in
  the last place above an exactly compliant value; absorb the representation
  error in the comparison, never by loosening the tolerance.

## Behavior contract (gate 3)

The material and surface-condition normalization, dataset validation, curve
evaluation, cross-over reconciliation, screening and conservative ranking are
exercised by the gate 3 contract test:
scripts/test_e2001_level_two_material_criteria.py against
scripts/e2001_level_two_material_criteria_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_level_two_material_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
