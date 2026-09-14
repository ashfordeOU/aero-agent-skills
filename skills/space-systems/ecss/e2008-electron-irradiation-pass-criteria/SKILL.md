---
name: e2008-electron-irradiation-pass-criteria
description: "Assess whether a blocking diode still sits inside its source control drawing limits once electron exposure and the anneal that follows are both behind it, under ECSS-E-ST-20-08C clause 12.6.11.2.3: refuse a limit set carrying no drawing reference, sentence only on the post-anneal reading and leave a device unsentenced while that reading is missing, judge forward drop and reverse leakage against their ceilings and blocking voltage against its floor with a tie admissible, name every breach rather than the first, record how much of the exposure shift the anneal gave back, and take the rejected share against the declared allowance. Use when post-exposure blocking diode data has to become a drawing verdict. Trigger: ecss, e-st-20-08c-clause-12-6-11-2-3, blocking-diode-post-anneal-sentencing, blocking-diode-post-exposure-drawing-limits, blocking-diode-forward-drop-ceiling, blocking-diode-reverse-leakage-ceiling, blocking-diode-voltage-floor-margin, blocking-diode-anneal-recovery-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-electron-irradiation-pass-criteria, blocking-diode-post-anneal-sentencing, blocking-diode-post-exposure-drawing-limits, blocking-diode-forward-drop-ceiling, blocking-diode-reverse-leakage-ceiling, blocking-diode-voltage-floor-margin, blocking-diode-anneal-recovery-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Electron Irradiation Pass Criteria (space-systems/ecss/e2008-electron-irradiation-pass-criteria)

Use when the task is the clause 12.6.11.2.3 decision of ECSS-E-ST-20-08C:
blocking diodes have been exposed to electrons and then annealed, and each
one is admissible only if the characteristics measured afterwards still sit
inside the limits its own source control drawing fixes.

## Domain quick reference

- The reading that sentences the device is the one taken after the anneal.
  The post-irradiation reading is the worst the part will ever look, and a
  diode refused on it is being refused for a shift the anneal was always
  expected to take back. A device whose record carries no post-anneal
  reading is left unsentenced rather than passed or failed on the earlier
  numbers.
- The limits come from the drawing that governs this diode type. Not the
  vendor datasheet typical, not the value the last programme flew, not a
  house limit carried forward. A verdict quoted with no drawing reference
  behind it is not a verdict against this clause, so an unreferenced limit
  set closes the assessment instead of passing it.
- The three characteristics point in two directions. Forward drop and
  reverse leakage are ceilings, because the exposure pushes both upward and
  the array feels the loss; blocking voltage is a floor, because that is
  what the diode is in the string to hold. A verdict that treats all three
  as one sense will pass a part that has lost its blocking capability.
- Landing exactly on a limit is admissible in all three cases, and the
  comparison tolerance exists to absorb representation error rather than to
  widen the drawing.
- The limit set is checked for sense before use. A forward drop ceiling
  above the blocking voltage floor describes no diode, and a limit set with
  that shape is a drawing transcription defect rather than a hard lot.
- How much of the exposure shift the anneal gave back belongs beside the
  verdict. Two diodes can both sit inside the drawing while one recovered
  nine tenths of its shift and the other a tenth, and the second is the one
  that will keep drifting through the mission.
- How many refused devices a delivery may carry is a separate, declared
  question. It is a lot allowance, not arithmetic on the devices, and it
  does not change any individual verdict.

## Workflow

1. Validate the sentencing policy first: the largest refused share the lot
   may carry and the band inside which an accepted diode counts as
   marginal. A share above one, or a marginal band above one, is refused
   rather than used.
2. Read the drawing limits and check them for sense: forward drop ceiling,
   reverse leakage ceiling and blocking voltage floor all positive, and the
   forward ceiling not above the blocking floor. An absent limit set, or
   one whose drawing reference is blank, closes the assessment on
   requirement not established.
3. Validate every exposed device record: a non-blank identifier, no
   duplicate identifier, and every reading it does carry complete and
   positive. An empty exposed population is refused rather than reported as
   a clean lot.
4. Sentence each device on its post-anneal reading against all three
   limits, admitting a tie, and record the margin on each together with the
   smallest of the three as the limiting margin. Name every limit a device
   breached, not only the first one found.
5. Close on post-anneal reading not evidenced if any device reached this
   point without one. A lot part-sentenced on pre-anneal numbers is not a
   lot verdict.
6. Where a pre-exposure and a post-irradiation reading both exist, take the
   share of the forward drop shift the anneal gave back and report it with
   the device. A device that kept drifting through the soak shows a
   negative share, which is a finding rather than an error.
7. Take the refused share of the sentenced lot against the declared
   allowance, a share landing exactly on the allowance being admissible,
   and raise a marginal advisory for every accepted device inside the
   policy band. Advisories are reported with the verdict and do not move
   it.
8. Close on one verdict: source control drawing requirement not
   established, post-anneal reading not evidenced, lot reject fraction
   exceeded, or lot meets drawing limits.

## Pitfalls

- Sentencing on the post-irradiation reading. That measurement exists to
  size the shift, not to judge the part, and a lot scrapped on it is being
  scrapped for damage the anneal was there to remove.
- Treating blocking voltage as a ceiling because the other two are. The
  sense inverts, and a diode that has lost half its blocking voltage passes
  a ceiling test comfortably.
- Comparing against a remembered limit. The drawing is the only source of
  the required value, and a criterion applied from memory is a criterion
  nobody can audit.
- Judging readings taken at whatever temperature the bench happened to sit
  at. The drawing limits are stated at a reference junction temperature, so
  uncorrected readings are being compared against a value they do not share
  a condition with.
- Reporting a pass with no margin, no weakest device and no recovery share.
  The verdict alone hides the difference between a lot that comfortably
  cleared the drawing after its anneal and one that grazed it, and the next
  build has nothing to compare against.

## Behavior contract (gate 3)

The policy validation, drawing limit validation, the per-device sentence on
the post-anneal reading against both ceilings and the floor with an
admissible tie, the unsentenced-device stop, the anneal recovery share, the
lot reject fraction against its allowance, the weakest device, the marginal
advisories and the closing verdict are exercised by the gate 3 contract
test: scripts/test_e2008_electron_irradiation_pass_criteria.py against
scripts/e2008_electron_irradiation_pass_criteria_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_electron_irradiation_pass_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
