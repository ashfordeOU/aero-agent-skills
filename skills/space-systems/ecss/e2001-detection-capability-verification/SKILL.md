---
name: e2001-detection-capability-verification
description: "Use when verify, as the testing-entity of ECSS-E-ST-20-01C clause 7.3.1, that the multipactor-detection channels chosen for a campaign really do register a discharge before the item is driven: drive a reference-event of known amplitude, compute each channel's signal-to-noise-ratio over its measured noise-floor, compare it with the required-registration-ratio at the exact boundary without relaxing it, confirm every declared channel holds a demonstration-record, confirm each record predates the first campaign-run and is still inside its validity-window, and derive the minimum-detectable-amplitude the demonstrated arrangement can claim. Trigger: ecss, e-st-20-01c, detection-capability-demonstration, reference-event-injection, signal-to-noise-ratio, measured-noise-floor, minimum-detectable-amplitude, demonstration-validity-window, testing-entity-evidence."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-detection-capability-verification, detection-capability-demonstration, reference-event-injection, signal-to-noise-ratio, measured-noise-floor, minimum-detectable-amplitude, demonstration-validity-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Detection Capability Verification (space-systems/ecss/e2001-detection-capability-verification)

Use when the task is the capability demonstration of
ECSS-E-ST-20-01C clause 7.3.1 -- the testing-entity proving, with
recorded evidence and before the RF-item is driven, that every chosen
multipactor-detection channel actually registers a discharge rather
than merely being installed and powered.

## Domain quick reference

- Clause 7.3.1 puts the burden on the testing-entity, and it is a
  demonstration, not a declaration: a reference-event of known
  amplitude is driven into the arrangement and each channel's recorded
  response is compared against its own measured noise-floor.
- The registration criterion is a ratio, not an absolute reading. A
  channel's signal-to-noise-ratio is its recorded response minus its
  measured noise-floor, both in dBm, and it is held against the
  campaign's required-registration-ratio in dB. A large raw response
  on a noisy channel proves nothing.
- Because that ratio is a difference of two dB figures, a
  demonstration sitting exactly on the required-registration-ratio can
  evaluate a few ULPs low in binary floating point. The comparison
  absorbs that representation error; the required ratio itself is
  never relaxed to make a case pass.
- Evidence has a direction in time and a shelf life. A demonstration
  recorded after the first campaign-run proves nothing about the runs
  that preceded it, and one older than the validity-window no longer
  describes the instrumentation as currently wired -- cabling,
  bias-settings and gauge calibration drift between set-ups.
- Coverage of the evidence is graded against the declared channel set,
  not against the records handed over: a channel with no record is an
  undemonstrated channel, and a record for a channel that is not in
  the declared set is an orphan record that signals a set-up mismatch.
- The demonstrated arrangement can only claim a
  minimum-detectable-amplitude equal to the worst (highest)
  per-channel floor plus the required-registration-ratio, restricted
  to the channels that actually passed. Quoting the best channel's
  figure as the arrangement's capability overstates what was proven.

## Workflow

1. Normalize every demonstration record: channel identifier, recorded
   response in dBm, measured noise-floor in dBm, and the timestamp of
   the demonstration. Reject a malformed timestamp, a non-numeric
   level and a duplicate record for one channel.
2. Compute each channel's signal-to-noise-ratio as response minus
   noise-floor and compare it with the required-registration-ratio
   under the boundary tolerance. A channel below it is recorded as not
   demonstrated, with its shortfall in dB.
3. Check the direction in time: a record whose timestamp is later than
   the first campaign-run is invalid evidence for that campaign,
   independent of how good the ratio is.
4. Check the validity-window: compute the age of each record against
   the campaign-run reference and flag a record older than the
   permitted window.
5. Reconcile the record set against the declared channel set. Report
   every declared channel with no record, and every record whose
   channel is not declared.
6. Derive the arrangement's minimum-detectable-amplitude from the
   passing channels: the highest measured noise-floor among them plus
   the required-registration-ratio. With no passing channel the
   capability is undefined and the demonstration has failed outright.
7. The detection capability is verified only when no channel is
   undemonstrated, no record is late or stale, no declared channel is
   missing evidence and no orphan record remains.

## Pitfalls

- Accepting a healthy raw response as proof and never subtracting the
  measured noise-floor -- a channel with a high floor can show a large
  reading and still be unable to separate a discharge from its own
  noise.
- Running the demonstration after the campaign has started, to save a
  chamber-cycle, and back-dating its validity -- the runs before the
  demonstration have no evidence behind them at all.
- Re-using a demonstration from an earlier set-up because the same
  instruments are involved -- the validity-window exists because the
  wiring, bias and calibration of those instruments do not survive a
  re-installation unchanged.
- Grading only the records handed over and never reconciling them
  against the declared channel set -- an undemonstrated channel
  disappears silently when it simply produces no record.
- Quoting the best channel's floor as the arrangement's
  minimum-detectable-amplitude -- the arrangement can only claim what
  its worst passing channel supports.
- Lowering the required-registration-ratio because a demonstration
  lands exactly on it -- the shortfall is dB-subtraction
  representation error and belongs in the comparison tolerance.

## Behavior contract (gate 3)

The record-normalization, signal-to-noise, boundary-tolerance,
timestamp-direction, validity-window, declared-set reconciliation and
minimum-detectable-amplitude logic is exercised by the gate 3 contract
test: scripts/test_e2001_detection_capability_verification.py against
scripts/e2001_detection_capability_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_detection_capability_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
