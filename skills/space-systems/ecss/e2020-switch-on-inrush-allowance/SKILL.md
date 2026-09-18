---
name: e2020-switch-on-inrush-allowance
description: "Verify a turn-on current profile exceeds the class current only while the input filter is charging. Use when ECSS-E-ST-20-20C clause 5.3.2.1.1 asks a switch-on transient to be justified rather than merely observed: group every profile segment above the class current by its declared cause, reject an excess not attributable to input-filter charging, charge the filter at the current left over once the steady load is served, confirm the whole excess finishes inside the shortest trip-off delay with margin, check the declared excess matches what the filter needs, and confirm the profile settles below the class current. Refuses an unknown cause and a steady load consuming the limiting current. Trigger: ecss, e-st-20-20c, lcl-switch-on-inrush-allowance, input-filter-charging-excess, turn-on-current-profile-attribution, inrush-duration-against-trip-off-delay, post-inrush-settling-current, leftover-charge-current."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-switch-on-inrush-allowance, input-filter-charging-excess, turn-on-current-profile-attribution, inrush-duration-against-trip-off-delay, post-inrush-settling-current, leftover-charge-current]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Switch-On Inrush Allowance (space-systems/ecss/e2020-switch-on-inrush-allowance)

Use when the task is the turn-on transient check of ECSS-E-ST-20-20C
clause 5.3.2.1.1 — showing that the only reason a load draws more than
the class current of its line while switching on is that the input
filter of that load is being charged, and that the excess stops when the
charging does.

## Domain quick reference

- Turning a line on is the one moment the allowance exists, and it is
  conditional twice over: on the CAUSE of the excess and on its
  DURATION. An excess that is real, short and harmless is still outside
  the allowance if input-filter charging is not what produced it.
- So this is an attribution problem before it is an arithmetic one. The
  turn-on profile is walked segment by segment, every segment above the
  class current is picked out, and each has to name filter charging as
  its cause. A segment above the class current because the load was
  already enabled, or because a downstream converter began its own soft
  start, is a different clause's problem and a finding here.
- The charging current is not the limiting current. The load is served
  from the same limited output, so the filter is charged by what is left
  over: C*V divided by the limiting current minus the steady load.
  Charging at the full limiting current understates the duration, and it
  understates it most on exactly the heavily loaded lines where the
  duration matters.
- A line whose steady load already consumes the limiting current never
  finishes charging and never comes on. That is not a margin finding, it
  is an input the assessment refuses.
- The excess has to be over before the limiter opens, so it is compared
  against the SHORTEST trip-off delay with the project margin applied to
  the excess rather than by relaxing the delay.
- The declared excess is checked against the charge the filter actually
  needs, in both directions. Much longer than the need is unattributed
  draw wearing a filter label; much shorter says the filter never
  finished charging, so the profile does not describe the real turn-on.
- The profile has to settle. Once the filter is charged the current
  returns below the class current, which is where the steady-state
  clause takes over; a profile ending above the class current has not
  completed a turn-on, it has started an overload.
- A peak above the limiting current is not a profile the line can
  produce. The limiter holds its output in the band, so a declared peak
  above it is a measurement or a model error rather than a design
  finding.
- The trip-off margin, the attribution tolerance band and the window
  advisory floor are declared project policy rather than physical
  constants; the defaults in the logic module are a starting point a
  project substitutes its own values into.

## Workflow

1. Validate the profile: unique labels, a known cause on every segment,
   a non-negative current and a positive duration. A segment with no
   named cause cannot be attributed and is refused rather than assumed
   benign.
2. Refuse the degenerate inputs first: a limiting current at or below
   the class current leaves no allowance to assess, and a steady load at
   or above the limiting current leaves nothing to charge with.
3. Group the segments above the class current by cause, keeping the
   permitted and the unattributed ones separately, and total both the
   whole excess and the part attributed to filter charging.
4. Charge the input filter at the current left over once the steady load
   is served, and report that leftover current alongside the duration so
   a reviewer can see which figure was used.
5. Compare the whole excess, with margin, against the shortest trip-off
   delay, and report the slack and the share of the delay consumed.
6. Compare the attributed excess against the charge the filter needs,
   flagging both a declared excess far longer than the need and one far
   shorter.
7. Confirm the last segment sits strictly below the class current.
8. Close with a verdict naming every finding, and an advisory where
   everything passes but the excess consumes most of the delay.

## Pitfalls

- Charging the filter at the full limiting current. The steady load is
  served from the same output, so the charge runs on the difference, and
  the shortcut understates the duration exactly where the line is most
  heavily loaded.
- Justifying any turn-on excess as inrush. The allowance names one
  cause; a load enable, a soft start or a secondary bus being energised
  above the class current is outside it however brief.
- Comparing the excess with a nominal or longest trip-off delay. The
  unit may open at the shortest delay in the window, so that is the
  figure the excess is measured against.
- Checking only that the excess fits. An excess that fits the delay but
  runs far longer than the filter needs is unattributed draw, and the
  duration comparison against the computed charge is what exposes it.
- Ignoring an excess shorter than the charge time. It says the filter
  did not finish charging inside the declared profile, so either the
  profile or the capacitance figure is wrong.
- Forgetting the settling check. A profile that ends above the class
  current has described an overload, not a turn-on, and the steady-state
  clause it hands over to will fail as well.
- Accepting a declared peak above the limiting current. The limiter
  holds its output in the band, so such a profile is an instrumentation
  or model error, and treating it as a design finding sends the
  investigation the wrong way.
- Comparing a charge duration with a trip-off delay by bare arithmetic.
  The duration is a product divided by a difference, so a case meant to
  sit exactly on the delay can land a few units in the last place the
  wrong side of it; the comparison absorbs that representation error
  while the delay stays as declared.

## Behavior contract (gate 3)

The policy validation, profile validation, leftover charge current,
input filter charge time, excess grouping by cause, trip-window
comparison, two-sided attribution check, settling check and overall
verdict are exercised by the gate 3 contract test:
scripts/test_e2020_switch_on_inrush_allowance.py against
scripts/e2020_switch_on_inrush_allowance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_switch_on_inrush_allowance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
