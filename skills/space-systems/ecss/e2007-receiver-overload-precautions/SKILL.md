---
name: e2007-receiver-overload-precautions
description: "Use when verify that no stage of an ECSS-E-ST-20-07C clause 5.2.5.3 emission or susceptibility measurement-chain is driven into overload: propagate the transducer-referred signal level through every measurement-chain stage, compare each stage input against its declared compression-point and damage-threshold, size the extra input-attenuation needed to restore linear operation without losing measurement-headroom against the emission-limit, and confirm the attenuation-insertion linearity check reproduces the inserted pad within tolerance. Trigger: ecss, e-st-20-electrical-scope, receiver-overload, transducer-overload, measurement-chain-linearity, compression-point, input-attenuation-sizing, preamplifier-saturation, attenuation-insertion-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-receiver-overload-precautions, receiver-overload, measurement-chain-linearity, compression-point, input-attenuation-sizing, attenuation-insertion-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Test Setup — Receiver Overload Precautions (space-systems/ecss/e2007-receiver-overload-precautions)

Use when the task is the ECSS-E-ST-20-07C clause 5.2.5.3 precaution that
keeps receivers and transducers out of overload for the whole of an
electromagnetic measurement -- propagating the transducer-referred level
through the measurement chain, checking every stage against its own
linear window, sizing the input attenuation that restores linearity, and
demonstrating the result with a pad-insertion linearity check.

## Domain quick reference

- A measurement chain runs transducer -> cable -> optional preselector
  filter -> optional preamplifier -> step attenuator -> receiver. Only
  the transducer, the preamplifier and the receiver front end compress;
  cables, pads and filters are passive loss elements and are not
  expected to declare a linear window of their own.
- Each compressing stage carries two thresholds referred to its own
  input: a compression point, above which the reported level is low and
  irreproducible, and a damage threshold, above which the stage is
  harmed. Above the damage threshold the correct action is to stop and
  protect the input, not to record a margin.
- Levels are carried in dBm through the chain. A transducer factor is
  additive: the terminal level is the measured quantity level minus the
  factor, and the dB microvolt to dBm conversion is the level minus 90
  minus ten times the log of the reference impedance (about 107 dB for
  a 50 ohm system).
- Attenuation inserted behind the transducer shifts every downstream
  stage by the same amount, so the needed value is the worst compression
  excess in the chain rounded up to the attenuator step size. It cannot
  rescue a saturated transducer, because the saturation happens ahead of
  the insertion point; that case is closed by reducing coupling.
- Adding attenuation costs sensitivity. The limit referred to the
  receiver input, less the added attenuation, must still stand a stated
  headroom above the receiver noise floor, otherwise the run trades one
  invalid result for another.
- The bench demonstration is a pad-insertion check: insert a known
  attenuator, and the indicated level must fall by the same number of dB
  within a stated tolerance. A shortfall means a stage was already
  compressed before the pad went in.

## Workflow

1. Refer the stimulus to the transducer terminals: subtract the
   transducer factor from the measured quantity level, then convert the
   dB microvolt terminal level to dBm at the system impedance.
2. Build the ordered chain (transducer first, receiver last, unique
   stage names) and propagate the level stage by stage, accumulating
   preamplifier gain and cable, pad and filter loss. Reject an
   unrecognized stage kind, a negative loss, a non-positive gain, or a
   damage threshold below its own compression point before any number
   is produced.
3. Categorize every stage as linear, overload or damage-risk against its
   own two thresholds; flag a compressing stage that declares neither
   threshold as uncategorized -- an undeclared linear window is a
   finding, not a pass.
4. Take the worst compression excess across the chain and round it up to
   a whole attenuator step to size the input attenuation. Mark the plan
   infeasible when it exceeds the attenuation on hand, or when the
   transducer itself is saturated.
5. Re-check measurement headroom with the attenuation in place: the
   limit referred to the receiver input, less the added attenuation,
   against the noise floor plus the required headroom.
6. Emit the precaution actions in priority order -- protect the input
   first, reduce transducer coupling, insert input attenuation, bypass
   the preamplifier, engage the preselector -- and record the
   pad-insertion linearity check. The setup is not clause-compliant
   until the finding list is empty and the linearity check is on record.

## Pitfalls

- Checking only the receiver input and declaring the chain safe: the
  preamplifier usually compresses first, because it sees the same level
  the receiver does minus its own gain and the pad behind it.
- Treating an overloaded reading as conservative. Compression drives the
  indication down, so an overloaded chain under-reports the emission and
  can turn a real exceedance into an apparent pass.
- Adding attenuation until the chain is linear and stopping there: the
  same pad pushes the limit toward the noise floor, and a limit that can
  no longer be resolved is as invalid as an overloaded one.
- Trying to fix a saturated transducer with downstream attenuation. The
  pad sits behind the saturation, so the indication changes while the
  distortion does not; the coupling itself has to be reduced.
- Sizing attenuation to the exact excess rather than to a whole
  attenuator step, which cannot be set on a step pad and silently
  becomes a fractional-dB assumption in the report.
- Skipping the pad-insertion check because the computed levels look
  comfortable. The computation uses declared thresholds; the insertion
  check is the only evidence the real hardware was linear on the day.
- Letting a dB sum that lands a few units in the last place above a
  threshold read as an overload. The logic absorbs representation error
  with a named tolerance far below any engineering value; the threshold
  itself is never widened.

## Behavior contract (gate 3)

The level-referral, chain-propagation, stage-categorization,
attenuation-sizing, headroom and pad-insertion-check logic is exercised
by the gate 3 contract test:
`scripts/test_e2007_receiver_overload_precautions.py` against
`scripts/e2007_receiver_overload_precautions_logic.py` (stdlib unittest,
offline). Run: python3 scripts/test_e2007_receiver_overload_precautions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
