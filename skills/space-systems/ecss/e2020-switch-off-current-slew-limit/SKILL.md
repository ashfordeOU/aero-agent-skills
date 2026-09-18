---
name: e2020-switch-off-current-slew-limit
description: "Evaluate whether a unit holds its output-current fall inside the declared switch-off slew ceiling, per ECSS-E-ST-20C clause 5.4.2.2.1. Use when a turn-off trace has to answer two questions at once: the steepest collapse against the declared ceiling, and the transient that same rate drives across the harness inductance against the bus allowance. Validate the time base, rate every segment, take the abrupt let-go rather than the mean decay, convert it into an induced volt, judge both at inclusive equality, and name the limit that actually binds each corner. Trigger: ecss, e-st-20-electrical-scope, switch-off-current-slew-limit, turn-off-current-fall-rate, peak-collapse-segment, harness-inductance-induced-transient, bus-transient-allowance-margin, switch-off-corner-headroom."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-switch-off-current-slew-limit, turn-off-current-fall-rate, peak-collapse-segment, harness-inductance-induced-transient, bus-transient-allowance-margin, switch-off-corner-headroom, output-current-fall-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Switch-Off Current Slew Limit (space-systems/ecss/e2020-switch-off-current-slew-limit)

Use when the task is the turn-off rate-of-fall requirement of
ECSS-E-ST-20C clause 5.4.2.2.1 -- showing that while the device is
switching off, the output current comes down no faster than the
declared ceiling, and that the collapse the trace does show is one the
installed harness can absorb.

## Domain quick reference

- Turning an output off is the more violent half of the switching
  cycle. The harness between the switch and the load is an inductor
  carrying the load current, and collapsing that current faster than
  the design allowed for drives a transient back onto the bus and
  across the switch element.
- The steepest falling stretch is the quantity, not the load current
  divided by the total decay time. A switch that lets go abruptly at
  the end of a leisurely decay passes on the mean and fails on the
  rate, and the mean is the number that tends to get quoted.
- The trace owes two answers, not one. A rate of fall inside the
  ceiling can still put more transient on the bus than the allowance
  permits whenever the installed harness is more inductive than the
  ceiling was set against, so the two checks bind at different corners
  and neither substitutes for the other.
- Half a transient check is no check. An inductance with no allowance
  behind it, or an allowance with no inductance, leaves the harness
  question untested while looking like it was asked, so the result says
  so rather than quietly passing.
- A trace that never falls is not a switch-off. It carries no rate to
  judge, and reading it as comfortable is how this clause gets closed
  on nothing.
- Both comparisons are inclusive. A rate landing exactly on the ceiling
  or a transient landing exactly on the allowance meets the
  requirement, and the tolerance absorbs representation error rather
  than loosening either limit.

## Workflow

1. Read the declared rate-of-fall ceiling. Without it there is nothing
   a measured collapse can be judged against and the assessment closes.
2. Validate each switch-off trace as a time series: two samples at
   least, times rising, currents real and never negative.
3. Rate every segment and take the steepest collapse. Carry the mean
   decay alongside it so the gap between the two is visible rather than
   assumed.
4. Where the harness inductance and the bus transient allowance are
   both declared, turn the peak rate into the voltage it develops and
   compare it with the allowance. Where only one is declared, record
   that the harness question went untested.
5. Judge both limits at inclusive equality, carry each headroom as a
   fraction of its limit, and keep the lower of the two as the margin
   that binds the trace.
6. Report the worst trace by that binding margin, every finding, and
   the advisories for traces the harness binds rather than the ceiling.

## Pitfalls

- Quoting the mean decay rate. It is the number that passes, and the
  abrupt let-go it averages away is the event the harness actually
  sees.
- Checking the slew ceiling and stopping. The ceiling was set against
  an assumed inductance; the flight harness is the one that matters,
  and a longer or tighter-routed run moves the transient without
  moving the rate.
- Declaring an inductance with no allowance behind it. The arithmetic
  runs, a voltage comes out, and nothing is ever compared with
  anything.
- Reading a flat capture as a comfortable switch-off. A trace that
  starts and ends at the same current shows no turn-off at all.
- Comparing a rate with the ceiling by bare arithmetic. The rate comes
  out of a division, so a collapse sitting exactly on the ceiling can
  fall a few units in the last place outside; the comparison absorbs
  that representation error while the declared limits stay untouched.

## Behavior contract (gate 3)

The trace validation, segment rates, peak-versus-mean collapse,
induced-transient conversion, half-declared transient advisory, binding
margin and worst-trace report are exercised by the gate 3 contract
test: scripts/test_e2020_switch_off_current_slew_limit.py against
scripts/e2020_switch_off_current_slew_limit_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_switch_off_current_slew_limit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
