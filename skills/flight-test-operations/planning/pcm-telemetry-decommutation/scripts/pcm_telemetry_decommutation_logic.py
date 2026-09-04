#!/usr/bin/env python3
"""PCM minor-frame telemetry decommutation: frame sync, lock and demultiplex.

Pure-stdlib decode side of a serial PCM telemetry word stream: find the
sync word, walk the locked minor frames and count sync misses, and
demultiplex the recovered channels - fixed channels from their word
slot every frame, supercommutated channels from their multiple word
slots per frame, and subcommutated channels keyed by the subframe id
into the per-subframe value lists. Produces the locked frame count,
the sync miss report and the per-channel time series that feed flight
test data reduction.

Conventions: the stream is a list of non-negative integer words. A
minor frame on the wire is the sync word followed by the data words,
then the idle words before the next sync word, so the frame period in
words is 1 + data_words_per_frame + idle_words. Word indices inside a
frame are 0-based over the DATA words only. The subframe id is read
from a designated data word masked to its low bits. All inputs are
validated; non-physical values raise ValueError.
"""

from __future__ import annotations


def frame_period_words(data_words_per_frame, idle_words):
    """Words from one sync word to the next: 1 + data + idle.

    A minor frame on the wire is the sync word followed by the data
    words, then the idle words before the next sync word.
    """
    if data_words_per_frame < 0:
        raise ValueError("data_words_per_frame must be non-negative")
    if idle_words < 0:
        raise ValueError("idle_words must be non-negative")
    return 1 + data_words_per_frame + idle_words


def _scan(stream, sync_word, start, end):
    """First sync_word index in stream[start:end], or None when absent."""
    for i in range(start, min(end, len(stream))):
        if stream[i] == sync_word:
            return i
    return None


def sync_search(stream, sync_word, start=0):
    """Index of the first occurrence of sync_word at or after start.

    Returns None when the sync word is absent from the scanned part.
    """
    if not stream:
        raise ValueError("empty stream")
    if sync_word < 0:
        raise ValueError("sync_word must be non-negative")
    return _scan(stream, sync_word, start if start >= 0 else 0, len(stream))


def acquire_lock(stream, sync_word, data_words_per_frame, idle_words=0,
                 max_scan=None):
    """Find the first sync word and report the lock position.

    Scans from index 0, limited to max_scan words when given. Returns
    {"first_sync_index": i, "scan_length": words examined up to and
    including the sync word}. Raises ValueError when the stream is
    unreadable, that is, no sync word is found in the scanned region.
    """
    if not stream:
        raise ValueError("empty stream")
    if sync_word < 0:
        raise ValueError("sync_word must be non-negative")
    if data_words_per_frame < 0:
        raise ValueError("data_words_per_frame must be non-negative")
    if idle_words < 0:
        raise ValueError("idle_words must be non-negative")
    if max_scan is not None and max_scan < 0:
        raise ValueError("max_scan must be non-negative")
    window_end = len(stream) if max_scan is None else min(max_scan, len(stream))
    first = _scan(stream, sync_word, 0, window_end)
    if first is None:
        raise ValueError("no sync word found; stream unreadable")
    return {"first_sync_index": first, "scan_length": first + 1}


def decode_frames(stream, sync_word, data_words_per_frame, idle_words=0):
    """Walk the locked minor frames of the stream and record their data.

    At each expected sync position (first sync index plus k frame
    periods), a word equal to the sync word locks the frame and the
    following data_words_per_frame words are recorded; any other word
    increments sync_misses and the walk resyncs by scanning forward
    from the missed position, bounded to the next two periods. Returns
    {"frames_locked": n, "sync_misses": m, "frame_data": [...]}.
    """
    if not stream:
        raise ValueError("empty stream")
    if data_words_per_frame < 0:
        raise ValueError("data_words_per_frame must be non-negative")
    if idle_words < 0:
        raise ValueError("idle_words must be non-negative")
    period = frame_period_words(data_words_per_frame, idle_words)
    first = acquire_lock(stream, sync_word, data_words_per_frame,
                         idle_words)["first_sync_index"]
    frame_data = []
    sync_misses = 0
    pos = first
    while pos + 1 + data_words_per_frame <= len(stream):
        if stream[pos] == sync_word:
            frame_data.append(stream[pos + 1:pos + 1 + data_words_per_frame])
            pos += period
            continue
        sync_misses += 1
        # Resync: scan from the missed position, bounded to two periods.
        resync = _scan(stream, sync_word, pos + 1, pos + 1 + 2 * period)
        if resync is None:
            break
        pos = resync
    return {"frames_locked": len(frame_data), "sync_misses": sync_misses,
            "frame_data": frame_data}


def demultiplex(frame_data, sid_word_index, sid_mask, supercommutated,
                subcommutated):
    """Split locked frame data into the per-channel time series.

    supercommutated maps a channel name to the word slots it occupies
    (one or more, in slot order) and yields that many samples per
    frame. subcommutated maps a channel name to {"word_index": i,
    "subframes": M}: the slot carries M sub-values and the subframe id
    carried by the frame selects which sub-value the sample belongs
    to. Returns {"super": {...}, "sub": {...}, "subframe_ids": [...]}.
    """
    if not frame_data:
        raise ValueError("empty frame list")
    frame_len = len(frame_data[0])
    if any(len(frame) != frame_len for frame in frame_data):
        raise ValueError("frames differ in length")
    if not isinstance(sid_word_index, int) or not (0 <= sid_word_index < frame_len):
        raise ValueError("sid_word_index out of range for the frame length")

    super_out = {}
    for channel, slots in supercommutated.items():
        for slot in slots:
            if not isinstance(slot, int) or not (0 <= slot < frame_len):
                raise ValueError("supercommutated word slot out of range")
        super_out[channel] = [frame[slot] for frame in frame_data
                              for slot in slots]

    sub_out = {}
    for channel, entry in subcommutated.items():
        if not isinstance(entry, dict) or set(entry) != {"word_index", "subframes"}:
            raise ValueError("subcommutated entry needs word_index and subframes")
        word_index = entry["word_index"]
        subframes = entry["subframes"]
        if not isinstance(word_index, int) or not (0 <= word_index < frame_len):
            raise ValueError("subcommutated word_index out of range")
        if not isinstance(subframes, int) or subframes < 1:
            raise ValueError("subframes must be at least 1")
        buckets = {i: [] for i in range(subframes)}
        for frame in frame_data:
            sub_id = frame[sid_word_index] & sid_mask
            if not (0 <= sub_id < subframes):
                raise ValueError("subframe id out of range for subframes")
            buckets[sub_id].append(frame[word_index])
        sub_out[channel] = buckets

    subframe_ids = [frame[sid_word_index] & sid_mask for frame in frame_data]
    return {"super": super_out, "sub": sub_out, "subframe_ids": subframe_ids}


def decommutation_summary(stream, sync_word, data_words_per_frame, idle_words,
                          format):
    """Decode and demultiplex in one call under a single format dict.

    The format dict carries the keys sid_word_index, sid_mask,
    supercommutated and subcommutated. Returns {"frames_locked": n,
    "sync_misses": m, "super": {...}, "sub": {...},
    "subframe_ids": [...]}.
    """
    required = ("sid_word_index", "sid_mask", "supercommutated", "subcommutated")
    if not isinstance(format, dict) or any(k not in format for k in required):
        raise ValueError("format dict needs sid_word_index, sid_mask, "
                         "supercommutated and subcommutated keys")
    decoded = decode_frames(stream, sync_word, data_words_per_frame, idle_words)
    demux = demultiplex(decoded["frame_data"], format["sid_word_index"],
                        format["sid_mask"], format["supercommutated"],
                        format["subcommutated"])
    return {"frames_locked": decoded["frames_locked"],
            "sync_misses": decoded["sync_misses"],
            "super": demux["super"], "sub": demux["sub"],
            "subframe_ids": demux["subframe_ids"]}
