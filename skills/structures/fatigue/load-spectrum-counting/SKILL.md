---
name: load-spectrum-counting
description: "Use when you must build a fatigue load spectrum from a mission load history: count cycles with the rainflow method, derive level-crossing and exceedance spectra, aggregate per-phase loads into a mission spectrum, apply spectrum truncation, and evaluate cumulative damage with Miner's rule on a Basquin S-N curve. Produces the rainflow cycle counts, the exceedance spectrum table, the truncated spectrum, and the cumulative damage fraction that gate the fatigue life assessment. Trigger: rainflow, cycle counting, exceedance spectrum, level crossing, load spectrum, mission profile, spectrum truncation, fatigue life."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [rainflow, cycle-counting, exceedance-spectrum, level-crossing, load-spectrum, mission-profile, spectrum-truncation, fatigue]
  version: 0.1.0
  author: AeroSkills
---

# Fatigue Load Spectrum Counting (structures/fatigue/load-spectrum-counting)

Use when the task is building or reducing a fatigue load spectrum:
rainflow cycle counting, exceedance and level-crossing spectra,
mission spectrum assembly, truncation, and spectrum damage.

## Domain quick reference

- Rainflow counting (ASTM E1049-85 section 5.4.4 practice) extracts
  cycles from the turning points of a load history: an excursion is a
  full cycle when the following excursion in the opposite direction is
  at least as large; the residual stream forms half cycles.
- The exceedance spectrum counts, per load level, how many peaks reach
  or pass the level; the level-crossing spectrum counts crossings of a
  level in the history.
- A mission spectrum aggregates per-phase (level, cycles) blocks and
  sums repeated levels across phases.
- Spectrum truncation removes cycles below a cutoff level; they
  contribute little damage and are dropped before damage summation.
- Miner's rule sums n/N over the spectrum blocks. This leaf derives N
  from a Basquin S-N curve N = C * S_a**(-b); the miner-damage leaf
  sums (n, N) blocks directly.
- Fatigue load spectra sit in the FAR-25.571 damage tolerance context
  for transport aeroplanes.

## Workflow

1. Reduce the mission history to cycles with rainflow_cycles.
2. Merge the counts with rainflow_spectrum.
3. Count level activity with exceedance_counts and upcrossing_count.
4. Aggregate mission phases with mission_spectrum.
5. Drop small cycles with truncate_spectrum.
6. Sum damage with spectrum_damage (Basquin lives, Miner fractions).
7. Feed the damage fraction into the miner-damage leaf's life check.

## Pitfalls

- Counting cycles by naive peak counting instead of rainflow.
- Summing exceedance over raw samples instead of turning points.
- Truncating away the cutoff level itself (keep levels >= cutoff).
- Mixing alternating stress (half the range) with the full load range
  in the Basquin curve.
- Double counting half cycles as full cycles in the spectrum.

## Behavior contract (gate 3)

The counting, spectrum, truncation, and damage logic is exercised by
the gate 3 contract test: scripts/test_load_spectrum.py against
scripts/load_spectrum_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_load_spectrum.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download. The rainflow and
  Miner rules are common fatigue methodology, summary-only per
  standards-map.yaml. ASTM E1049 names the counting practice; the
  method text here is summary, not standard text.
- compliance: STANDARDS-REF, gated: false.
