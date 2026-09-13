---
name: e20-antenna-rf-chain-characterisation
description: "Use when evaluate the feed-chain of a spacecraft antenna as a circuit in its own right under ECSS-E-ST-20C clause 7.2.2.3.5: categorize every stage as a waveguide-run, filter, diplexer, orthomode-transducer, rotary-joint, directional-coupler, polariser or switch, sum the cascaded-insertion-loss against its allocation, refer each stage dissipation back through the Friis cascade into a chain noise temperature, turn the stage return losses into adjacent-interface mismatch ripple and a worst-case input-port-standing-wave-ratio, walk the forward power down a transmit chain for its rf-power-handling-margin, combine the stage delay ripples, and charge the receive figure-of-merit penalty the chain costs the antenna. Trigger: ecss, e-st-20c-clause-7-2-2-3-5, antenna-feed-chain-characterisation, cascaded-insertion-loss-budget, friis-noise-temperature-cascade, interface-mismatch-ripple, input-port-standing-wave-ratio, rf-power-handling-margin, group-delay-ripple-budget."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-rf-chain-characterisation, antenna-feed-chain-characterisation, cascaded-insertion-loss-budget, friis-noise-temperature-cascade, interface-mismatch-ripple, input-port-standing-wave-ratio, rf-power-handling-margin, group-delay-ripple-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Antenna Feed-Chain Characterisation (space-systems/ecss/e20-antenna-rf-chain-characterisation)

Use when the task is the clause 7.2.2.3.5 case of ECSS-E-ST-20C --
characterising the passive circuit between the transceiver port and
the radiating aperture independently of the aperture itself, and then
folding that characterisation back into what the antenna delivers. The
chain is runs, filters, diplexers, transducers, rotary joints,
couplers, polarisers and switches; it is measurable on the bench
without an aperture, and it carries its own allocation.

## Domain quick reference

- Every stage is categorized by kind before any number is taken from
  it, because kind sets what the stage is allowed to declare: a
  waveguide-run is dissipation and delay, a filter adds delay ripple
  across the band, a rotary-joint adds a rotation-dependent match, a
  directional-coupler taps a fraction of the through path. A stage of
  an unrecognised kind, a stage with negative dissipation (a passive
  circuit has no gain), or a stage with no declared return loss is
  rejected rather than silently defaulted.
- Dissipation cascades by addition in dB. Noise does not. Each stage
  contributes a noise temperature set by its own dissipation and its
  physical temperature, referred back to the chain input through
  everything ahead of it; for an all-passive chain the cascade collapses
  to the single-loss identity, which is the check that the cascade was
  assembled the right way round.
- Mismatch acts twice. Two reflecting interfaces facing each other
  produce a transmission ripple across the band set by the product of
  their reflection magnitudes -- flat loss is not the whole cost. And
  every stage reflection returns to the input port through the
  dissipation ahead of it, twice, so the worst-case
  input-port-standing-wave-ratio is the in-phase sum of the attenuated
  stage reflections, not the reflection of the first stage alone.
- A transmit chain is graded on handling. The forward power arriving at
  a stage is the port power attenuated by everything upstream, so the
  first stage is the hardest driven; the rf-power-handling-margin of
  each stage is the ratio of its rating to what actually arrives.
- A receive chain is graded on figure-of-merit. Dissipation ahead of
  the receiver costs twice: it removes signal and it adds noise while
  lifting the receiver noise contribution referred to the antenna port.
  The penalty is therefore always larger than the bare dissipation of
  the chain, which is why the chain is characterised separately instead
  of being folded into a single loss term.

## Workflow

1. Validate the ordered stage list: categorize each stage kind, reject
   a duplicate stage identity, a negative dissipation, an implausibly
   lossy through path, or a missing return loss.
2. Sum the stage dissipations into the cascaded-insertion-loss and
   compare it with the chain allocation.
3. Refer the stage noise contributions back to the chain input with the
   Friis cascade at the declared physical temperature; cross-check
   against the single-loss identity.
4. Convert each stage return loss into a reflection magnitude; compute
   the mismatch ripple of every adjacent interface pair and keep the
   worst, then sum the attenuated stage reflections into the worst-case
   input-port reflection and its standing-wave-ratio.
5. For a transmit chain, walk the forward power down the stages and
   compute the rf-power-handling-margin of every stage that declares a
   rating.
6. For a receive chain, combine the chain noise temperature, the chain
   dissipation, the antenna noise temperature and the receiver noise
   temperature into the figure-of-merit penalty charged to the antenna.
7. Combine the independent stage delay ripples as a root-sum-square and
   compare with the delay allocation.
8. Grade every quantity against the chain allocation; the chain is not
   characterisation-compliant until all of them are clear.

## Pitfalls

- Charging the chain once, as a flat loss. The same hardware shows up
  as dissipation, as added noise, as band ripple, as a port match and
  as a handling constraint; a single insertion-loss number answers one
  of five questions.
- Adding stage noise temperatures directly. A contribution is only
  comparable once referred through the stages ahead of it; adding them
  as measured overstates the deep stages and understates the shallow
  ones.
- Reading the chain match off the first stage. The input port sees
  every stage reflection attenuated by the round trip to it, and a
  chain of individually respectable stages can still sum to a match
  outside its allocation.
- Sizing handling at the aperture end. The forward power is highest at
  the port end of a transmit chain, so grading the last stage -- the
  one that sees the least -- reports a margin the first stage does not
  have.
- Treating the receive penalty as equal to the dissipation. The chain
  also lifts the receiver contribution referred to the antenna port, so
  the figure-of-merit cost is strictly larger than the dB of loss, and
  the gap grows as the receiver gets quieter.

## Behavior contract (gate 3)

The stage categorisation, cascaded-insertion-loss, Friis noise cascade,
interface mismatch ripple, input-port reflection and
standing-wave-ratio, forward-power profile and handling margin, delay
ripple, figure-of-merit penalty and the aggregate allocation grading
are exercised by the gate 3 contract test:
scripts/test_e20_antenna_rf_chain_characterisation.py against
scripts/e20_antenna_rf_chain_characterisation_logic.py (stdlib
unittest, offline, deterministic). Run:
python3 scripts/test_e20_antenna_rf_chain_characterisation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
