---
name: e2020-rlcl-limitation-mode-derating
description: "Verify component derating in a retriggerable limiter holding current limitation, per ECSS-E-ST-20C clause 5.2.3.5.1. Use when a latching current limiter must be shown safe through a sustained limitation event and not only in steady conduction: take the upper bus voltage with the upper edge of the limitation band, collapse the output onto the faulted load, divide the differential across the series parts, choose peak or duty-averaged power per part from its thermal time constant, raise junction temperature through the mounting path, then compare voltage, current, power and temperature against each derated rating and name the limiting part. Trigger: ecss, e-st-20-electrical-scope, rlcl-limitation-mode-derating, rlcl-pass-device-limitation-dissipation, rlcl-limitation-mode-junction-temperature, retrigger-duty-cycle-averaging, rlcl-limitation-derating-margin, limiter-differential-voltage-share."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-rlcl-limitation-mode-derating, rlcl-limitation-mode-derating, rlcl-pass-device-limitation-dissipation, rlcl-limitation-mode-junction-temperature, retrigger-duty-cycle-averaging, rlcl-limitation-derating-margin, limiter-differential-voltage-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — RLCL Limitation Mode Derating (space-systems/ecss/e2020-rlcl-limitation-mode-derating)

Use when the task is the derating question of ECSS-E-ST-20C clause
5.2.3.5.1 -- showing that the parts inside a retriggerable latching
current limiter stay inside their derated ratings during the one state
that actually stresses them, the interval the limiter spends holding its
output current at the limitation value.

## Domain quick reference

- A retriggerable limiter spends almost all of its life in conduction,
  where the drop across it is small and nothing is stressed. The clause
  is not about that life. In limitation mode the same part is a series
  element carrying its full limitation current across nearly the whole
  bus voltage, and a derating case closed on the conduction point says
  nothing about it.
- The operating point is the worst corner. Dissipation rises with the
  input voltage and with the current, so the assessment takes the upper
  bus voltage, the upper edge of the limitation band -- the band,
  because a limitation threshold is a tolerance and not a number -- and
  the lowest output voltage the faulted load can impose.
- The differential is shared among the series parts and the shares have
  to add up. The pass device takes most of it, a sense element takes a
  little, and the sum cannot exceed the differential itself. A set whose
  declared shares total more than one is describing a voltage the bus
  never supplied, so it is refused rather than assessed.
- Retriggering thins the heat, but only for a part slow enough to feel
  the average. A limiter holds limitation for a dwell, opens, and
  retries. A part whose thermal time constant is longer than the dwell
  runs at the duty-averaged power; a part faster than the dwell reaches
  the peak on every cycle, and a part that declares no time constant is
  taken at the peak because nothing said otherwise.
- Derating is four limits, not one. Voltage, current, power and
  junction temperature each carry a factor, and a part can sit
  comfortably inside three while the fourth is what fails. The limiting
  component is the smallest margin across all four, and it is named
  because it is the part a redesign has to move.
- The factors are declared project policy rather than physical
  constants, so the policy reference travels with the verdict and a set
  of factors with no policy behind it closes the assessment instead of
  passing it.

## Workflow

1. Declare the limitation-mode operating point: upper input voltage,
   the output voltage the fault holds, the limitation current with its
   tolerance, the dwell, the retrigger recovery and the mounting
   temperature. Reject a point whose output is not below its input,
   because that is conduction and not limitation.
2. Resolve the stressing quantities from that point -- the differential
   across the limiter, the upper edge of the limitation band, and the
   peak dissipation their product gives.
3. Take the retrigger duty from the dwell and the recovery, and carry
   the duty-averaged dissipation alongside the peak. A limiter with no
   declared recovery is treated as holding limitation continuously.
4. Read the series component set and check the declared differential
   shares divide the differential rather than exceeding it. Refuse a
   duplicate identifier and an empty set.
5. For each component choose the governing power from its thermal time
   constant against the dwell, then raise its junction temperature from
   the mounting reference through its thermal resistance.
6. Compare voltage, current, power and junction temperature against the
   derated allowances, taking the tighter of the component ceiling and
   the policy ceiling. Record the utilisation of each limit rather than
   a bare pass.
7. Report the limiting component, the limit that binds it, and every
   exceedance; close with the policy reference the factors came from.

## Pitfalls

- Closing the derating case on the conduction point. The limiter is
  barely stressed there. The clause is about the limitation interval,
  and a file that never analysed it has not addressed the requirement
  at all.
- Running the nominal limitation current. The threshold is a tolerance
  band and the high edge is what heats the part, so a case quoted on
  the nominal understates the dissipation on every unit that builds to
  the high side.
- Averaging the power for a fast part. A device whose thermal time
  constant is shorter than the dwell reaches the peak junction
  temperature within the first dwell, so a duty-averaged number for it
  is not conservative -- it is simply the wrong number.
- Assessing only the pass device. The small series parts carry the same
  current with far worse thermal paths, and the limiting component is
  often the sense element rather than the device everybody looked at.
- Comparing a stress with its allowance by bare arithmetic. Both sides
  come out of float products, so a part sitting exactly on its derated
  allowance can land a few units in the last place above it; the
  comparison absorbs that representation error while the allowance
  itself stays untouched.

## Behavior contract (gate 3)

The policy validation, limitation-point resolution, share accounting,
peak-versus-averaged power selection, junction-temperature rise,
four-limit derating comparison and limiting-component report are
exercised by the gate 3 contract test:
scripts/test_e2020_rlcl_limitation_mode_derating.py against
scripts/e2020_rlcl_limitation_mode_derating_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_rlcl_limitation_mode_derating.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
