---
name: mil-std-1797a
description: "Assess the flying qualities of a piloted aircraft against MIL-STD-1797A level criteria: classify the flight phase category (A precision tracking, B gradual nonterminal, C terminal), select the aircraft class (I small light, II medium, III large heavy, IV high maneuverability), and grade each dynamic mode against the level tables: short period damping and frequency by category and class, phugoid minimum damping 0.04, dutch roll minimum damping 0.19, spiral minimum time to double 20 s, roll mode maximum time constant 1.0 s, roll performance. Produces a Level 1, 2, or 3 verdict per mode, the overall limiting level, and the Cooper-Harper band. Use when the task is flying qualities assessment, handling qualities level classification, or MIL-STD-1797A compliance review. Trigger: mil-std-1797a, flying qualities, handling qualities, short period, dutch roll, phugoid, spiral mode, roll mode, roll performance, flight phase category, aircraft class, cooper-harper band."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mil-std-1797a
    reference-only: true
gated: false
domain: flight-mechanics
pack: handling-qualities
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: handling-qualities
  tags: [mil-std-1797a, flying-qualities, short-period, dutch-roll, phugoid, spiral-mode, roll-mode, roll-performance, flight-phase-category, aircraft-class, cooper-harper-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# MIL-STD-1797A Flying Qualities Assessment (flight-mechanics/handling-qualities/mil-std-1797a)

Use when the task is grading the dynamic stability and response modes
of a piloted aircraft against the MIL-STD-1797A (and its predecessor
MIL-F-8785C) flying qualities level criteria: classify the flight
phase category and aircraft class, check each mode against the level
tables, and report the Level 1, 2, or 3 verdict plus the overall
limiting level and Cooper-Harper band. This is the level-criteria
leaf; mode derivative extraction and eigenvalue computation live in
the stability-control leaves.

## Domain quick reference

- Flight phase categories: A = nonterminal phases requiring rapid
  maneuvering, precision tracking, or precise flight-path control
  (air-to-air combat, ground attack, in-flight refueling as receiver,
  terrain following); B = nonterminal phases accomplished gradually
  without precision tracking (climb, cruise, loiter, descent); C =
  terminal phases (takeoff, approach, landing, wave-off).
- Aircraft classes: I = small light (utility, primary trainer); II =
  medium weight, medium maneuverability (small transport, tactical
  bomber); III = large heavy, low maneuverability (heavy transport,
  tanker, bomber); IV = high maneuverability (fighter, attack).
- Flying qualities levels: 1 = clearly adequate, desired performance
  with minimal pilot compensation; 2 = adequate with increased pilot
  workload or degraded mission effectiveness; 3 = safe but marginal,
  controllable with excessive workload. The overall level is the worst
  (limiting) level across modes.
- Short period (damping bands are category independent): Level 1
  damping 0.35 to 1.30, Level 2 0.25 to 2.00, Level 3 minimum 0.15.
  Minimum frequency (rad/s) is a function of category, class, and
  n/alpha (g/rad), interpolated linearly between n/alpha = 1.0 and
  3.0 and clamped outside: category A classes I/II/III/IV start at
  3.6/3.6/3.0/2.5 and rise to 6.0; categories B and C start at 1.0
  and rise to 2.0. Level 1 requires both damping and frequency; a
  frequency shortfall with Level 1 damping grades Level 2.
- Phugoid: Level 1 damping >= 0.04; Level 2 damping >= 0 (stable);
  Level 3 time to double >= 55 s (slow divergence allowed).
- Dutch roll (damping ratio, minimum frequency rad/s, minimum
  damping-frequency product): Level 1 category A class IV: 0.19, 1.0,
  0.35; category A classes I-III: 0.19, 0.4, 0.35; categories B and C:
  0.08, 0.4, 0.15. Level 2: 0.02, 0.4, 0.05. Level 3: damping > 0
  (stable oscillation).
- Spiral mode minimum time to double: Level 1 20 s (A and C), 12 s
  (B); Level 2 8 s; Level 3 4 s.
- Roll mode maximum time constant (s): Level 1 1.0 (A), 1.4 (B), 1.0
  (C); Level 2 1.4 (A), 3.0 (B), 1.4 (C); Level 3 10 (all).
- Roll performance (category A only): time to a 60 deg bank angle
  change: Level 1 1.3 s (classes I, II, IV) or 1.7 s (III); Level 2
  1.8 s (I, II, IV) or 2.5 s (III); Level 3 3.6 s (I, II, IV) or 5.0 s
  (III). The first-order roll response phi(t) = p_ss * (t - tau *
  (1 - exp(-t / tau))) converts a steady roll rate p_ss and roll mode
  time constant tau into the bank angle reached in 1 s, the time to
  60 deg, and the time to 90 deg.
- Cooper-Harper tie-in: Level 1 maps to ratings 1-3 (satisfactory
  without improvement), Level 2 to 4-6 (deficiencies warrant
  improvement), Level 3 to 7-9 (deficiencies require improvement);
  rating 10 (uncontrollable) sits outside the level framework. The
  pilot-assigned rating itself is collected per the
  cooper-harper-rating leaf.

## Workflow

1. Classify the flight phase category (A, B, or C) from the mission
   segment and the aircraft class (I to IV) from the vehicle type.
2. Gather the measured or simulated mode metrics: short period damping
   and frequency (and n/alpha), phugoid damping, dutch roll damping
   and frequency, spiral time to double (or stable), roll mode time
   constant, and steady roll rate with roll mode time constant for
   roll performance.
3. Run each mode assessment from scripts/flying_qualities_logic.py,
   e.g. assess_short_period({"zeta_sp": 0.7, "omega_sp": 3.0}, "A",
   "IV") returns {"level": 1, "verdict": "PASS", ...}. Every assess
   function validates category, class, and inputs and raises
   ValueError on invalid category, class, or non-physical values.
4. Combine with overall_flying_qualities_level(state, category,
   aircraft_class): it runs all six modes, returns the overall
   limiting level, the limiting modes, and the Cooper-Harper band
   (1 to 3 for Level 1, 4 to 6 for Level 2, 7 to 9 for Level 3).
   Roll performance reports level None for categories B and C
   (the criterion applies to category A only) and is skipped by
   combine_levels.
5. Interpret against the requirement: Level 1 is the usual
   procurement and safety requirement for the operational envelope;
   any Level 3 mode flags a safety-marginal condition; a divergent
   mode (negative damping) grades Level 3 and needs design action.

## Worked example

Fighter in air-to-air combat (category A, class IV) with measured
mode metrics: short period zeta 0.7, omega 3.0 rad/s, n/alpha 1.0;
phugoid zeta 0.05; dutch roll zeta 0.25, omega 1.5 rad/s; spiral
time to double 25 s; roll mode tau 0.8 s; steady roll rate 100 deg/s
with tau 0.5 s. Run:

```python
import sys
sys.path.insert(0, "scripts")
from flying_qualities_logic import overall_flying_qualities_level
state = {"zeta_sp": 0.7, "omega_sp": 3.0, "n_over_alpha": 1.0,
         "zeta_ph": 0.05, "zeta_dr": 0.25, "omega_dr": 1.5,
         "t2_spiral": 25.0, "tau_roll": 0.8,
         "roll_rate_ss": 100.0, "roll_mode_tau": 0.5}
result = overall_flying_qualities_level(state, "A", "IV")
print(result["level"], result["limiting_modes"],
      result["cooper_harper_band"])
```

Every mode is Level 1: short period frequency 3.0 >= 2.5 rad/s
minimum and damping 0.7 in band; dutch roll product 0.375 >= 0.35;
spiral 25 s >= 20 s; roll mode 0.8 s <= 1.0 s; roll performance
time to 60 deg about 1.04 s <= 1.3 s. Result: level 1, no limiting
mode, Cooper-Harper band 1-3. Now degrade the spiral to 10 s:
overall drops to level 2 with limiting mode "spiral" and band 4-6.
A short period damping of 0.15 drops the short period verdict to
level 3 and the overall level to 3.

## Verification checklist

- [ ] Category, class, and level definitions match the standard's
      framing (A/B/C, I-IV, levels 1-3).
- [ ] Short period: damping 0.35-1.30 Level 1; frequency table by
      category/class with n/alpha interpolation.
- [ ] Phugoid: 0.04 Level 1 minimum damping; 55 s Level 3 time to
      double for divergence.
- [ ] Dutch roll: 0.19 / 1.0 / 0.35 category A class IV Level 1;
      product criterion enforced (a high frequency alone does not
      pass a low damping product).
- [ ] Spiral: 20 s (A, C) and 12 s (B) Level 1; 8 s Level 2; 4 s
      Level 3.
- [ ] Roll mode: 1.0 s category A Level 1 maximum.
- [ ] Roll performance: 60 deg bank criterion per class, first-order
      response model, category A only.
- [ ] Overall level is the worst limiting level; Cooper-Harper band
      reported.
- [ ] Contract test passes: python3 scripts/test_flying_qualities.py
      (offline, deterministic, all known-good values asserted).

## Pitfalls

- Misclassifying category or class: the short-period frequency floor and the
  dutch roll tables are category- and class-dependent (category A class IV
  starts at 2.5 rad/s, category B at 1.0), so a Level 1 verdict computed for
  A/IV is not transferable to another category/class.
- Checking dutch roll on damping alone: the product criterion (damping times
  frequency) is enforced, so a high frequency does not pass a low damping
  product; report the limiting of damping, frequency and product.
- Applying roll performance outside category A: the time-to-60-deg criterion
  applies to category A only; assess_roll_performance reports level None for
  B and C and combine_levels skips it, so do not force a category-A roll
  rate check in cruise.
- Comparing spiral and roll mode in the wrong units: spiral is a minimum
  time to double (s) and roll mode a maximum time constant (s); they grade
  on separate tables and are not interchangeable thresholds.
- Reading the overall level from one mode: the overall level is the worst
  (limiting) level across all six modes, so a single Level 3 mode (for
  example divergent spiral time to double below 4 s) drops the whole
  assessment even when every other mode is Level 1.
- Passing invalid category, class or non-physical metrics: every assess
  function validates and raises ValueError on invalid category/class strings
  and non-physical values such as negative damping.

## Behavior contract (gate 3)

scripts/test_flying_qualities.py (stdlib unittest, offline) is the
correct-answer oracle: it asserts the known-good Level 1 case
(short period damping 0.7, frequency 3.0 rad/s, category A, class IV),
the low damping case (0.15 grades Level 3, not Level 1), the spiral
Level 2 case (time to double 10 s, category A), the dutch roll
product gating, the first-order roll response values (bank angle in
1 s about 56.77 deg and time to 90 deg about 1.37 s for p_ss 100
deg/s and tau 0.5 s), the overall limiting level, the Cooper-Harper
band tie-in, and ValueError on invalid category, class, and
non-physical inputs. Run: python3 scripts/test_flying_qualities.py.

## Related skills

- cooper-harper-rating: collects the pilot-assigned rating that the
  level bands map to; use together for piloted evaluation results.
- dynamic-stability: computes eigenvalues and mode metrics from
  derivatives; feed its outputs into this leaf's assess functions.
- short-period-mode-analysis: derives short period frequency and
  damping from stability derivatives; this leaf grades the result.
- lateral-directional-stability: derives dutch roll, roll, and
  spiral mode metrics; this leaf grades them.
- pilot-induced-oscillation: PIO susceptibility is a separate
  pilot-in-the-loop coupling assessment, not a mode level.

## Compliance

MIL-STD-1797A (Flying Qualities of Piloted Aircraft, successor to
MIL-F-8785C) is referenced, not reproduced: the criteria tables in
scripts/flying_qualities_logic.py are a summary paraphrase of the
standard's level framework for assessment use (compliance
STANDARDS-REF, reference-only: true, gated: false).
