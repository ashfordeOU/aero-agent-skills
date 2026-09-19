---
name: q7046-fastener-specifications
description: "Validate the purchase description a threaded fastener is to be procured against, and derive the numbers a receiving inspection will check it by. Use when a parts list has to become something a supplier can quote and a buyer can accept: report the fields the description does not state, parse the metric thread designation and take the coarse pitch from the table only when none is stated, read tensile and yield strength out of the property class, compute the tensile stress area and proof load, and cross-check the class against the material family and the coating against the class. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-purchase-description, fastener-property-class-strength, metric-thread-stress-area, fastener-proof-load, fastener-coating-embrittlement-conflict."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-fastener-specifications, fastener-purchase-description, fastener-property-class-strength, metric-thread-stress-area, fastener-proof-load, fastener-coating-embrittlement-conflict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Specifications (space-systems/ecss/q7046-fastener-specifications)

Use when the task is the specifications clause of ECSS-Q-ST-70-46:
turning a fastener line on a parts list into a purchase description
that fixes the dimensions, the property class and the material, and
that carries the load figures acceptance will be judged against.

## Domain quick reference

- A fastener is bought against a standard and a designation, never
  against a description. The standard reference, the thread designation,
  the length, the property class, the material family, the coating, the
  head type and the locking feature are all buyable; "a small stainless
  cap screw" is not.
- The property class is not a lookup table, it is an encoding. A carbon
  or alloy steel class carries its nominal tensile strength in the first
  figure and ten times the ratio of yield to tensile in the second, so
  12.9 means 1200 MPa with a yield at nine tenths of it. Austenitic
  stainless classes are named the other way and are tabulated.
- The tensile stress area is taken on a diameter reduced by a fixed
  multiple of the pitch, not on the nominal diameter. Using the nominal
  diameter overstates an M6 by roughly a sixth, and every preload and
  margin downstream inherits it.
- Pitch is part of the size. A fine-pitch thread of the same nominal
  diameter has a larger stress area and a different mating part, so a
  designation with no pitch means the coarse pitch and nothing else.
- A diameter the coarse table does not carry has no implied pitch. The
  specification has to state one; assuming the nearest tabulated value
  silently buys a different thread.
- The class and the material have to be the same kind of thing. A
  stainless class on an alloy steel part, or a steel class on titanium,
  is a specification no supplier can satisfy and every supplier will
  interpret.
- The coating and the class interact. An electroplated finish puts
  hydrogen into a high-strength part, and above the risk threshold that
  is a conflict to resolve in the specification rather than a process
  note; cadmium carries its own restriction whatever the class.

## Workflow

1. Check the description against the required field set first and stop
   there if anything is missing; the numeric work on a half-specified
   part produces figures nobody should quote.
2. Parse the thread designation, taking the coarse pitch from the table
   when none is stated and refusing an untabulated diameter that states
   no pitch.
3. Read the tensile and yield strength out of the property class,
   refusing a class whose figures fall outside the encodings.
4. Compute the tensile stress area from diameter and pitch, then the
   proof load from the yield strength and the proof ratio, and report
   the tensile load alongside it.
5. Sanity-check the length against the diameter, then run the
   material-against-class and coating-against-class cross-checks.
6. Report the gaps, the parsed thread, the strengths, the loads and
   every conflict, and call the description buyable only when all three
   lists are empty.

## Pitfalls

- Computing the load on the nominal diameter. It is the single most
  common overstatement in a fastener calculation and it always errs
  towards the unsafe side.
- Leaving the pitch off an untabulated diameter. The part arrives with
  whichever pitch the supplier stocks, and it mates with nothing on the
  drawing.
- Treating the property class as a material. The class fixes the
  strength the part must reach; the material fixes what can reach it,
  and the specification owes both.
- Reading the second figure of a steel class as a yield strength in
  hundreds of MPa. It is a ratio; read that way, 10.9 becomes a
  900 MPa tensile part instead of a 1000 MPa one.
- Specifying an electroplated finish on a high-strength class and
  handling the embrittlement in a process note. The relief bake and its
  test belong in the purchase description, or the part arrives without
  them.
- Computing loads for a description that is still missing fields. The
  numbers look authoritative, get quoted downstream, and change when
  the missing fields are finally filled in.

## Behavior contract (gate 3)

The required-field check, the metric designation parser with its
coarse-pitch table and refusals, the property-class encoding for steel
and the tabulated stainless classes, the tensile stress area, the proof
and tensile loads, the length sanity check and the material and coating
cross-checks are exercised by the gate 3 contract test:
scripts/test_q7046_fastener_specifications.py against
scripts/q7046_fastener_specifications_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_fastener_specifications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
