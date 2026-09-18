---
name: e2020-current-telemetry-full-scale
description: "Verify that the current telemetry of a protected power output still reads at the point its protection device limits, against clause 5.2.8.3.1 of ECSS-E-ST-20-20C. Use when a latching or fold-back limiter output carries a shunt, amplifier and converter chain and the question is whether the reported current reaches the worst-case maximum limitation current: build that limit from the class current, the limiting ratio and the arithmetic sum of tolerance, temperature, ageing, radiation and supply spreads, refer the converter span back through gain and shunt, name whichever of amplifier or converter clips first, then report headroom and the current one code represents. Trigger: ecss, e-st-20-20c-clause-5-2-8-3-1, current-telemetry-full-scale, protection-device-limitation-current, telemetry-chain-clipping, protection-limit-current-telemetry-coverage, telemetry-range-versus-limitation-current, shunt-and-gain-referral."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e-st-20-20c-clause-5-2-8-3-1, e2020-current-telemetry-full-scale, e-st-20-20c, current-telemetry-full-scale, protection-device-limitation-current, telemetry-chain-clipping, protection-limit-current-telemetry-coverage, telemetry-range-versus-limitation-current]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Interface — Current Telemetry Full Scale (space-systems/ecss/e2020-current-telemetry-full-scale)

Use when the task is clause 5.2.8.3.1 of ECSS-E-ST-20-20C: the range of
the current telemetry on a protected output has to reach at least the
maximum limitation current of the protection device in front of it. This
leaf reads one protection-device specification and one telemetry chain
and decides whether the reported current is still a number where the
device actually goes into limiting.

## Domain quick reference

- The current that matters is not the class current of the output and
  not its nominal load. It is the *maximum* limitation current: the top
  of the band inside which the protection device may go into limiting,
  once initial tolerance, temperature, ageing, radiation and supply
  spread have all been taken at their worst sign together. Those
  contributors are summed arithmetically, not in quadrature, because the
  requirement is a bound on a single unit, not a population statistic.
- A telemetry chain reports current only indirectly. The shunt turns
  current into a voltage, the amplifier scales it, and the converter
  span bounds it. Referring the span back gives the full-scale current
  as span divided by the product of shunt resistance and gain, which is
  why a design that doubles the gain for resolution halves the current
  the chain can still report.
- The zero-current output voltage is part of the span, not free
  headroom. A chain biased to report a signed current, or biased off
  ground to keep the amplifier out of its own rail, has that much less
  span left above zero for the positive range.
- Either the amplifier or the converter clips first, and knowing which
  one changes the fix. A chain the amplifier bounds gains nothing from a
  larger converter reference, and a chain the converter bounds gains
  nothing from a higher amplifier rail.
- Range and resolution trade against each other on a fixed code count. A
  chain stretched to reach the limitation current with an eight-bit
  converter can satisfy this clause and still be useless for the
  operating-point measurement it also has to serve, so the current one
  code represents is reported alongside the coverage verdict.

## Workflow

1. Validate the protection-device specification: a positive class
   current, a limiting ratio at or above one, and declared spread
   contributors that are recognised, non-negative and individually below
   unity. A ratio under one means the device limits inside its own
   rating and is an input error, not a conservative case.
2. Sum the declared spreads arithmetically and form the limitation band
   around the nominal limiting current; the upper edge is the current
   the telemetry range has to reach.
3. Validate the telemetry chain and compute its full-scale current from
   the converter span less the zero-current output voltage, divided by
   the shunt-and-gain product. Apply an amplifier clip level when one is
   declared and sits below the span.
4. Record which element set the ceiling, so a shortfall is reported
   against the part that actually caused it.
5. Compare full scale with the required current, absorbing
   floating-point representation error at an exact match with a named
   tolerance rather than by trimming the required current.
6. Report the headroom as a fraction of the required current, and, when
   a converter bit count is declared, the current one code represents
   against any required resolution.
7. Return the verdict with every finding named: a saturating range, the
   clipping element behind it, and a range bought at the cost of
   resolution.

## Pitfalls

- Sizing the range on the class current. The class current is the rating
  of the output, not the current at which its protection device stops
  conducting more; the range has to reach the upper edge of the
  limitation band, which sits well above it.
- Taking the nominal limitation current as the limit. The nominal figure
  is the centre of a band; a unit at the top of tolerance at hot end of
  life limits higher, and that unit is the one the range has to cover.
- Combining the spread contributors in quadrature. A root-sum-square
  combination is a statement about a population; this requirement has to
  hold for the single unit in front of the telemetry, so the
  contributors add.
- Forgetting the zero-current output voltage. A chain biased half a volt
  off ground has half a volt less span for positive current, and a range
  calculated from the raw converter span overstates what the chain
  reports by exactly that amount.
- Fixing a shortfall at the wrong end. Raising the converter reference
  on a chain the amplifier already clips changes nothing; the element
  that set the ceiling is what has to move.
- Declaring the clause met on range alone. A range reached by coarsening
  the code step satisfies this clause and breaks the measurement the
  same telemetry is relied on for elsewhere, so resolution is reported
  with the verdict.

## Behavior contract (gate 3)

The protection-device validation, spread summation, limitation-band
construction, chain referral, clipping-element identification, coverage
comparison, headroom and resolution reporting are exercised by the
gate 3 contract test:
scripts/test_e2020_current_telemetry_full_scale.py against
scripts/e2020_current_telemetry_full_scale_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_current_telemetry_full_scale.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
