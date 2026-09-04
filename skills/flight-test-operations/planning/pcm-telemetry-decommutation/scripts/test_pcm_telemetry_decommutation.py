#!/usr/bin/env python3
"""Gate 3 contract test: pcm-telemetry-decommutation.

Exercises scripts/pcm_telemetry_decommutation_logic.py (stdlib
unittest, offline, deterministic). Contract: docs/harness-contract.md
gate 3 - frame_period_words returns 1 + data + idle; sync_search finds
the sync word or None; acquire_lock reports the first sync index and
the scanned length; decode_frames walks the locked minor frames and
counts sync misses; demultiplex recovers fixed, supercommutated and
subcommutated channel time series keyed by the subframe id;
decommutation_summary combines decode and demultiplex under one format
dict. Worked-example fixture: 16-bit words, sync 0xEB90, 8 data words
per frame, 1 idle word (period 10), 40 frames built deterministically.
"""

import unittest

import pcm_telemetry_decommutation_logic as pcm

SYNC_WORD = 0xEB90
IDLE_WORD = 0x0000
DATA_WORDS = 8
IDLE_WORDS = 1
FRAMES = 40

FORMAT = {"sid_word_index": 0, "sid_mask": 0x0003,
          "supercommutated": {"A": [1], "A2": [3, 5]},
          "subcommutated": {"S": {"word_index": 2, "subframes": 4}}}


def frame_data_words(k):
    """Data words of frame k in the worked-example fixture."""
    return [k & 3, 1000 + k, 2000 + (k & 3) * 100 + (k // 4), 3000 + k,
            4000 + k, 5000 + k, 6000 + k, 7000 + k]


def build_stream(corrupt_frame=None):
    """Deterministic 40-frame wire stream; optionally corrupt a sync word."""
    words = []
    for k in range(FRAMES):
        words.append(0xFFFF if k == corrupt_frame else SYNC_WORD)
        words.extend(frame_data_words(k))
        words.append(IDLE_WORD)
    return words


def decode(stream, corrupt=False):
    """Decode helper; corrupt option only for building the corrupt stream."""
    if corrupt:
        stream = build_stream(corrupt_frame=20)
    return pcm.decode_frames(stream, SYNC_WORD, DATA_WORDS, IDLE_WORDS)


class TestFramePeriod(unittest.TestCase):
    def test_period_values(self):
        self.assertEqual(pcm.frame_period_words(8, 1), 10)
        self.assertEqual(pcm.frame_period_words(8, 0), 9)
        self.assertEqual(pcm.frame_period_words(0, 0), 1)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcm.frame_period_words(-1, 0)
        with self.assertRaises(ValueError):
            pcm.frame_period_words(8, -1)


class TestSyncSearch(unittest.TestCase):
    def test_finds_first_occurrence_and_start(self):
        stream = [SYNC_WORD, 2, SYNC_WORD]
        self.assertEqual(pcm.sync_search(stream, SYNC_WORD), 0)
        self.assertEqual(pcm.sync_search(stream, SYNC_WORD, start=2), 2)

    def test_absent_returns_none(self):
        self.assertIsNone(pcm.sync_search([1, 2, 3], SYNC_WORD))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcm.sync_search([], SYNC_WORD)
        with self.assertRaises(ValueError):
            pcm.sync_search([1, 2, 3], -1)


class TestAcquireLock(unittest.TestCase):
    def test_clean_stream_first_sync_zero(self):
        lock = pcm.acquire_lock(build_stream(), SYNC_WORD, DATA_WORDS,
                                IDLE_WORDS)
        self.assertEqual(lock["first_sync_index"], 0)
        self.assertEqual(lock["scan_length"], 1)
        self.assertEqual(set(lock), {"first_sync_index", "scan_length"})

    def test_unaligned_stream_first_sync_three(self):
        junk = [0x0001, 0x0002, 0x0003]
        lock = pcm.acquire_lock(junk + build_stream(), SYNC_WORD, DATA_WORDS,
                                IDLE_WORDS)
        self.assertEqual(lock["first_sync_index"], 3)
        self.assertEqual(lock["scan_length"], 4)

    def test_max_scan_bounds_and_errors(self):
        junk = [0x0001, 0x0002, 0x0003]
        lock = pcm.acquire_lock(junk + build_stream(), SYNC_WORD, DATA_WORDS,
                                IDLE_WORDS, max_scan=6)
        self.assertEqual(lock["first_sync_index"], 3)
        with self.assertRaises(ValueError):
            pcm.acquire_lock(junk + build_stream(), SYNC_WORD, DATA_WORDS,
                             IDLE_WORDS, max_scan=3)
        with self.assertRaises(ValueError):
            pcm.acquire_lock([0] * 200, SYNC_WORD, DATA_WORDS, IDLE_WORDS)
        with self.assertRaises(ValueError):
            pcm.acquire_lock([], SYNC_WORD, DATA_WORDS, IDLE_WORDS)


class TestDecodeFrames(unittest.TestCase):
    def test_clean_stream_locks_all_frames(self):
        dec = decode(build_stream())
        self.assertEqual(dec["frames_locked"], 40)
        self.assertEqual(dec["sync_misses"], 0)
        self.assertEqual(set(dec), {"frames_locked", "sync_misses",
                                    "frame_data"})
        for k in range(FRAMES):
            self.assertEqual(dec["frame_data"][k], frame_data_words(k))

    def test_identical_stream_decodes_identically(self):
        s = build_stream()
        self.assertEqual(pcm.decode_frames(s, SYNC_WORD, DATA_WORDS, IDLE_WORDS),
                         pcm.decode_frames(s, SYNC_WORD, DATA_WORDS, IDLE_WORDS))

    def test_corrupt_sync_yields_39_locked_1_miss(self):
        dec = decode(build_stream(), corrupt=True)
        self.assertEqual(dec["frames_locked"], 39)
        self.assertEqual(dec["sync_misses"], 1)
        expected = [frame_data_words(k) for k in range(FRAMES) if k != 20]
        self.assertEqual(dec["frame_data"], expected)

    def test_unaligned_stream_recovers_clean_frames(self):
        junk = [0x0001, 0x0002, 0x0003]
        dec = pcm.decode_frames(junk + build_stream(), SYNC_WORD, DATA_WORDS,
                                IDLE_WORDS)
        self.assertEqual(dec["frames_locked"], 40)
        self.assertEqual(dec["sync_misses"], 0)
        clean = pcm.decode_frames(build_stream(), SYNC_WORD, DATA_WORDS,
                                  IDLE_WORDS)
        self.assertEqual(dec["frame_data"], clean["frame_data"])

    def test_invalid_streams_raise(self):
        with self.assertRaises(ValueError):
            pcm.decode_frames([], SYNC_WORD, DATA_WORDS, IDLE_WORDS)
        with self.assertRaises(ValueError):
            pcm.decode_frames([0] * 200, SYNC_WORD, DATA_WORDS, IDLE_WORDS)
        with self.assertRaises(ValueError):
            pcm.decode_frames(build_stream(), SYNC_WORD, -1, IDLE_WORDS)


class TestDemultiplex(unittest.TestCase):
    def setUp(self):
        self.frame_data = decode(build_stream())["frame_data"]
        self.demux = pcm.demultiplex(self.frame_data, 0, 0x0003,
                                     FORMAT["supercommutated"],
                                     FORMAT["subcommutated"])

    def test_result_dict_keys(self):
        self.assertEqual(set(self.demux), {"super", "sub", "subframe_ids"})
        self.assertEqual(set(self.demux["super"]), {"A", "A2"})
        self.assertEqual(set(self.demux["sub"]), {"S"})

    def test_super_A_is_ramp_1000_to_1039(self):
        self.assertEqual(self.demux["super"]["A"], list(range(1000, 1040)))

    def test_super_A2_interleaves_both_slots(self):
        expected = [v for k in range(FRAMES) for v in (3000 + k, 5000 + k)]
        self.assertEqual(self.demux["super"]["A2"], expected)
        self.assertEqual(len(self.demux["super"]["A2"]), 80)

    def test_sub_S_subframe_lists(self):
        sub = self.demux["sub"]["S"]
        self.assertEqual(set(sub), {0, 1, 2, 3})
        self.assertEqual(sub[0], list(range(2000, 2010)))
        self.assertEqual(sub[1], list(range(2100, 2110)))
        self.assertEqual(sub[2], list(range(2200, 2210)))
        self.assertEqual(sub[3], list(range(2300, 2310)))

    def test_subframe_ids_and_ramp_identity(self):
        self.assertEqual(self.demux["subframe_ids"][:8],
                         [0, 1, 2, 3, 0, 1, 2, 3])
        self.assertEqual(len(self.demux["subframe_ids"]), 40)
        for k in range(FRAMES):
            self.assertEqual(self.demux["sub"]["S"][k & 3][k // 4],
                             2000 + (k & 3) * 100 + (k // 4))

    def test_empty_and_ragged_frames_raise(self):
        with self.assertRaises(ValueError):
            pcm.demultiplex([], 0, 0x0003, FORMAT["supercommutated"],
                            FORMAT["subcommutated"])
        ragged = [self.frame_data[0], self.frame_data[1] + [0]]
        with self.assertRaises(ValueError):
            pcm.demultiplex(ragged, 0, 0x0003, FORMAT["supercommutated"],
                            FORMAT["subcommutated"])

    def test_bad_slot_references_raise(self):
        with self.assertRaises(ValueError):
            pcm.demultiplex(self.frame_data, DATA_WORDS, 0x0003,
                            FORMAT["supercommutated"], FORMAT["subcommutated"])
        with self.assertRaises(ValueError):
            pcm.demultiplex(self.frame_data, -1, 0x0003,
                            FORMAT["supercommutated"], FORMAT["subcommutated"])
        with self.assertRaises(ValueError):
            pcm.demultiplex(self.frame_data, 0, 0x0003, {"X": [99]},
                            FORMAT["subcommutated"])

    def test_bad_subcommutation_raises(self):
        with self.assertRaises(ValueError):
            pcm.demultiplex(self.frame_data, 0, 0x0003,
                            FORMAT["supercommutated"],
                            {"S": {"word_index": 2, "subframes": 0}})
        with self.assertRaises(ValueError):
            pcm.demultiplex(self.frame_data, 0, 0x0003,
                            FORMAT["supercommutated"],
                            {"S": {"word_index": 2}})


class TestCorruptionRecovery(unittest.TestCase):
    def setUp(self):
        frame_data = decode(build_stream(), corrupt=True)["frame_data"]
        self.demux = pcm.demultiplex(frame_data, 0, 0x0003,
                                     FORMAT["supercommutated"],
                                     FORMAT["subcommutated"])

    def test_channel_A_recovers_39_values(self):
        expected = [1000 + k for k in range(FRAMES) if k != 20]
        self.assertEqual(self.demux["super"]["A"], expected)

    def test_channel_S_subframe_0_drops_frame_20_sample(self):
        self.assertEqual(len(self.demux["sub"]["S"][0]), 9)
        self.assertNotIn(2005, self.demux["sub"]["S"][0])

    def test_channel_A2_drops_frame_20_samples(self):
        a2 = self.demux["super"]["A2"]
        self.assertEqual(len(a2), 78)
        self.assertNotIn(3020, a2)
        self.assertNotIn(5020, a2)


class TestSummary(unittest.TestCase):
    def test_summary_matches_decode_and_demultiplex(self):
        s = build_stream()
        dec = pcm.decode_frames(s, SYNC_WORD, DATA_WORDS, IDLE_WORDS)
        dem = pcm.demultiplex(dec["frame_data"], 0, 0x0003,
                              FORMAT["supercommutated"],
                              FORMAT["subcommutated"])
        summ = pcm.decommutation_summary(s, SYNC_WORD, DATA_WORDS, IDLE_WORDS,
                                         FORMAT)
        self.assertEqual(set(summ),
                         {"frames_locked", "sync_misses", "super", "sub",
                          "subframe_ids"})
        self.assertEqual(summ["frames_locked"], dec["frames_locked"])
        self.assertEqual(summ["sync_misses"], dec["sync_misses"])
        self.assertEqual(summ["super"], dem["super"])
        self.assertEqual(summ["sub"], dem["sub"])
        self.assertEqual(summ["subframe_ids"], dem["subframe_ids"])

    def test_summary_on_corrupt_stream(self):
        summ = pcm.decommutation_summary(build_stream(corrupt_frame=20),
                                         SYNC_WORD, DATA_WORDS, IDLE_WORDS,
                                         FORMAT)
        self.assertEqual(summ["frames_locked"], 39)
        self.assertEqual(summ["sync_misses"], 1)
        self.assertEqual(len(summ["super"]["A"]), 39)
        self.assertEqual(len(summ["sub"]["S"][0]), 9)

    def test_bad_format_dict_raises(self):
        with self.assertRaises(ValueError):
            pcm.decommutation_summary(build_stream(), SYNC_WORD, DATA_WORDS,
                                      IDLE_WORDS, {"sid_word_index": 0})


if __name__ == "__main__":
    unittest.main()
