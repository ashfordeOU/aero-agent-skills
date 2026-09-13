---
name: e20-rf-power-handling-general-requirements
description: "Use when determine whether every element of a spacecraft radio-frequency chain sustains the maximum operating radio-frequency power it actually sees in vacuum without damage, under ECSS-E-ST-20C clause 7.3.2.1: derive the average and peak-envelope drive from the carrier set, propagate both through the insertion-loss budget of each waveguide-run, filter, switch and antenna-feed, derate any capability substantiated only in ambient air and vented to vacuum, then compare a thermally-limited element against the average and a voltage-breakdown-limited element against the peak envelope. Trigger: ecss, e-st-20-electrical-scope, rf-power-handling, maximum-operating-rf-power, rf-chain-element-rating, peak-envelope-power, vacuum-power-derating, multi-carrier-rf-chain."
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
  tags: [ecss, e-st-20-electrical-scope, e20-rf-power-handling-general-requirements, rf-power-handling, maximum-operating-rf-power, rf-chain-element-rating, peak-envelope-power, vacuum-power-derating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Radio-Frequency Power Handling, General Requirements (space-systems/ecss/e20-rf-power-handling-general-requirements)

Use when the task is the general power-handling requirement of
ECSS-E-ST-20C clause 7.3.2.1 -- establishing that each element of a
radio-frequency chain can sustain the maximum operating
radio-frequency power of the in-orbit vacuum environment without
damage, before any agreed design margin is applied.

## Domain quick reference

- The drive level is not the transmitter nameplate. For a set of
  simultaneous carriers the chain carries an average level equal to
  the sum of the carrier powers, while the envelope peaks far higher:
  with equal-amplitude carriers the voltages add coherently, so the
  peak-envelope level is the square of the summed carrier voltages.
  For a single carrier the two collapse to the same number; for eight
  equal carriers the envelope peak is eight times the average. Sizing
  a breakdown-limited element on the average understates its stress by
  that factor.
- Which of the two applies depends on what limits the element. A
  thermally-limited element -- a terminated load, a lossy
  waveguide-run, a resistive attenuator -- integrates the heat and is
  assessed against the average. A voltage-breakdown-limited element --
  a narrow-gap filter, a switch, a rotary-joint, an antenna-feed --
  fails on instantaneous field strength and is assessed against the
  peak envelope.
- Each element sees a different level. Working from the source
  outward, the incident level at an element is the drive reduced by
  the cumulative insertion loss of everything ahead of it, so the
  element nearest the source is usually, but not always, the critical
  one; the assessment is per element, not per chain.
- A power-handling capability is only valid in the medium it was
  substantiated in. A capability measured in ambient air does not
  transfer to a vented element operating in vacuum, where the gas that
  carried the heat and raised the breakdown threshold is gone; a
  conservative vacuum-derating factor is applied and the element is
  flagged for proper substantiation. A hermetically-sealed element
  keeps its ambient capability only while the seal is evidenced by a
  leak-rate record. A capability with no substantiated basis at all
  supports no numeric verdict.
- An element carrying exactly its effective capability is compliant.
  Because the incident level is reached through a chain of decibel
  conversions, an exactly-compliant case can land a few units in the
  last place above the capability; the comparison absorbs that
  representation error without widening the capability itself.

## Workflow

1. Validate the carrier set: every carrier power strictly positive.
   Compute the average level (sum of carrier powers) and the
   peak-envelope level (square of the sum of the carrier voltage
   amplitudes). Reject an empty or non-positive carrier set.
2. Validate the chain: ordered element list, unique identifiers, each
   with a non-negative insertion loss, a positive capability, a rating
   basis, a pressurization state and a limitation type.
3. Propagate both levels element by element: the incident level at an
   element is the level leaving the previous element; the level
   leaving an element is its incident level reduced by its own
   insertion loss.
4. Compute each element's effective capability: the substantiated
   capability multiplied by the vacuum-derating factor implied by its
   rating basis and pressurization state. An unsubstantiated basis
   yields no effective capability and is a finding in itself.
5. Select the stressing level per element from its limitation type --
   average for thermally-limited, peak envelope for
   voltage-breakdown-limited -- and compare it with the effective
   capability. Record the capability-to-stress ratio in decibels.
6. Report the per-element findings, the worst-case ratio and the
   element that sets it. The chain meets clause 7.3.2.1 only when no
   element carries a finding.

## Pitfalls

- Assessing a multi-carrier chain on the summed average alone. The
  envelope peak scales with the carrier count, and the breakdown-
  limited elements are precisely the ones that see it.
- Applying the transmitter output level to every element. The
  insertion loss ahead of an element is real attenuation, and ignoring
  it drives a needless capability requirement onto the far end of the
  chain.
- Carrying an ambient-air capability into the vacuum case unchanged
  because the component datasheet quotes a single number. The number
  is medium-dependent, and for a vented element it is the wrong
  medium.
- Treating a hermetically-sealed housing as self-evident. Without a
  leak-rate record there is no evidence the retained gas is still
  there at end of life.
- Reading a bare floating-point overshoot as an exceedance. An element
  loaded to exactly its capability through a decibel chain is
  compliant; the tolerance belongs in the comparison, never in the
  capability.

## Behavior contract (gate 3)

The carrier-set arithmetic, chain propagation, vacuum-derating,
limitation-dependent comparison and finding logic is exercised by the
gate 3 contract test:
scripts/test_e20_rf_power_handling_general_requirements.py against
scripts/e20_rf_power_handling_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_rf_power_handling_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
