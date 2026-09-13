---
name: e2007-esd-related-emi-control
description: "Use when verify the interference-control provisions required for a space system or equipment exposed to electrostatic-discharge events under ECSS-E-ST-20-07C clause 4.2.4.2: categorize each event as a surface-charging-arc, an internal-charging-arc, a triboelectric-separation event or a ground-handling-event, size the arc-discharge pulse from the stored capacitance, the breakdown-voltage and the arc resistance, couple that pulse onto a victim-harness through its transfer-impedance and shield-effectiveness, compare the coupled transient against the victim transient-susceptibility threshold with the declared emi-margin, and confirm the chassis-bonding, surface-conductivity, shield-termination and transient-filtering provisions for that event family are on record. Trigger: ecss, e-st-20-electrical-scope, esd-related-emi-control, electrostatic-discharge, arc-transient-coupling, transfer-impedance, surface-charging-arc, internal-charging-arc, shield-termination, transient-susceptibility."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-esd-related-emi-control, electrostatic-discharge, arc-transient-coupling, transfer-impedance, surface-charging-arc, internal-charging-arc, transient-susceptibility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — ESD-Related EMI Control (space-systems/ecss/e2007-esd-related-emi-control)

Use when the task is the electrostatic-discharge interference-control
assessment of ECSS-E-ST-20-07C clause 4.2.4.2 — categorizing each
discharge event a system or equipment is exposed to, sizing the
arc-discharge pulse it delivers, coupling that pulse onto the victim
harness, and checking the coupled transient against the victim
transient-susceptibility threshold with a declared emi-margin.

## Domain quick reference

- Clause 4.2.4.2 treats an electrostatic-discharge event as an
  interference source, not only as a damage mechanism: the arc is a
  fast, broadband current pulse that couples into harnesses and
  equipment ports, so the provision set is an interference-control
  set (bonding, surface conductivity, shield termination, transient
  filtering) rather than a single component-level protection device.
- Four event families cover the in-scope exposures. A
  surface-charging-arc comes from differential charging of an external
  dielectric relative to the conductive structure. An
  internal-charging-arc comes from energetic electrons buried inside a
  dielectric until the internal field exceeds breakdown. A
  triboelectric-separation event comes from contact and separation of
  dissimilar materials during deployment or release. A
  ground-handling-event is the pre-launch human-body or charged-device
  exposure. Each event is categorized into exactly one family before
  its provisions are checked, and an unrecognized event kind is
  rejected rather than assumed benign.
- The arc is modelled as a capacitive discharge through the arc
  resistance: peak current is the breakdown-voltage divided by the arc
  resistance, transferred charge is capacitance times breakdown-voltage,
  stored energy is half the capacitance times the breakdown-voltage
  squared, and the decay time constant is the product of arc resistance
  and capacitance. The spectral corner frequency derived from that time
  constant is what makes a small-energy arc an EMI source: a short
  time constant pushes significant content into the band where harness
  coupling is efficient.
- Coupling onto a victim-harness uses the surface transfer-impedance of
  its shield: the open-circuit transient is peak current times the
  transfer-impedance per metre times the exposed run length, reduced by
  the shield-effectiveness expressed in decibels. The result is
  compared with the victim transient-susceptibility threshold, and the
  ratio in decibels is the emi-margin. A design is acceptable only when
  that emi-margin meets or exceeds the declared requirement.
- The provision set is family-specific. A surface-charging-arc needs
  surface-conductivity control and a bonded conductive path plus
  terminated shields; an internal-charging-arc needs dielectric
  thickness or shielding control plus bonding and transient filtering;
  a triboelectric-separation event needs static-dissipative materials
  and bonding; a ground-handling-event needs a controlled handling area,
  operator bonding and transient filtering. A missing provision is a
  finding even when the computed emi-margin passes.

## Workflow

1. Inventory every electrostatic-discharge exposure of the system and
   its equipment, and categorize each one into its event family.
   Reject an unrecognized event kind before it enters the assessment.
2. Size the arc-discharge pulse for each event from the stored
   capacitance, the breakdown-voltage and the arc resistance; record
   peak current, transferred charge, stored energy, decay time constant,
   pulse duration and spectral corner frequency.
3. For each event and the victim it can reach, compute the coupled
   transient from the harness transfer-impedance, the exposed run
   length and the shield-effectiveness.
4. Compute the emi-margin as the decibel ratio of the victim
   transient-susceptibility threshold to the coupled transient, and
   compare it against the declared requirement. Treat an exactly
   on-limit result as compliant by absorbing the floating-point
   representation error, never by widening the requirement.
5. Check the family-specific provision set for each event and list the
   provisions that are not on record.
6. Aggregate the coupling findings and the provision findings; the
   system is not interference-controlled for electrostatic discharge
   until both lists are empty. Report the worst emi-margin as the
   driving case.

## Pitfalls

- Treating an arc as an energy problem only: a milli-joule arc that is
  harmless thermally still radiates a broadband pulse, and clause
  4.2.4.2 is about that interference path, not about the energy.
- Collapsing the four event families into one generic exposure — the
  provision sets differ, and a surface-conductivity coating does
  nothing for an internal-charging-arc driven by buried charge.
- Applying the open-circuit transient without the shield-effectiveness
  term, or applying the shield-effectiveness twice by also reducing the
  transfer-impedance; each is a large error in opposite directions.
- Reading a passing emi-margin as compliance while a required provision
  is unrecorded — the computed coupling covers one victim and one path,
  while the provision set covers the exposures that were never modelled.
- Widening the declared emi-margin requirement to make an exactly
  on-limit case pass; absorb the representation error in the comparison
  instead and leave the engineering requirement untouched.
- Assuming a ground-handling-event is out of scope because it happens
  before launch; the latent damage and the provisions that prevent it
  are part of the same interference-control set.

## Behavior contract (gate 3)

The event categorization, arc-pulse sizing, transfer-impedance
coupling, emi-margin and provision-set logic is exercised by the gate 3
contract test: scripts/test_e2007_esd_related_emi_control.py against
scripts/e2007_esd_related_emi_control_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2007_esd_related_emi_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
