---
name: e2007-emc-test-safety-provisions
description: "Use when assess the radiation-hazard provisions required by ECSS-E-ST-20-07C clause 5.2.5.1 for an electromagnetic run that energizes high-drive radiating or high-voltage equipment: categorize each energized asset by its radiated-field and stored-energy hazard, compute the far-field-power-density reaching the operator position from the drive level and the antenna-gain, weigh it against the permissible-exposure-limit of the emitting band, derive the minimum standoff when that limit is exceeded, check the position sits beyond the far-field boundary, and confirm every safeguard the hazard category demands is declared present before the run starts. Trigger: ecss, e-st-20-electrical-scope, e-st-20-07c-clause-5-2-5-1, radiation-hazard-provisions, radhaz-standoff-distance, permissible-exposure-limit, far-field-power-density, high-voltage-safety-provisions, hazard-zone-demarcation, access-interlock-verification."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-emc-test-safety-provisions, radiation-hazard-provisions, radhaz-standoff-distance, permissible-exposure-limit, far-field-power-density, high-voltage-safety-provisions, hazard-zone-demarcation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Radiation-Hazard Provisions (space-systems/ecss/e2007-emc-test-safety-provisions)

Use when the task is the personnel-safety obligation of ECSS-E-ST-20-07C
clause 5.2.5.1 -- deciding which safeguards a run has to have in place
because it energizes high-drive radiating equipment or high-voltage
equipment, and proving the operator position is far enough back from the
radiating asset to stay inside the permitted exposure.

## Domain quick reference

- Clause 5.2.5.1 is an entry condition, not a blanket rule. The
  radiation-hazard provisions attach to an asset once it crosses a hazard
  threshold: a radiating chain driven at or above the high-drive level, or
  a source whose open-circuit voltage or stored energy reaches the
  electrical-hazard level. An asset below every threshold is uncategorized
  for this clause and carries no safeguard obligation, which is a finding
  about scope rather than a pass.
- The two hazard families demand different safeguards and an asset can
  carry both. A radiated-field hazard needs hazard-zone-demarcation, an
  access-interlock, a warning-indicator and a reachable emission-cutoff
  control. An electrical hazard needs discharge-and-ground tooling, an
  access-interlock, a warning-indicator and an insulated barrier. Where
  both apply the safeguard set is the union, never the larger of the two.
- Exposure at the operator position is an inverse-square estimate:
  the drive level multiplied by the antenna-gain, spread over the sphere
  of the standoff radius. The permissible-exposure-limit it is weighed
  against is frequency-dependent -- flat in the low bands, at its most
  restrictive across the very-high-frequency band where whole-body
  absorption peaks, rising again with frequency through the microwave
  band, then flat once more.
- When the position exceeds the limit, the actionable output is the
  minimum standoff -- the radius at which the same drive and antenna-gain
  land exactly on the limit -- not a bare fail. It is what the hazard-zone
  demarcation is drawn from.
- The inverse-square estimate is only valid beyond the far-field boundary
  of the radiating aperture, roughly twice the squared aperture over the
  wavelength. A position inside that boundary needs a measured survey, so
  it is reported as its own finding rather than quietly computed.
- A power-density assembled from a product and a square can land a few
  units in the last place above a limit it is physically equal to. The
  comparison absorbs that representation error; the exposure limit itself
  is never relaxed.

## Workflow

1. Inventory every asset that will be energized during the run with its
   kind, its drive level, its open-circuit voltage and its stored energy.
   Reject an unrecognized asset kind or a negative level before anything
   else runs.
2. Categorize each asset: radiated-field hazard, electrical hazard, both,
   or uncategorized. A receiver or a support instrument is never a
   radiated-field hazard however large the level recorded against it.
3. Take the union of the safeguards its categories demand, compare that
   against the safeguards declared present, and raise one finding per
   absent safeguard so the reviewer sees which one is missing.
4. For each radiated-field hazard, compute the power-density at the
   operator standoff, look up the permissible-exposure-limit for the
   emitting frequency, and raise a finding with the minimum standoff
   attached whenever the position is inside the hazard zone.
5. Where the radiating aperture is declared, compute the far-field
   boundary and raise a separate finding when the operator position sits
   inside it, because there the computed estimate does not apply.
6. Permit the run only when every asset comes back with an empty finding
   list; report the hazardous assets separately so the safety brief can
   name them.

## Pitfalls

- Treating the clause as covering only radiated hazards and letting a
  high-voltage supply through with warning signage alone -- the discharge
  and grounding tooling is what makes the rack safe to approach after the
  run, and no amount of demarcation substitutes for it.
- Applying one exposure limit across the whole sweep. The limit moves by
  more than a factor of five between the low bands and the most
  restrictive band, so a standoff that is generous at one frequency can be
  well inside the hazard zone at another.
- Computing a standoff inside the far-field boundary of a large aperture
  and acting on the number; the field there is still forming and the
  inverse-square estimate can understate the exposure badly.
- Reporting a bare fail without the minimum standoff, which leaves the
  facility with nothing to draw the hazard zone from and invites an
  arbitrary guess.
- Relaxing the exposure limit to clear a position that fails by a few
  units in the last place. The representation error belongs in the
  comparison, not in the safety limit.

## Behavior contract (gate 3)

The hazard-categorization, safeguard-set, power-density, exposure-limit,
minimum-standoff and far-field-boundary logic is exercised by the gate 3
contract test: scripts/test_e2007_emc_test_safety_provisions.py against
scripts/e2007_emc_test_safety_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_emc_test_safety_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
