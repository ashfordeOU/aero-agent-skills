---
name: e2006-secondary-arc-pass-criteria
description: "Use when verify the pass conditions of a secondary-arc qualification-campaign on a solar-array coupon under ECSS-E-ST-20-06C clause 7.2.3.3: confirm the campaign envelope bounds the worst-case string-voltage, string-current, primary-arc population and bias-dwell, categorize every recorded discharge event as non-sustained, temporary-sustained or permanent-sustained from its duration, its peak arc-current and how it terminated, reject any sustained event against the no-sustained-arc condition, evaluate the string-to-string insulation from pre-campaign and post-campaign insulation-resistance, separate cosmetic discoloration from disqualifying carbonized-track, melted-insulation and exposed-conductor damage, and aggregate the three conditions into one verdict. Trigger: ecss, e-st-20-06c, secondary-arc-pass-criteria, sustained-arc, permanent-sustained-arc, temporary-sustained-arc, string-to-string-insulation, insulation-resistance-retention, arc-extinction, solar-array-coupon-campaign."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-secondary-arc-pass-criteria, e-st-20-06c, secondary-arc, sustained-arc, string-to-string-insulation, insulation-resistance-retention, arc-extinction, solar-array-coupon-campaign]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Secondary-Arc Pass Criteria (space-systems/ecss/e2006-secondary-arc-pass-criteria)

Use when the task is the clause 7.2.3.3 acceptance decision of
ECSS-E-ST-20-06C: a secondary-arc qualification-campaign has run on a
solar-array coupon, and the coupon is admissible only if no sustained
discharge was recorded and the insulation between adjacent strings came
through the campaign undamaged.

## Domain quick reference

- A primary arc on an array surface is a short blow-off of charge; it
  becomes a secondary arc when the string's own generated current feeds
  the resulting plasma across the gap between two strings at different
  potentials. The pass decision is not about the primary-arc count — the
  campaign deliberately triggers those — it is about what the string did
  afterwards.
- Every recorded discharge event is categorized into exactly one of three
  families before any verdict is formed. Non-sustained: the event decayed
  inside the supply transient-recovery window, or drew less current than
  the string can feed, so the string never sustained it.
  Temporary-sustained: the discharge self-extinguished, but only after
  conducting string-sustainable current well past that window.
  Permanent-sustained: the discharge was still burning when the bias
  supply was externally cut off, so the coupon never demonstrated
  extinction at all. An event with an unrecognized termination mode is
  rejected, not silently counted as benign.
- The no-sustained-arc condition admits non-sustained events only. Both
  sustained families are findings; a permanent-sustained event is the
  more severe because the extinction behaviour was never observed, but a
  temporary-sustained event is equally disqualifying unless the
  programme has explicitly argued the case for admitting it.
- The insulation condition has three parts, all of which must hold: the
  post-campaign string-to-string insulation-resistance stays at or above
  the required floor; it retains a minimum fraction of its pre-campaign
  value (a collapse from a very high starting value is a finding even
  when the absolute floor is still met); and the observed surface
  condition carries no disqualifying damage. Discoloration and surface
  deposit are cosmetic; carbonized-track, melted-insulation,
  exposed-conductor and a string-to-string short are disqualifying.
- A verdict is only meaningful if the campaign envelope bounded the
  flight worst case — applied string-voltage and string-current at or
  above the worst-case values, the required primary-arc population
  reached, and the bias dwell at least as long as required. A clean arc
  record obtained inside too small an envelope proves nothing.

## Workflow

1. Check the campaign envelope against the flight worst case: applied
   string-voltage, applied string-current, primary-arc population and
   bias-dwell duration. Record the voltage and current margins; each
   shortfall is a coverage finding that stands on its own.
2. Categorize each recorded discharge event from its duration, its peak
   arc-current and its termination mode. Externally cut off implies
   permanent-sustained. A self-extinguished event below the current the
   string can sustain, or inside the transient-recovery window, is
   non-sustained. Anything else is temporary-sustained.
3. Apply the no-sustained-arc condition: raise a finding for every
   permanent-sustained event, and for temporary-sustained events unless
   they were explicitly admitted by the programme.
4. Evaluate the string-to-string insulation: compare post-campaign
   insulation-resistance against the required floor, compute the
   retention ratio against the pre-campaign value and compare it against
   the retention floor, and separate the observed conditions into
   cosmetic and disqualifying. Reject an uncategorized condition.
5. Aggregate the coverage, arc and insulation finding lists. The coupon
   passes clause 7.2.3.3 only when all three lists are empty; report the
   finding count with the verdict so a near-miss is visible.

## Pitfalls

- Reading "the arc went out" as a pass. Self-extinction distinguishes a
  temporary-sustained event from a permanent-sustained one; it does not
  make the event non-sustained. Only duration inside the
  transient-recovery window, or current below what the string can feed,
  does that.
- Judging the insulation on the absolute resistance floor alone. An
  insulation that fell from a hundred gigaohm to two gigaohm still clears
  a one-gigaohm floor while having lost most of its dielectric strength;
  the retention ratio is what catches it.
- Treating visible marking as automatic failure. Discoloration and
  surface deposit are cosmetic outcomes of the plasma exposure; only a
  carbonized-track, melted-insulation, exposed-conductor or
  string-to-string short is disqualifying.
- Declaring a pass from a campaign whose applied string-voltage or
  string-current sat below the flight worst case. Coverage findings are
  not softened by a clean arc record — they invalidate it.
- Comparing an exactly-compliant measurement against a limit with a bare
  float comparison. Durations arrive as timestamp differences and applied
  voltages as sums of segment values, so a compliant value can land a few
  ULPs on the wrong side; the logic absorbs that representation error
  without widening any engineering limit.

## Behavior contract (gate 3)

The coverage, event-categorization, no-sustained-arc and
insulation-condition logic is exercised by the gate 3 contract test:
scripts/test_e2006_secondary_arc_pass_criteria.py against
scripts/e2006_secondary_arc_pass_criteria_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2006_secondary_arc_pass_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
