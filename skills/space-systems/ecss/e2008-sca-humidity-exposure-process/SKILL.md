---
name: e2008-sca-humidity-exposure-process
description: "Use when accepting or auditing a subgroup humidity exposure. Verify that every sample of a solar cell assembly subgroup was actually held inside the chamber, at ambient pressure, for the humidity exposure period of ECSS-E-ST-20-08C clause 6.4.3.8.2: reduce the chamber pressure record to the intervals that held the ambient band, credit a sample only where its own time in the chamber overlaps one of them, refuse to credit time the record never observed, compare each sample with the required period, and close the subgroup only when it is large enough and every sample reached it. Trigger: ecss, e-st-20-08c, clause-6-4-3-8-2, sca-subgroup-humidity-exposure, ambient-pressure-chamber-hold, subgroup-sample-exposure-credit, humidity-exposure-period-accounting, chamber-pressure-interruption-charging."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-sca-humidity-exposure-process, sca-subgroup-humidity-exposure, ambient-pressure-chamber-hold, subgroup-sample-exposure-credit, humidity-exposure-period-accounting, chamber-pressure-interruption-charging]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Subgroup Humidity Exposure Process (space-systems/ecss/e2008-sca-humidity-exposure-process)

Use when the task is the chamber step of the solar cell assembly subgroup
humidity exposure of ECSS-E-ST-20-08C clause 6.4.3.8.2 — deciding, sample by
sample, whether the members of a subgroup were really held inside the chamber,
at ambient pressure, for the exposure period the test specification defines.

## Domain quick reference

- The exposure period belongs to each sample, not to the chamber run. Samples
  that go in late, come out early or are pulled for an interim inspection each
  carry their own window, so a run that satisfies the period as a whole can
  still leave an individual sample short.
- Ambient pressure is a stated condition of this exposure, not a chamber
  detail. A chamber that partly evacuates turns damp heat into a different
  environment, so the time it spent out of band earns no exposure credit for
  any sample that was inside it at the time.
- Credit is interval-based because the chamber is sampled. Between two logged
  entries the pressure is not observed, so an interval counts only when both of
  its endpoints hold the band; one out-of-band entry therefore voids the
  interval before it and the interval after it, which is the conservative
  reading a slow logging rate has to pay for.
- Time in the chamber outside the logged record is not exposure. A sample left
  in after the logger stopped may well have been at ambient pressure, but
  nothing observed it, and an unobserved hold is a gap in the record rather
  than credit.
- Two hold shapes differ for the hardware. A single long ambient hold and the
  same number of hours split by pressure departures are not the same exposure,
  so the number of separate holds and the longest one are reported alongside
  the total.
- The band edges are part of the band. A chamber sitting exactly on a tolerance
  limit is holding the condition, so edge membership is inclusive and the
  comparison absorbs representation error rather than moving the limit.
- A subgroup is a sampling device. Too few samples makes the result unable to
  speak for the lot whatever the chamber did, which is a different outcome from
  a subgroup that was simply under-exposed.

## Workflow

1. Validate the ambient pressure band, refusing an inverted or non-positive
   one. The laboratory band is the default; a chamber at altitude declares its
   own explicitly rather than silently widening the check.
2. Validate the chamber pressure record: at least two entries, strictly
   increasing time stamps, each carrying a positive pressure. A repeated time
   stamp is an input error, not a zero-length interval.
3. Validate the subgroup roster: a non-empty identifier per sample, unique
   across the subgroup, and an unload time strictly after the load time.
4. Reduce the record to the intervals that held the ambient band, merging
   intervals that touch so one continuous hold reads as one.
5. Credit each sample with the overlap between its own in-chamber window and
   those intervals, and report separately the hours it spent in the chamber
   uncredited and the hours it spent outside the logged record.
6. Compare every credited exposure with the required period, absorbing
   floating-point representation error at the boundary with a named tolerance,
   and record the shortfall of each sample that fell short.
7. Close on one subgroup verdict — undersized, short, or exposed — with the
   per-sample accounting and every finding attached to it.

## Pitfalls

- Reading the exposure off the first and last entry of the chamber record.
  That is the record span; it credits the pressure departures as exposure and
  overstates what the samples saw.
- Crediting the whole subgroup from one sample. Load and unload records exist
  precisely because the samples do not share a window, and the shortest window
  governs the subgroup.
- Crediting an interval on one good endpoint. The chamber state between entries
  is not observed, so a half-credited interval is an assumption.
- Treating unlogged chamber time as exposure. The sample may have been held
  perfectly; nothing recorded it, and a sentencing decision cannot rest on
  that.
- Reporting only the total ambient hold. Ten short holds and one long one sum
  the same and mean different things to a bondline, so the count and the
  longest hold are carried with the total.
- Calling an exactly-on-the-limit chamber pressure an excursion, or widening
  the band until the run passes. Band edges are inclusive and the tolerance
  belongs inside the comparison, not in the limit.
- Passing an undersized subgroup because every sample it did carry was fully
  exposed. The sampling floor is a separate condition and it has its own
  verdict.

## Behavior contract (gate 3)

The pressure band and chamber record validation, the subgroup roster checks,
the ambient hold reduction, the per-sample exposure credit, the unlogged-time
accounting and the subgroup verdict are exercised by the gate 3 contract test:
scripts/test_e2008_sca_humidity_exposure_process.py against
scripts/e2008_sca_humidity_exposure_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_humidity_exposure_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
