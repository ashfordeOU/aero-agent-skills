---
name: e20-battery-user-manual-contents
description: "Use when verify that a battery-user-manual carries the content required by the ECSS-E-ST-20C Annex D data-requirement: check each mandated chapter (cell-and-battery identification, operating-envelope, charge-and-discharge-control, ground-handling-and-storage, safety-and-hazard-precautions, life-and-degradation-data, transport-and-shipping), reject an uncategorized chapter, prove the declared operating-envelope is self-consistent and that the charge-termination-voltage sits inside it, check the storage state-of-charge and storage-temperature against the chemistry band, and confirm the cycle-life and calendar-life entries cover the mission duty-profile. Trigger: ecss, e-st-20-electrical-scope, battery-user-manual, charge-termination-voltage, state-of-charge-storage, depth-of-discharge-limit, cell-balancing-procedure, thermal-runaway-precaution, annex-d-data-requirement."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-user-manual-contents, battery-user-manual, charge-termination-voltage, state-of-charge-storage, depth-of-discharge-limit, cell-balancing-procedure, annex-d-data-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Battery User Manual Contents (space-systems/ecss/e20-battery-user-manual-contents)

Use when the task is the content check of the battery-user-manual of
ECSS-E-ST-20C Annex D -- the document the battery supplier hands to
every party that will charge, discharge, handle, store, transport or
operate the assembly, covering its operating-envelope, its
charge-and-discharge-control, its ground-handling-and-storage regime,
its safety precautions and its life-and-degradation data.

## Domain quick reference

- Annex D is a data-requirement: it fixes the chapters the manual must
  contain, so the check is coverage plus internal consistency, not a
  redesign of the assembly. The mandated chapters are the
  cell-and-battery identification (cell type, chemistry, series and
  parallel arrangement, serial numbers), the operating-envelope, the
  charge-and-discharge-control, the ground-handling-and-storage
  regime, the safety-and-hazard-precautions, the
  life-and-degradation-data and the transport-and-shipping
  constraints. A chapter outside the recognized set is not an extra
  credit -- it is an uncategorized entry the check refuses, because an
  unrecognized heading usually means a mandated chapter was renamed
  rather than written.
- The operating-envelope is stated per cell and scaled to the assembly
  by the series count. It is self-consistent only when the minimum
  cell voltage sits below the maximum, the temperature floor sits
  below the ceiling, and the charge-termination-voltage lies inside
  the voltage envelope -- inclusive at both ends, since terminating
  exactly at the declared maximum is the nominal design point, not a
  violation.
- Each chemistry carries its own usable cell-voltage window and its
  own storage band. A lithium-ion assembly is stored part-charged and
  cool; a nickel-hydrogen or nickel-cadmium assembly follows a
  different regime. Declaring a storage state-of-charge outside the
  chemistry's band is a real finding, and a state-of-charge outside
  0-100 percent is not a finding at all but an invalid input.
- Life data is only meaningful against the mission duty-profile. The
  cycle count the mission demands follows from the orbit rate, the
  mission duration and the fraction of orbits that actually produce a
  discharge cycle; the manual's declared cycle-life must cover that
  count at the declared depth-of-discharge-limit, and its declared
  calendar-life must cover the mission duration including the
  pre-launch storage period.
- The safety chapter is graded by topic coverage, not by length:
  thermal-runaway, over-charge-protection, over-discharge-protection,
  external-short-circuit, cell-venting-and-gas-release and the
  personal-protective-equipment required for handling each have to
  appear.

## Workflow

1. Normalize and check the chapter list. Report the mandated chapters
   that are absent and the duplicated headings; refuse an unrecognized
   chapter outright.
2. Resolve the chemistry to its cell-voltage window and its storage
   band. An unrecognized chemistry stops the assessment -- without it
   no envelope or storage check has a reference.
3. Validate the operating-envelope: minimum below maximum on both
   voltage and temperature, charge-termination-voltage inside the
   voltage envelope inclusive of its ends, and the declared cell
   voltages inside the chemistry window. Scale to the assembly with
   the series count.
4. Check the ground-handling-and-storage regime: the declared storage
   state-of-charge and storage-temperature against the chemistry band,
   and the declared re-charge interval against the maximum dormancy
   the chemistry tolerates.
5. Check the charge-and-discharge-control chapter: a recognized charge
   mode, a charge rate inside the declared maximum, a stated
   termination criterion, and a cell-balancing-procedure where the
   series count makes one necessary.
6. Compute the cycle count the mission duty-profile demands and
   compare the declared cycle-life at the declared
   depth-of-discharge-limit; compare the declared calendar-life
   against the mission duration plus storage.
7. Check the safety topic coverage, then aggregate. The manual is
   compliant only when every list is empty.

## Pitfalls

- Reading chapter presence as content. A heading with no
  operating-envelope numbers under it passes a coverage check and
  fails the consistency check; run both, and never let coverage alone
  close the manual.
- Treating a charge-termination-voltage equal to the envelope maximum
  as an exceedance. That equality is the design point; the comparison
  absorbs floating-point representation error rather than tightening
  the declared envelope.
- Comparing a declared cycle-life against the orbit count instead of
  the cycle count. Not every orbit discharges the assembly; the
  eclipse fraction of the duty-profile is what converts orbits into
  cycles, and skipping it overstates the demand on a
  continuously-illuminated mission and understates nothing.
- Ignoring the depth-of-discharge-limit the cycle-life was declared
  at. A cycle-life valid at a shallow discharge does not transfer to a
  deeper one; the pair travels together or the number is unusable.
- Accepting a storage state-of-charge of 0 or 100 percent as merely a
  finding for a lithium-ion assembly. Full or flat storage is a
  handling hazard, and a value outside 0-100 percent is an invalid
  input the check must refuse before it grades anything.
- Grading the safety chapter by page count. Coverage is by topic --
  a long chapter that never mentions cell-venting-and-gas-release is
  still incomplete.

## Behavior contract (gate 3)

The chapter-coverage check, chemistry resolution, operating-envelope
consistency, storage-regime check, charge-control check,
duty-profile cycle demand and life comparison, safety topic coverage
and the manual-level verdict are exercised by the gate 3 contract
test: scripts/test_e20_battery_user_manual_contents.py against
scripts/e20_battery_user_manual_contents_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_battery_user_manual_contents.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
