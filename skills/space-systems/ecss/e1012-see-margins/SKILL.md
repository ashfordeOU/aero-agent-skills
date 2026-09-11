---
name: e1012-see-margins
description: "Use when evaluate single event effects (SEE) margin compliance for space electronics under ECSS-E-ST-10C §5.5.3: categorize each event type as soft (SEU, SET, SEFI) or potentially destructive (SEL, SEB, SEGR), compute the predicted event count over the mission duration, apply the required margin factor, compare the margined total against the mission allowable, and flag any device that exceeds the allowable or lacks current-limiting protection for a destructive-category event. Trigger: ecss, e-st-10-system-scope, see-margins, seu, sel, single-event-effects, radiation-margins, space-electronics, latch-up."
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
  tags: [ecss, e-st-10-system-scope, see-margins, seu, sel, single-event-effects, radiation-margins, space-electronics, latch-up]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Single Event Effects Margins (space-systems/ecss/e1012-see-margins)

Use when the task is the per-device single event effects margin assessment of
ECSS-E-ST-10C §5.5.3 — categorizing SEE event types, computing the predicted
event count over the mission with the required margin factor applied, and
verifying that each device either satisfies the margined rate budget or carries
adequate protection measures for destructive-category events.

## Domain quick reference

- §5.5.3 groups SEE into two hazard categories based on the consequence
  of the event on the affected device:
  - **Soft**: the device state is altered but no physical damage occurs; the
    error is recoverable by reset, error-correcting code, or watchdog timeout.
    Event types: SEU (Single Event Upset), SET (Single Event Transient),
    SEFI (Single Event Functional Interrupt), MBU (Multiple Bit Upset).
  - **Potentially destructive**: the event can cause permanent device damage
    if the resulting current or voltage stress is not limited in time.
    Event types: SEL (Single Event Latch-up), SEB (Single Event Burnout),
    SEGR (Single Event Gate Rupture).
- The predicted SEE rate for a device comes from a radiation environment model
  (orbit, shielding) combined with the device's measured cross-section vs.
  linear energy transfer (LET) curve. The margin rule multiplies this rate by
  a margin factor (≥ 1.0; commonly 2× for soft errors, 10× for destructive)
  before comparing it to the mission allowable.
- Mission allowable is the maximum number of events (or the maximum rate) that
  the system design can tolerate over the full mission lifetime, derived from
  reliability and availability requirements at the system level.
- For destructive events the margin check alone is not sufficient: the device
  must also carry at least one hardware protection measure — current-limiting
  circuitry that prevents destructive current during a latch-up, or a
  power-cycling recovery capability that clears the latched state before damage
  threshold is reached.

## Workflow

1. For each device under assessment, identify every credible SEE event type
   (SEU, SET, SEFI, MBU, SEL, SEB, SEGR) that the device's technology is
   susceptible to, and categorize each type as soft or potentially destructive.
   Reject any unrecognised event type before it enters the margin calculation.
2. For each (device, event type) pair, obtain the predicted event rate in
   events/device/day from the radiation analysis. Confirm the rate is non-negative
   and that the mission duration is positive; both are required to proceed.
3. Compute the predicted event count over the full mission:
   `predicted_events = predicted_rate × mission_duration_days`
   Apply the required margin factor:
   `margined_events = predicted_events × margin_factor`
   The margin factor must be ≥ 1.0 (no relaxation below unity is permitted).
4. Compare `margined_events` against the `allowable_events` for that device
   and event type:
   - `margin_ratio = allowable_events / margined_events`
   - **PASS** if `margin_ratio ≥ 1.0`; **FAIL** otherwise.
   - A predicted rate of zero always yields PASS (ratio = ∞); record it
     explicitly so the reviewer can confirm the zero is physically justified
     and not a missing analysis.
5. For each potentially destructive event type (SEL, SEB, SEGR), perform
   a separate protection check regardless of the margin outcome:
   - Confirm the device has at least one protection measure on record:
     hardware current-limiting, or a power-cycling recovery scheme with a
     cycle time within the device's survival time limit.
   - Flag a MISSING finding if neither measure is recorded; a device with
     a PASS margin but no SEL protection is not compliant.
6. A device is SEE-compliant for a given event type only when both conditions
   hold: the margin check is PASS **and** (the event type is soft, OR the
   protection check is confirmed present). Aggregate all per-device findings;
   the device's overall SEE status is non-compliant until every event-type
   finding is clear.

## Pitfalls

- Applying the allowable as a rate and the margin check as a count, or
  vice versa, without consistent units — normalize everything to total events
  over the mission before comparing.
- Treating a zero predicted rate as a global waiver and omitting the device
  from the record entirely; every device must appear in the assessment,
  with a note confirming the basis for a zero rate prediction.
- Using a margin factor less than 1.0 (i.e., relaxing below the predicted
  value) — the margin is a penalty multiplier on the predicted rate, never a
  discount; any margin factor below 1.0 is a configuration error.
- Concluding a destructive event is acceptable because the margined rate PASS
  is achieved, while the protection check has not been performed or is missing;
  both checks must pass independently.
- Conflating SEL with SEU in the protection check step because both involve a
  stored-state perturbation — SEL is a current-mode latch-up with potentially
  destructive power dissipation, qualitatively different from a bit flip, and
  always requires dedicated hardware mitigation.

## Behavior contract (gate 3)

The event categorization, margin computation, protection check, and
full-device assessment logic are exercised by the gate 3 contract test:
scripts/test_e1012_see_margins.py against scripts/e1012_see_margins_logic.py
(stdlib unittest, offline, ≥ 10 test cases). Run:
python3 scripts/test_e1012_see_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
