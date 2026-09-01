#!/usr/bin/env python3
"""Flight test telemetry and data acquisition logic (paraphrase, common
telemetry methodology).

Common-knowledge summary (standards-map.yaml, far-25/cs-25
reference-only context): the flight test telemetry chain samples the
instrumented channels, packs them into a PCM minor frame with IRIG
time coding, conditions the sensor signals to the ADC span, streams
the data to the ground station over the telemetry link, and gates the
recorded data on quality checks. The functions here cover PCM frame
and bit rate sizing, supercommutation and subcommutation of channels,
IRIG time of year coding, signal conditioning to the ADC span,
end-to-end data latency budgeting, the ground station link margin
check, and the telemetry quality verdict. Units stay SI (Hz, bit/s,
s, ms, dBm).
"""

import math


def pcm_frame_size(words_per_frame, bits_per_word):
    """Size of one PCM minor frame in bits.

    A PCM minor frame is words_per_frame words of bits_per_word bits
    each, so the frame holds words_per_frame * bits_per_word bits.
    Example: 64 words of 16 bits give 1024 bits per frame.

    Returns the frame size as an int.

    Raises ValueError on a non-int (or bool) words_per_frame with
    words_per_frame < 1, or a non-int (or bool) bits_per_word with
    bits_per_word < 1.
    """
    if isinstance(words_per_frame, bool) or not isinstance(words_per_frame, int):
        raise ValueError("words_per_frame must be an int, got %r" % (words_per_frame,))
    if words_per_frame < 1:
        raise ValueError("words_per_frame must be >= 1, got %r" % (words_per_frame,))
    if isinstance(bits_per_word, bool) or not isinstance(bits_per_word, int):
        raise ValueError("bits_per_word must be an int, got %r" % (bits_per_word,))
    if bits_per_word < 1:
        raise ValueError("bits_per_word must be >= 1, got %r" % (bits_per_word,))
    return words_per_frame * bits_per_word


def pcm_bit_rate(frame_rate, words_per_frame, bits_per_word):
    """Bit rate of the PCM stream.

    A minor frame of words_per_frame words of bits_per_word bits sent
    frame_rate times per second carries frame_rate * words_per_frame *
    bits_per_word bits per second. Example: 50 frames/s of 1024 bits
    give 51200 bit/s.

    Returns the bit rate as a float (bit/s).

    Raises ValueError on a non-numeric (or bool) frame_rate with
    frame_rate <= 0, or a non-int (or bool) words_per_frame or
    bits_per_word with a value < 1.
    """
    if isinstance(frame_rate, bool) or not isinstance(frame_rate, (int, float)):
        raise ValueError("frame_rate must be numeric, got %r" % (frame_rate,))
    if frame_rate <= 0:
        raise ValueError("frame_rate must be > 0, got %r" % (frame_rate,))
    if isinstance(words_per_frame, bool) or not isinstance(words_per_frame, int):
        raise ValueError("words_per_frame must be an int, got %r" % (words_per_frame,))
    if words_per_frame < 1:
        raise ValueError("words_per_frame must be >= 1, got %r" % (words_per_frame,))
    if isinstance(bits_per_word, bool) or not isinstance(bits_per_word, int):
        raise ValueError("bits_per_word must be an int, got %r" % (bits_per_word,))
    if bits_per_word < 1:
        raise ValueError("bits_per_word must be >= 1, got %r" % (bits_per_word,))
    return frame_rate * words_per_frame * bits_per_word


def supercommutated_instances(channel_sample_rate, frame_rate):
    """Supercommutated channel appearances per minor frame.

    A channel sampled faster than the minor frame rate appears
    channel_sample_rate / frame_rate times in every frame
    (supercommutation); the ratio must be an integer greater than 1.
    Example: a 200 Hz channel on a 50 frame/s stream appears 4 times
    per frame.

    Returns the instances per frame as an int.

    Raises ValueError on a non-numeric (or bool) channel_sample_rate or
    frame_rate with a value <= 0, or when the ratio is not an integer
    greater than 1.
    """
    for name, val in (("channel_sample_rate", channel_sample_rate), ("frame_rate", frame_rate)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
        if val <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, val))
    instances = channel_sample_rate / frame_rate
    if instances <= 1:
        raise ValueError(
            "channel_sample_rate must exceed frame_rate for supercommutation, "
            "got %r instances per frame" % (instances,)
        )
    if instances != int(instances):
        raise ValueError(
            "supercommutated instances per frame must be an integer, got %r"
            % (instances,)
        )
    return int(instances)


def subcommutated_instances(frame_rate, channel_sample_rate):
    """Subcommutated frames per sample of a slow channel.

    A channel sampled slower than the minor frame rate is sampled once
    every frame_rate / channel_sample_rate frames (subcommutation); the
    ratio must be an integer greater than 1. Example: a 25 Hz channel
    on a 100 frame/s stream is sampled once every 4 frames.

    Returns the frames per sample as an int.

    Raises ValueError on a non-numeric (or bool) frame_rate or
    channel_sample_rate with a value <= 0, or when the ratio is not an
    integer greater than 1.
    """
    for name, val in (("frame_rate", frame_rate), ("channel_sample_rate", channel_sample_rate)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
        if val <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, val))
    frames_per_sample = frame_rate / channel_sample_rate
    if frames_per_sample <= 1:
        raise ValueError(
            "channel_sample_rate must be below frame_rate for subcommutation, "
            "got %r frames per sample" % (frames_per_sample,)
        )
    if frames_per_sample != int(frames_per_sample):
        raise ValueError(
            "subcommutated frames per sample must be an integer, got %r"
            % (frames_per_sample,)
        )
    return int(frames_per_sample)


def irig_b_time_of_year(day_of_year, seconds_of_day):
    """Seconds of year for an IRIG-B time-of-year code.

    IRIG-B transmits the day of year and the seconds of day at 100
    pulses per second. The seconds of year are (day_of_year - 1) *
    86400 + seconds_of_day. Example: day 32 at 43200 s gives
    2721600.0 s.

    Returns the seconds of year as a float.

    Raises ValueError on a non-int (or bool) day_of_year outside 1..366
    (day 366 covers a leap year), or a non-numeric (or bool)
    seconds_of_day outside [0, 86400).
    """
    if isinstance(day_of_year, bool) or not isinstance(day_of_year, int):
        raise ValueError("day_of_year must be an int, got %r" % (day_of_year,))
    if not (1 <= day_of_year <= 366):
        raise ValueError("day_of_year must be in 1..366, got %r" % (day_of_year,))
    if isinstance(seconds_of_day, bool) or not isinstance(seconds_of_day, (int, float)):
        raise ValueError("seconds_of_day must be numeric, got %r" % (seconds_of_day,))
    if not (0 <= seconds_of_day < 86400):
        raise ValueError(
            "seconds_of_day must be in [0, 86400), got %r" % (seconds_of_day,)
        )
    return (day_of_year - 1) * 86400 + seconds_of_day


def conditioning_verdict(sensor_span, gain, adc_range):
    """Signal conditioning verdict: amplified span vs ADC full scale.

    The sensor signal of span sensor_span is amplified by the gain, so
    the conditioned span is sensor_span * gain and must fit the ADC
    full-scale range adc_range (same unit, V for voltage channels).
    The channel is "ok" when the conditioned span is within the ADC
    range, else "over-range" (the amplifier clips before the
    converter).

    Returns "ok" or "over-range".

    Raises ValueError on a non-numeric (or bool) argument with a value
    <= 0.
    """
    for name, val in (
        ("sensor_span", sensor_span),
        ("gain", gain),
        ("adc_range", adc_range),
    ):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
        if val <= 0:
            raise ValueError("%s must be > 0, got %r" % (name, val))
    conditioned_span = sensor_span * gain
    return "ok" if conditioned_span <= adc_range else "over-range"


def total_latency(acquisition_ms, processing_ms, link_ms):
    """End-to-end telemetry data latency in ms.

    The end-to-end latency is the sum of the acquisition delay, the
    processing delay, and the link delay: acquisition_ms +
    processing_ms + link_ms. Example: 5 ms + 10 ms + 25 ms give
    40.0 ms.

    Returns the total latency as a float (ms).

    Raises ValueError on a non-numeric (or bool) argument with a value
    < 0.
    """
    total = 0.0
    for name, val in (
        ("acquisition_ms", acquisition_ms),
        ("processing_ms", processing_ms),
        ("link_ms", link_ms),
    ):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
        if val < 0:
            raise ValueError("%s must be >= 0, got %r" % (name, val))
        total += val
    return total


def latency_ok(total_ms, requirement_ms):
    """Data latency verdict against the requirement.

    The telemetry data meets the latency requirement when total_ms <=
    requirement_ms.

    Returns True when the latency is within the requirement, else
    False.

    Raises ValueError on a non-numeric (or bool) total_ms with a value
    < 0, or a non-numeric (or bool) requirement_ms with a value <= 0.
    """
    if isinstance(total_ms, bool) or not isinstance(total_ms, (int, float)):
        raise ValueError("total_ms must be numeric, got %r" % (total_ms,))
    if total_ms < 0:
        raise ValueError("total_ms must be >= 0, got %r" % (total_ms,))
    if isinstance(requirement_ms, bool) or not isinstance(requirement_ms, (int, float)):
        raise ValueError("requirement_ms must be numeric, got %r" % (requirement_ms,))
    if requirement_ms <= 0:
        raise ValueError("requirement_ms must be > 0, got %r" % (requirement_ms,))
    return total_ms <= requirement_ms


def latency_buffer_samples(latency_s, sample_rate):
    """Samples buffered in the pipeline for the latency.

    A latency of latency_s seconds at sample_rate samples per second
    holds latency_s * sample_rate samples in the pipeline, rounded up
    because a partial sample still occupies a buffer slot. Example:
    0.05 s at 200 samples/s gives 10 samples.

    Returns the buffered samples as an int.

    Raises ValueError on a non-numeric (or bool) latency_s with a value
    < 0, or a non-numeric (or bool) sample_rate with a value <= 0.
    """
    if isinstance(latency_s, bool) or not isinstance(latency_s, (int, float)):
        raise ValueError("latency_s must be numeric, got %r" % (latency_s,))
    if latency_s < 0:
        raise ValueError("latency_s must be >= 0, got %r" % (latency_s,))
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, float)):
        raise ValueError("sample_rate must be numeric, got %r" % (sample_rate,))
    if sample_rate <= 0:
        raise ValueError("sample_rate must be > 0, got %r" % (sample_rate,))
    return int(math.ceil(latency_s * sample_rate))


def ground_link_ok(received_power_dbm, sensitivity_dbm, min_margin_dbm):
    """Ground station link margin verdict.

    The link margin is received_power_dbm minus sensitivity_dbm and
    must be at least min_margin_dbm for a reliable link. Example:
    -95.0 dBm received at -110.0 dBm sensitivity gives 15.0 dB of
    margin, which meets a 10.0 dB minimum.

    Returns True when the margin meets the minimum, else False.

    Raises ValueError on a non-numeric (or bool) argument, or a
    min_margin_dbm with a value <= 0.
    """
    for name, val in (
        ("received_power_dbm", received_power_dbm),
        ("sensitivity_dbm", sensitivity_dbm),
        ("min_margin_dbm", min_margin_dbm),
    ):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (name, val))
    if min_margin_dbm <= 0:
        raise ValueError("min_margin_dbm must be > 0, got %r" % (min_margin_dbm,))
    margin = received_power_dbm - sensitivity_dbm
    return margin >= min_margin_dbm


def telemetry_quality_ok(bit_error_rate, dropout_percent, ber_limit, dropout_limit):
    """Telemetry quality verdict from bit error rate and dropouts.

    The recorded data is usable when the bit error rate stays at or
    below ber_limit (errors per bit, in [0, 1]) and the dropout
    percentage stays at or below dropout_limit (in [0, 100]). Example:
    1e-5 errors per bit and 0.5 % dropouts pass limits of 1e-4 and
    1.0.

    Returns True when both checks pass, else False.

    Raises ValueError on a non-numeric (or bool) bit_error_rate or
    dropout_percent with a value out of range, or a non-numeric (or
    bool) limit with a value outside (0, 1] for ber_limit or (0, 100]
    for dropout_limit.
    """
    if isinstance(bit_error_rate, bool) or not isinstance(bit_error_rate, (int, float)):
        raise ValueError("bit_error_rate must be numeric, got %r" % (bit_error_rate,))
    if not (0 <= bit_error_rate <= 1):
        raise ValueError("bit_error_rate must be in [0, 1], got %r" % (bit_error_rate,))
    if isinstance(dropout_percent, bool) or not isinstance(dropout_percent, (int, float)):
        raise ValueError("dropout_percent must be numeric, got %r" % (dropout_percent,))
    if not (0 <= dropout_percent <= 100):
        raise ValueError(
            "dropout_percent must be in [0, 100], got %r" % (dropout_percent,)
        )
    if isinstance(ber_limit, bool) or not isinstance(ber_limit, (int, float)):
        raise ValueError("ber_limit must be numeric, got %r" % (ber_limit,))
    if not (0 < ber_limit <= 1):
        raise ValueError("ber_limit must be in (0, 1], got %r" % (ber_limit,))
    if isinstance(dropout_limit, bool) or not isinstance(dropout_limit, (int, float)):
        raise ValueError("dropout_limit must be numeric, got %r" % (dropout_limit,))
    if not (0 < dropout_limit <= 100):
        raise ValueError("dropout_limit must be in (0, 100], got %r" % (dropout_limit,))
    return bit_error_rate <= ber_limit and dropout_percent <= dropout_limit
