---
name: e1011-physical-perf
description: "Use when evaluate crew physical performance and fatigue limits under ECSS-E-ST-10-11C §4.5.3: categorize each crew task by metabolic rate band (rest, light, moderate, heavy, or very heavy), check the continuous-work duration against the per-category allowable limit, compute the minimum required recovery period, flag any work bout that exceeds the sustained-performance threshold, and validate a full work-rest schedule against the daily workload accumulation limit for each category. Applicable to IVA and EVA crew scheduling, ergonomic compliance review, and mission-phase workload analysis. Trigger: ecss, e-st-10-system-scope, physical-performance, crew-workload, fatigue, metabolic-rate, work-rest-schedule, human-factors, ergonomics."
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
  tags: [ecss, e-st-10-system-scope, physical-performance, crew-workload, fatigue, metabolic-rate, work-rest-schedule, human-factors]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Crew Physical Performance and Fatigue (space-systems/ecss/e1011-physical-perf)

Use when the task is to evaluate crew physical workload against the
physical performance and fatigue reference data of ECSS-E-ST-10-11C
§4.5.3 -- categorizing work tasks by metabolic rate, verifying
continuous-work duration limits, computing required recovery periods,
and checking daily accumulated workload against per-category caps.

## Domain quick reference

- §4.5.3 maps metabolic rate (W) to five workload bands: REST
  (below 65 W), LIGHT (65–174 W), MODERATE (175–294 W),
  HEAVY (295–414 W), and VERY HEAVY (415 W and above). Thresholds
  derive from ISO 8996 metabolic rate categories adapted for
  space-environment crew assessments. Every crew task is placed into
  exactly one band before any limit is applied.
- Continuous duration limits cap the uninterrupted work time per band:
  LIGHT 480 min, MODERATE 120 min, HEAVY 45 min, VERY HEAVY 20 min.
  A REST segment carries no practical continuous limit within a 24-hour
  period. Exceeding the continuous limit for a band is a direct
  physical-performance violation regardless of recovery state.
- Recovery is proportional to work intensity. The minimum rest period
  following a work bout equals a multiplier times the bout duration:
  LIGHT 0.25×, MODERATE 0.5×, HEAVY 1.0×, VERY HEAVY 2.0×.
  Starting a new work bout before that rest period has elapsed is an
  insufficient-recovery violation.
- Daily accumulated workload limits cap the total time in each band
  across a full crew-day: LIGHT 480 min, MODERATE 240 min,
  HEAVY 120 min, VERY HEAVY 60 min. These limits are independent of
  the continuous-duration check; a schedule can pass all continuous
  checks and still fail on daily accumulation.

## Workflow

1. Assign a metabolic rate (W) to every crew task in the schedule.
   Reject any task with a negative or missing rate before the
   assessment proceeds.
2. Categorize each task into its workload band using the metabolic
   rate thresholds. A task is placed in exactly one band; borderline
   values use the lower-rate band convention (a rate equal to a
   threshold is placed in the higher band, consistent with the
   half-open interval [lower, upper)).
3. For each work bout, compare its duration against the continuous
   duration limit for its band. Record a continuous-limit violation
   if the bout duration exceeds the limit.
4. For each pair of consecutive work bouts, sum the rest time
   between them and compare it to the required recovery for the
   preceding bout (recovery_ratio × work_duration). Record an
   insufficient-recovery violation if the accumulated rest falls short.
5. Sum the work durations per band across the full schedule day.
   Compare each band total against its daily accumulation limit.
   Record a daily-limit violation for every band that is exceeded.
6. Aggregate all violations. A schedule is compliant only when the
   continuous-limit, insufficient-recovery, and daily-limit violation
   lists are all empty.

## Pitfalls

- Applying the daily limit check without first running the continuous
  and recovery checks -- a schedule that passes daily totals can still
  have single bouts that are too long or transitions with too little
  rest; all three checks are mandatory.
- Treating the recovery ratio as a fixed number of minutes rather than
  a multiple of the preceding work duration -- a 30 min HEAVY bout
  requires 30 min of rest, but a 45 min HEAVY bout requires 45 min of
  rest; the required rest scales with the bout length.
- Conflating the continuous limit with the daily limit -- a MODERATE
  task can legally run for 120 min in a single bout but the crew-day
  cap is 240 min; two full 120 min bouts with sufficient recovery
  between them exhaust the daily allowance and a third bout (even a
  short one) triggers a daily-limit violation.
- Dropping REST segments from the schedule before running the recovery
  check -- REST time is what satisfies the recovery requirement; if
  REST segments are filtered out early, the preceding-bout recovery
  time will appear as zero and every transition will be flagged.

## Behavior contract (gate 3)

The categorization, continuous-limit, recovery, and daily-accumulation
logic is exercised by the gate 3 contract test:
scripts/test_e1011_physical_perf.py against
scripts/e1011_physical_perf_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_physical_perf.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
