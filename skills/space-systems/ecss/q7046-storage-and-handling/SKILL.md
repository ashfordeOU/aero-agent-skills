---
name: q7046-storage-and-handling
description: "Evaluate whether a stored threaded fastener lot may still be issued, and what its protection is actually worth. Use when parts have been in stores for a while and someone must decide between releasing, re-inspecting, re-preserving and quarantining them: set the shelf life from the corrosion protection and the store class, restart the clock from a package breach rather than pausing it, clamp a month-end expiry onto a real calendar day, check the store against its own temperature and humidity band, and call out a mixed bin, a bulk-tipped container, a galvanic pairing or an issue order that is not oldest-first. Trigger: ecss, q-st-70-46-fasteners, fastener-shelf-life-expiry, fastener-corrosion-protection-class, fastener-store-environment-band, fastener-lot-segregation-and-issue."
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
  tags: [ecss, q-st-70-46-fasteners, q7046-storage-and-handling, fastener-shelf-life-expiry, fastener-corrosion-protection-class, fastener-store-environment-band, fastener-lot-segregation-and-issue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Storage and Handling (space-systems/ecss/q7046-storage-and-handling)

Use when the task is the storage and handling clause of
ECSS-Q-ST-70-46: how long a protected fastener lot stays usable in the
store it is actually kept in, and whether the way it is being kept and
issued has already cost it that protection.

## Domain quick reference

- The clock is set by two things together: the corrosion protection the
  parts carry and the class of store they sit in. A sealed, desiccated
  lot in a controlled store outlasts a bare passivated lot in a shed by
  an order of magnitude, and neither number can be quoted alone.
- A package breach restarts the clock; it does not pause it. From the
  moment the seal opens the parts are in the room's environment, and the
  life left is the uncontrolled life measured from the breach.
- Expiry arithmetic is calendar arithmetic. A lot made on the 31st has
  no 31st to expire on in half the months of the year, so the date is
  clamped to the last valid day rather than rolling into the next month.
- An environmental excursion is not an expiry. It is a reason to
  re-preserve and restart, because the protection may have been consumed
  without the life having run out.
- A container holding more than one lot has no lot identity. The
  traceability to the heat is carried by the container label, and two
  lots under one label destroy it for both.
- Threaded parts are not tipped in bulk. Threads damage each other's
  flanks, and the flanks are not where a bin check looks.
- Issue is oldest-first. Any other order spends the life of the newest
  lot while the oldest expires in place, which converts stock into
  scrap without anything visibly going wrong.
- Re-inspection is scheduled from the life, not from the calendar year.
  A short-life lot is looked at more often than a long-life one sitting
  in the same rack.

## Workflow

1. Take the protection and the store class and read the shelf life in
   whole months, then derive the re-inspection interval from it.
2. Set the start of the clock: manufacture, or the package breach if
   there was one, refusing a breach recorded before manufacture.
3. Add the life in whole months and clamp the result onto a real
   calendar day, then take the remaining life as whole days, which goes
   negative once the lot is past.
4. Check the store's temperature and humidity against the band for its
   class, with a value on the edge counted as inside.
5. Collect the handling findings: how many lots share the container,
   whether the parts were tipped in bulk, whether dissimilar metals are
   in contact, and what order the bin is issued in.
6. Dispose: past its life is quarantine; an environmental excursion is
   re-preserve and restart; any other finding is re-inspect before
   issue; nothing outstanding releases the lot.

## Pitfalls

- Quoting one shelf life for a part number. The same part in a shed and
  in a controlled store are two different remaining lives, and the store
  is the half people leave out of the record.
- Treating a resealed package as if the clock had paused. The parts saw
  the room, and resealing traps whatever humidity was in it at the time.
- Rolling a month-end expiry into the first of the next month. It looks
  harmless and it silently extends the life of every lot made on a 29th,
  30th or 31st.
- Reading an excursion as an expiry, or an expiry as an excursion. One
  is answered by re-preservation and one is not answerable at all.
- Topping up a bin from a second lot. It is the single most common way
  fastener traceability is lost, and it is undetectable afterwards
  because both lots look identical.
- Issuing from the front of the rack. Newest-first is the default
  behaviour of anyone in a hurry, and it expires the back of the rack in
  place at full cost.
- Tipping a bag of bolts into a tray to count them. The count is right
  and the thread flanks are not, and the damage does not surface until
  the prevailing torque is measured at installation.

## Behavior contract (gate 3)

The shelf life by protection and store class, the re-inspection
interval, the breach-restarted clock, the month-end expiry clamp, the
remaining life in days, the environmental band check, the handling
findings and the storage disposition are exercised by the gate 3
contract test:
scripts/test_q7046_storage_and_handling.py against
scripts/q7046_storage_and_handling_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_storage_and_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
