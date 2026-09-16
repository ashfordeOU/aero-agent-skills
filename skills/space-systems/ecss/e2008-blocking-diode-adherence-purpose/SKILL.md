---
name: e2008-blocking-diode-adherence-purpose
description: "Use when a planar blocking diode adherence campaign is scoped or defended. Determine why contact attachment on a planar blocking diode is verified only where contacts exist, under ECSS-E-ST-20-08C clause 12.6.4.2.1: settle the build state first, holding a mesa or integrated part outside the clause and a bare metallisation outside the check, take the share of array power one opened series attachment costs, weight the service exposures the joint has to outlast into one index, relieve the consequence where a parallel diode carries the string, map each exposure onto the parameter recording it, and close on one applicability verdict. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-2-1, planar-blocking-diode-contact-presence, planar-blocking-diode-attachment-criticality, blocking-diode-string-loss-fraction, blocking-diode-attachment-evidence-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c-clause-12-6-4-2-1, e2008-blocking-diode-adherence-purpose, planar-blocking-diode-contact-presence, planar-blocking-diode-attachment-criticality, blocking-diode-string-loss-fraction, blocking-diode-attachment-evidence-coverage, planar-blocking-diode-adherence-applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Adherence Purpose (space-systems/ecss/e2008-blocking-diode-adherence-purpose)

Use when the task is to state and defend why the contacts of a planar
blocking diode are pulled under ECSS-E-ST-20-08C clause 12.6.4.2.1 --
whether this device is even in the clause, whether it carries an
attachment at all, what an opened attachment costs the array, and
whether anything is being recorded against the exposures the argument
rests on.

## Domain quick reference

- The clause carries a condition before it carries a requirement. A
  planar blocking diode arrives either with leads already attached to
  the metallisation or with bare metallisation and nothing on it, and
  only the first has an attachment a pull can describe.
- A mesa or integrated build is not a failed planar part. It is a
  different construction, governed elsewhere, and recording it as a
  planar failure puts a finding against the wrong clause.
- Pulling a device with nothing attached does not return a conservative
  answer. It returns a number about the grip of the tooling, entered in
  the record as though it were about the part, and nothing afterwards
  can separate the two.
- The consequence half of the argument is specific to this device. A
  blocking diode sits in series with a string, so an attachment that
  opens takes the string off the array, and the share of array power
  that represents is what the verification is buying.
- The exposure half is the downstream life: the series weld of the lead,
  the conduction heating the string current puts through the joint, the
  routing strain of harness integration, the broadband loading of
  launch, and a mission of thermal cycles shearing the attachment.
- Those weights sum to one, so the index is a share rather than a score,
  and the criticality is the product of the halves. A whole downstream
  life on a string worth nothing, and a whole string faced with almost
  nothing, both come out small -- correctly.
- A parallel diode carrying the string when this one opens relieves the
  consequence by a declared factor. It does not remove it: the array
  still runs a leg down until the next failure has somewhere to go.
- An exposure declared with nothing recorded against it is an argument,
  not evidence, so the coverage of the evidence parameters is checked in
  its own right rather than assumed from the list.

## Workflow

1. Validate the purpose policy first: criticality floor, evidence
   coverage floor and redundancy relief factor. A relief factor above
   one, which would make a redundant diode more critical, is refused
   rather than used.
2. Settle the build state before anything else. A non-planar
   construction closes out of clause scope; a planar device with nothing
   attached closes as not applicable, and no consequence figure is owed
   for either.
3. Group the declared service exposures, rejecting an unrecognised one
   rather than ignoring it, count a repeated one once, and map each onto
   the parameter recording it. With nothing declared, close there.
4. Derive the string loss share from the string and array power,
   refusing a string larger than the array it sits in, then take the
   criticality and apply the redundancy relief where a parallel diode is
   declared.
5. Take the evidence coverage across the declared exposures and name
   every exposure nothing is recorded against.
6. Report every finding, not the first, and close on one verdict: out of
   clause scope, not applicable, exposures not declared, criticality
   below threshold, evidence incomplete, or verification justified. A
   value landing exactly on a floor passes; the comparison tolerance
   absorbs representation error and the floor does not move.

## Pitfalls

- Pulling a device that has nothing attached. The tooling grips the
  metallisation, the number is about the grip, and the record cannot
  tell afterwards which of the two it measured.
- Failing a mesa part against this clause. Out of scope and
  non-compliant read the same in a summary table and mean opposite
  things to the supplier who has to answer them.
- Arguing the pull from the mission alone. Most of the demand on a
  blocking diode lead is spent before launch, in the weld schedule and
  the harness routing, and a cycling-only argument understates it.
- Treating array size as irrelevant. The same diode on a twelve-string
  array and on a two-hundred-string array carries the same joint and a
  completely different consequence, and only one of them earns a
  destructive campaign.
- Reading a parallel diode as removing the consequence. It buys one
  failure, not immunity, and writing the criticality to zero removes the
  evidence that would catch the second.
- Declaring an exposure and recording nothing against it. The campaign
  then produces a pass that says only that nobody looked, which reads in
  the record exactly like a pass that says the joint held.
- Comparing a derived index, share or criticality against its floor by
  bare arithmetic. All three come out of sums and divisions that land a
  few units in the last place either side of a limit on different hosts,
  so the comparison absorbs that error while the floor never moves.

## Behavior contract (gate 3)

The policy validation, the planar contact configuration categories, the
service exposure index and its evidence map, the string loss share, the
attachment criticality and its redundancy relief, the evidence coverage,
the finding inventory and the purpose verdict are exercised by the gate
3 contract test:
scripts/test_e2008_blocking_diode_adherence_purpose.py against
scripts/e2008_blocking_diode_adherence_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_adherence_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
