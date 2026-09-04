# Wave-35 leaf spec: pcm-telemetry-decommutation (flight-test-operations, planning pack)

- Path: skills/flight-test-operations/planning/pcm-telemetry-decommutation/
- Pack: planning. Closest siblings: telemetry-data-acquisition (the
  DESIGN leaf: sizes the PCM minor frame and bit rate, ASSIGNS
  supercommutated and subcommutated channels against the frame rate,
  encodes IRIG time, conditions signals, budgets latency and link
  margin - it stops at the transmitter), flight-test-data-reduction
  (post-decomm processing: calibration correction, time alignment,
  moving average, corrected airspeed). Repo-wide grep proves ZERO
  owners for decommutation, frame sync, subframe demultiplexing.
- Standards id: far-25 (reference-only; sibling precedent
  telemetry-data-acquisition carries far-25/cs-25). Ledger
  Standard: far-25.
- Family: flight-test-operations

## Claim

Decode a serial PCM minor-frame telemetry stream at the ground
station: given the word stream, the frame format (sync word, data
words per frame, idle word spacing), acquire frame sync by finding
the sync pattern, walk the locked frames and count sync misses, and
demultiplex the channels: fixed channels from their word slots every
frame, supercommutated channels from their multiple word slots per
frame, and subcommutated channels keyed by the subframe ID into the
per-subframe value lists. Produces the locked frame count, the sync
miss report, and the recovered per-channel time series that feed
data reduction.

Does NOT do: PCM frame and bit rate sizing, channel assignment,
IRIG time encoding, link margin and bit error rate budgeting, signal
conditioning (telemetry-data-acquisition owns the design side);
calibration correction, time alignment, smoothing (flight-test-data-
reduction); RF/downlink hardware.

## Model (implement exactly)

Module constants:
- None beyond defaults in signatures.

Conventions: the stream is a list of non-negative integer words
(0 <= w < 2^word_bits). A minor frame on the wire is the sync word
followed by the data words, then the idle words before the next sync
word. The frame period in words is 1 + data_words_per_frame +
idle_words. Word indices inside a frame are 0-based over the DATA
words only (word 0 is the first data word after the sync word). The
subframe ID is read from a designated data word masked to its low
bits. A supercommutated channel occupies one or more fixed word slots
and yields that many samples per frame. A subcommutated channel
occupies one word slot whose value is one of M sub-values; the
subframe ID carried by the frame tells which sub-value the sample
belongs to.

Functions (pure stdlib):
- frame_period_words(data_words_per_frame, idle_words) -> 1 +
  data_words_per_frame + idle_words. ValueErrors on negative inputs.
- sync_search(stream, sync_word, start = 0) -> index of the first
  occurrence of sync_word at or after start, or None when absent.
  ValueError: empty stream, sync_word < 0.
- acquire_lock(stream, sync_word, data_words_per_frame, idle_words
  = 0, max_scan = None) -> dict {first_sync_index, scan_length}
  = sync_search from index 0 (scan limited to max_scan when given).
  ValueError when no sync word is found (stream unreadable).
- decode_frames(stream, sync_word, data_words_per_frame, idle_words
  = 0) -> dict {frames_locked, sync_misses, frame_data} where
  frame_data is the list of per-frame data-word lists (only frames
  whose sync word matched are locked and appended). Walk: at each
  expected sync position (first_sync_index + k * period), if the
  word equals sync_word the frame is locked and the following
  data_words_per_frame words are recorded; otherwise increment
  sync_misses and resync by sync_search from the expected position
  + 1 (bounded to the next two periods) and continue from there.
  ValueErrors: negative data_words_per_frame, empty stream, no sync
  at all.
- demultiplex(frame_data, sid_word_index, sid_mask,
  supercommutated, subcommutated) -> dict {super, sub,
  subframe_ids} where super = {channel: [values across frames in
  frame order, slot order]}, sub = {channel: {subframe_index:
  [values]}}, subframe_ids = [word & sid_mask for each frame].
  supercommutated = {channel: [word indices]}; subcommutated =
  {channel: {"word_index": i, "subframes": M}}. ValueErrors:
  sid_word_index out of range for the frame length, empty frame
  list, unknown keys, subframes < 1.
- decommutation_summary(stream, sync_word, data_words_per_frame,
  idle_words, format) -> dict combining decode_frames and
  demultiplex outputs under one format dict (keys sid_word_index,
  sid_mask, supercommutated, subcommutated). Returns {frames_locked,
  sync_misses, super, sub, subframe_ids}.

Deterministic identity to test: on a clean stream every transmitted
frame is locked (sync_misses == 0) and the recovered channel values
equal the transmitted ramp values elementwise; a frame whose sync
word is corrupted is not locked and increments sync_misses by one.

## Worked example

Fixture (16-bit words, constructed deterministically in the test):
sync word 0xEB90, 8 data words per frame, 1 idle word, so the frame
period is 10 words. Frame k (k = 0..39) data words: word0 = k & 3
(subframe ID), word1 = 1000 + k (channel A, fixed slot), word2 =
2000 + (k & 3) * 100 + (k // 4) (channel S subcommutated, 4
subframes), word3 = 3000 + k (channel A2 supercommutated, first
slot), word4 = 4000 + k (filler), word5 = 5000 + k (channel A2
supercommutated, second slot), word6 = 6000 + k (filler), word7 =
7000 + k (filler). Idle word 0x0000. The wire stream is the 40
frames concatenated (400 words), starting at index 0.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds:
- frame_period_words(8, 1) = 10.
- acquire_lock: first_sync_index = 0 (clean aligned stream).
- decode_frames: frames_locked = 40, sync_misses = 0.
- demultiplex with sid_word_index 0, sid_mask 0x0003,
  supercommutated {"A": [1], "A2": [3, 5]}, subcommutated {"S":
  {"word_index": 2, "subframes": 4}}:
  - super A = [1000..1039] (40 values).
  - super A2 = 80 values interleaved [3000+0, 5000+0, 3000+1,
    5000+1, ...].
  - sub S: subframe 0 = [2000..2009] (10 values), subframe 1 =
    [2100..2109], subframe 2 = [2200..2209], subframe 3 =
    [2300..2309] (10 values each).
  - subframe_ids = [0,1,2,3,0,1,...] (40 ids).

Corruption check (validation fixture): the same 40-frame stream with
frame 20's sync word replaced by 0xFFFF gives frames_locked = 39,
sync_misses = 1; channel A recovers 39 values (frame 20 dropped);
subframe 0 of channel S recovers 9 values (the sample at frame 20,
value 2005, is dropped).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: negative data_words_per_frame / idle_words; empty
  stream; sync_word < 0; no sync word found (acquire_lock raises);
  decode on a stream with no sync raises; sid_word_index out of
  range; empty frame list; subframes < 1.
- Period: frame_period_words(8, 1) = 10; (8, 0) = 9; (0, 0) = 1.
- Clean stream: worked example asserts above elementwise; identical
  stream decodes identically (determinism).
- Unaligned stream: three junk words prepended -> first_sync_index
  = 3 and the same recovered arrays.
- Corruption: frame 20 sync corrupted -> 39 locked, 1 miss, frame
  20 samples absent, subframe 0 length 9.
- Sync search: sync_word absent -> acquire_lock ValueError;
  sync_search returns None.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-pcm-telemetry-decommutation.yaml)

Query 1 (copy verbatim):
  "acquire PCM telemetry frame sync lock and decommutate the supercommutated and subcommutated channels into time series"
  intent: "flight-test-operations; PCM frame sync and channel decommutation"
  expected_skill: "flight-test-operations/planning/pcm-telemetry-decommutation"
Query 2 (copy verbatim):
  "demultiplex a PCM minor frame stream by the subframe id into the recovered telemetry channel samples"
  intent: "flight-test-operations; subframe id demultiplexing of PCM telemetry channels"
  expected_skill: "flight-test-operations/planning/pcm-telemetry-decommutation"
Task ids: w35-pcm-telemetry-decommutation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decommutate a serial PCM
telemetry stream:" and include the outputs in the Claim. First tag:
pcm-telemetry-decommutation. Additional tags ONLY: pcm-frame-sync,
supercommutated-demux, subcommutated-demux, minor-frame-decode.
NEVER single generic words (telemetry, frame, sync, channel, decode,
stream). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): frame rate sizing, bit rate
sizing, IRIG time, signal conditioning, ADC span, data latency,
link margin, bit error rate, dropout, ground station link
(telemetry-data-acquisition); calibration correction, time
alignment, moving average, corrected airspeed (flight-test-data-
reduction); RF, Nyquist, anti-aliasing.
