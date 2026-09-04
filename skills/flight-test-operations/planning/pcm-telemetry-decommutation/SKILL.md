---
name: pcm-telemetry-decommutation
description: "Use when you must decommutate a serial PCM telemetry stream: acquire frame sync by locating the sync word in the captured word stream, walk the locked minor frames and count sync misses, and demultiplex the recovered telemetry channels into time series, with fixed channels read from their word slot every frame, supercommutated channels read from their multiple word slots per frame, and subcommutated channels keyed by the subframe id into the per-subframe value lists. Produce the locked frame count, the sync miss report, the subframe id trace, and the recovered per-channel time series that feed data reduction. Trigger: pcm telemetry decommutation, pcm frame sync, supercommutated demux, subcommutated demux, minor frame decode."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: planning
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [pcm-telemetry-decommutation, pcm-frame-sync, supercommutated-demux, subcommutated-demux, minor-frame-decode]
  version: 0.1.0
  author: AeroSkills
---

# PCM Telemetry Decommutation (flight-test-operations/planning/pcm-telemetry-decommutation)

Use when the task is decoding a serial PCM minor-frame telemetry
stream at the ground station decode side: finding the sync word in the
captured word stream, locking the minor frames, counting sync misses,
and splitting each locked frame back into the fixed,
supercommutated and subcommutated channel time series that feed data
reduction. This leaf implements the standard decommutation walk in
pure Python, stdlib only. It pairs with
flight-test-operations/planning/telemetry-data-acquisition (the design
leaf, which sizes the frame and assigns the channels and stops at the
transmitter) and with
flight-test-operations/planning/flight-test-data-reduction (the post
decomm processing leaf that calibrates, aligns and smooths these
recovered series).

## Domain quick reference

- Wire format: a minor frame on the wire is the sync word followed by
  the data words, then the idle words before the next sync word. The
  frame period in words is 1 + data_words_per_frame + idle_words, and
  frame_period_words(data_words_per_frame, idle_words) returns that
  period. Example: 8 data words and 1 idle word give a 10 word
  period.
- Frame sync acquisition: the sync word is a fixed bit pattern that
  repeats at every frame boundary. sync_search finds its first
  occurrence at or after a start index; acquire_lock reports
  first_sync_index and scan_length (words examined up to and including
  the sync word) for the first lock in the stream, or raises
  ValueError when no sync word exists in the scanned region.
- Locked-frame walk: with the frame lock at first_sync_index, the next
  sync word is expected one frame period later. At each expected sync
  position, a word equal to the sync word locks the frame and the
  following data_words_per_frame words are recorded; any other word is
  a sync miss, and the walk resyncs by scanning forward from the
  missed position, bounded to the next two frame periods.
- Fixed channel: one word slot sampled every frame, so it yields one
  value per locked frame.
- Supercommutation: a channel occupies multiple word slots per frame
  (a list of slot indices) and yields one sample per slot, so it
  yields len(slots) values per locked frame, in slot order.
- Subcommutation: a channel occupies one word slot that carries M
  sub-values, cycled across frames. A designated subframe id word,
  masked to its low bits, selects which sub-value each frame carries;
  the sample joins the per-subframe value list for that id.
- Subframe id: read from the frame data word at sid_word_index and
  masked with sid_mask, so the recovered trace is the id itself for
  every locked frame.
- All channel values are recovered as transmitted: no calibration,
  alignment or smoothing happens here (those belong to
  flight-test-data-reduction).

## Workflow

1. State the format: data_words_per_frame and idle_words, and confirm
   the period with frame_period_words(data_words_per_frame,
   idle_words).
2. Acquire the frame lock: acquire_lock(stream, sync_word,
   data_words_per_frame, idle_words, max_scan) returns
   first_sync_index and scan_length; a ValueError means the stream
   holds no sync word in the scanned region and cannot be decoded.
3. Walk the frames: decode_frames(stream, sync_word,
   data_words_per_frame, idle_words) returns frames_locked,
   sync_misses and frame_data, the per-frame data word lists of every
   locked frame. Corrupted sync words drop the affected frame and add
   one to sync_misses.
4. Demultiplex with demultiplex(frame_data, sid_word_index, sid_mask,
   supercommutated, subcommutated): pass the supercommutated map
   {channel: [word slots]} and the subcommutated map {channel:
   {"word_index": i, "subframes": M}}. Recover super[channel] (values
   in frame order then slot order), sub[channel][subframe_id] (values
   per subframe id) and subframe_ids.
5. For a one-call decode, run decommutation_summary(stream, sync_word,
   data_words_per_frame, idle_words, format) with the format dict
   {"sid_word_index", "sid_mask", "supercommutated", "subcommutated"};
   it returns frames_locked, sync_misses, super, sub and subframe_ids
   together.
6. Hand the recovered per-channel series to flight-test-data-reduction
   for its post-decomm processing (its correction, alignment and
   smoothing steps).
7. Confirm the deterministic checks with the contract test
   scripts/test_pcm_telemetry_decommutation.py.

## Worked example

16-bit words, sync word 0xEB90, 8 data words per frame, 1 idle word,
so the frame period is 10 words. Frame k (k = 0..39) carries: word0 =
k & 3 (subframe id), word1 = 1000 + k (channel A, fixed), word2 =
2000 + (k & 3) * 100 + (k // 4) (channel S, subcommutated, 4
subframes), word3 = 3000 + k (channel A2, supercommutated slot 1),
word4 = 4000 + k, word5 = 5000 + k (channel A2, supercommutated slot
2), word6 = 6000 + k, word7 = 7000 + k. Idle word 0x0000. The wire
stream is the 40 frames concatenated (400 words).

Real module outputs on this fixture:

- frame_period_words(8, 1) = 10.
- acquire_lock: first_sync_index = 0, scan_length = 1 (clean, aligned
  stream).
- decode_frames: frames_locked = 40, sync_misses = 0, and every
  frame_data[k] equals the transmitted data words of frame k
  elementwise.
- demultiplex with sid_word_index 0, sid_mask 0x0003,
  supercommutated {"A": [1], "A2": [3, 5]}, subcommutated {"S":
  {"word_index": 2, "subframes": 4}}:
  - super A = [1000, 1001, ..., 1039] (40 values).
  - super A2 = [3000, 5000, 3001, 5001, ..., 3039, 5039] (80 values,
    frame order then slot order).
  - sub S: subframe 0 = [2000..2009], subframe 1 = [2100..2109],
    subframe 2 = [2200..2209], subframe 3 = [2300..2309] (10 values
    each).
  - subframe_ids = [0, 1, 2, 3, 0, 1, ...] (40 ids, cycling).

Corruption check on the same 40-frame stream with frame 20 sync word
replaced by 0xFFFF: frames_locked = 39, sync_misses = 1; channel A
recovers 39 values (the 1020 sample is dropped with frame 20);
channel A2 recovers 78 values (3020 and 5020 dropped); subframe 0 of
channel S recovers 9 values (the frame 20 sample, value 2005, is
dropped).

## Verification

- Confirm frame_period_words(8, 1) = 10, (8, 0) = 9, (0, 0) = 1, and
  that negative data_words_per_frame or idle_words raises ValueError.
- Confirm sync_search finds the first sync word at or after start and
  returns None when the sync word is absent; empty streams and
  negative sync words raise ValueError.
- Confirm acquire_lock on the clean stream reports first_sync_index 0;
  three junk words prepended shift it to 3 with the same recovered
  frames.
- Confirm on a clean stream every transmitted frame is locked
  (sync_misses == 0) and the recovered channel values equal the
  transmitted ramp values elementwise (deterministic identity).
- Confirm a frame whose sync word is corrupted is not locked and
  increments sync_misses by one, with its samples absent from every
  recovered channel.
- Confirm demultiplex raises ValueError on an empty frame list, an
  out-of-range sid_word_index, a ragged frame length, a supercommutated
  slot outside the frame, subframes below 1, and subcommutated entries
  missing their word_index or subframes keys.
- Confirm decommutation_summary returns exactly the keys frames_locked,
  sync_misses, super, sub, subframe_ids and matches the decode then
  demultiplex result.
- Run the contract test offline: python3
  scripts/test_pcm_telemetry_decommutation.py (27 tests,
  deterministic).

## Related leaves

- flight-test-operations/planning/telemetry-data-acquisition: the
  design side, sizes the PCM frame, assigns the supercommutated and
  subcommutated channels and stops at the transmitter.
- flight-test-operations/planning/flight-test-data-reduction: the post
  decomm processing side, calibrates, aligns and smooths the series
  this leaf recovers.
- flight-test-operations/planning/flight-test-instrumentation: the
  sensor and recorder chain upstream of the telemetry stream.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_pcm_telemetry_decommutation.py

The test covers the frame period arithmetic, sync word search, frame
lock acquisition on clean and unaligned streams with max_scan bounds,
the locked-frame walk on clean and corrupted streams (40 frames
locked with zero misses versus 39 locked with one miss), fixed and
supercommutated channel recovery including the interleaved multi slot
channel, subcommutated recovery keyed by the subframe id, the
subframe id trace, the elementwise ramp identity, the corruption
dropped-sample checks, and ValueError rejection of empty streams, no
sync word, negative frame words, out-of-range slots and malformed
format and subcommutation dicts.

## Compliance

- Standards referenced, not reproduced: FAR-25 sets the flight test
  and certification context; PCM decommutation practice (frame sync
  acquisition, minor frame locking, supercommutation and
  subcommutation demultiplexing) is common telemetry methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
