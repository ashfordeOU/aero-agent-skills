#!/usr/bin/env python3
"""Command authentication, ECSS-E-ST-50C clause 5.4.5.

Paraphrased requirement, no standard text reproduced. The clause places one
obligation on the telecommand chain: where authentication is required, a
command is acted on only when it has been shown to come from an authorized
source. Showing that takes more than a matching tag, so this module models
the whole decision a receiving end has to make:

  policy + command       -> is authentication required for this command at all
  key record + counter   -> is the key still valid for this command counter
  counter + last accepted -> is this a fresh command or a replay of an old one
  key + counter + octets -> the tag the command should carry
  carried tag vs. derived -> compared without leaking where they diverge

An unauthenticated command that needed authentication is refused; an
authenticated command that did not need it is still accepted, with the
authentication recorded. The refusal reason is reported so an operator can
tell a replay from a wrong key.

Tags are derived with the standard library keyed-hash construction over
integer octets, so the result is byte-identical on every host.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import hashlib
import hmac

# Octets of tag carried with an authenticated command by default. A truncated
# tag is legitimate; a very short one is not a tag.
DEFAULT_TAG_OCTETS = 16
MIN_TAG_OCTETS = 4

# Digest used to derive the tag.
DEFAULT_DIGEST = "sha256"

# How far ahead of the last accepted counter a command may be and still be
# taken, so a command lost on the link does not lock the receiver out.
DEFAULT_COUNTER_WINDOW = 32

# Outcome tokens.
ACCEPTED = "accepted"
ACCEPTED_UNAUTHENTICATED = "accepted-authentication-not-required"
MISSING_AUTHENTICATION = "refused-authentication-missing"
UNKNOWN_KEY = "refused-unknown-key"
KEY_NOT_VALID = "refused-key-not-valid-for-counter"
REPLAYED_COUNTER = "refused-replayed-counter"
COUNTER_OUT_OF_WINDOW = "refused-counter-out-of-window"
TAG_MISMATCH = "refused-tag-mismatch"
OUTCOMES = (
    ACCEPTED,
    ACCEPTED_UNAUTHENTICATED,
    MISSING_AUTHENTICATION,
    UNKNOWN_KEY,
    KEY_NOT_VALID,
    REPLAYED_COUNTER,
    COUNTER_OUT_OF_WINDOW,
    TAG_MISMATCH,
)

# Outcomes that let the command be acted on.
ACCEPTING_OUTCOMES = (ACCEPTED, ACCEPTED_UNAUTHENTICATED)

_KEY_KEYS = ("id", "secret", "valid_from_counter", "valid_to_counter")


def _integer(value, name):
    """Return value as an int, refusing bools, floats and text."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return int(value)


def validate_octets(data, name="octets"):
    """Return command content as bytes, refusing anything that is not octets."""
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if not isinstance(data, (list, tuple)):
        raise ValueError("%s must be octets, got %r" % (name, data))
    values = []
    for index, octet in enumerate(data):
        value = _integer(octet, "%s[%d]" % (name, index))
        if value < 0 or value > 255:
            raise ValueError(
                "%s[%d] must lie in 0..255, got %d" % (name, index, value)
            )
        values.append(value)
    return bytes(bytearray(values))


def validate_tag_octets(tag_octets=DEFAULT_TAG_OCTETS, digest=DEFAULT_DIGEST):
    """Validate the requested tag width against the digest that produces it."""
    if digest not in hashlib.algorithms_available:
        raise ValueError("digest %r is not available" % (digest,))
    width = _integer(tag_octets, "tag_octets")
    if width < MIN_TAG_OCTETS:
        raise ValueError(
            "tag_octets must be at least %d, got %d" % (MIN_TAG_OCTETS, width)
        )
    full = hashlib.new(digest).digest_size
    if width > full:
        raise ValueError(
            "tag_octets %d exceeds the %d octets %s produces" % (width, full, digest)
        )
    return width


def validate_key(key):
    """Validate a key record and return it normalized."""
    if not isinstance(key, dict):
        raise ValueError("key must be a mapping, got %r" % (key,))
    missing = [name for name in _KEY_KEYS if name not in key]
    if missing:
        raise ValueError("key is missing fields: %s" % ", ".join(missing))
    identifier = key["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("key id must be a non-empty string")
    secret = validate_octets(key["secret"], "key secret")
    if len(secret) < 16:
        raise ValueError("key secret must be at least 16 octets, got %d" % len(secret))
    low = _integer(key["valid_from_counter"], "valid_from_counter")
    high = _integer(key["valid_to_counter"], "valid_to_counter")
    if low < 0 or high < 0:
        raise ValueError("key validity counters must not be negative")
    if low > high:
        raise ValueError("key validity range is inverted: %d > %d" % (low, high))
    return {
        "id": identifier.strip(),
        "secret": secret,
        "valid_from_counter": low,
        "valid_to_counter": high,
    }


def key_is_valid_for(key, counter):
    """True when a key may still be used at this command counter."""
    record = validate_key(key)
    value = _integer(counter, "counter")
    if value < 0:
        raise ValueError("counter must not be negative, got %d" % value)
    return record["valid_from_counter"] <= value <= record["valid_to_counter"]


def counter_freshness(counter, last_accepted, window=DEFAULT_COUNTER_WINDOW):
    """Say whether a counter is fresh, a replay, or too far ahead to trust."""
    value = _integer(counter, "counter")
    previous = _integer(last_accepted, "last_accepted")
    span = _integer(window, "window")
    if value < 0 or previous < 0:
        raise ValueError("counters must not be negative")
    if span < 1:
        raise ValueError("window must be at least 1, got %d" % span)
    if value <= previous:
        return REPLAYED_COUNTER
    if value - previous > span:
        return COUNTER_OUT_OF_WINDOW
    return ACCEPTED


def derive_tag(
    key, counter, command_octets, tag_octets=DEFAULT_TAG_OCTETS, digest=DEFAULT_DIGEST
):
    """Derive the tag an authorized source would carry for this command."""
    record = validate_key(key)
    width = validate_tag_octets(tag_octets, digest)
    value = _integer(counter, "counter")
    if value < 0:
        raise ValueError("counter must not be negative, got %d" % value)
    content = validate_octets(command_octets, "command_octets")
    message = (
        record["id"].encode("utf-8")
        + b"\x00"
        + value.to_bytes(8, "big")
        + b"\x00"
        + content
    )
    return hmac.new(record["secret"], message, digest).digest()[:width]


def verify_tag(
    key,
    counter,
    command_octets,
    carried_tag,
    tag_octets=DEFAULT_TAG_OCTETS,
    digest=DEFAULT_DIGEST,
):
    """Compare a carried tag with the derived one without revealing where."""
    expected = derive_tag(key, counter, command_octets, tag_octets, digest)
    carried = validate_octets(carried_tag, "carried_tag")
    if len(carried) != len(expected):
        return False
    return hmac.compare_digest(carried, expected)


def authentication_required(command_name, protected_commands):
    """True when policy says this command may only be acted on authenticated."""
    if not isinstance(command_name, str) or not command_name.strip():
        raise ValueError("command_name must be a non-empty string")
    if isinstance(protected_commands, str) or not isinstance(
        protected_commands, (list, tuple, set, frozenset)
    ):
        raise ValueError("protected_commands must be a collection of names")
    return command_name.strip() in {
        name.strip() for name in protected_commands if isinstance(name, str)
    }


def assess_command_authentication(
    command_name,
    command_octets,
    protected_commands,
    key=None,
    counter=None,
    carried_tag=None,
    last_accepted_counter=-1,
    window=DEFAULT_COUNTER_WINDOW,
    tag_octets=DEFAULT_TAG_OCTETS,
    digest=DEFAULT_DIGEST,
):
    """Decide whether one command may be acted on, per clause 5.4.5."""
    required = authentication_required(command_name, protected_commands)
    presented = carried_tag is not None

    if not presented:
        outcome = MISSING_AUTHENTICATION if required else ACCEPTED_UNAUTHENTICATED
        return {
            "command": command_name.strip(),
            "authentication_required": required,
            "authentication_presented": False,
            "outcome": outcome,
            "act_on_command": outcome in ACCEPTING_OUTCOMES,
            "next_last_accepted_counter": _integer(
                last_accepted_counter, "last_accepted_counter"
            ),
            "key_id": None,
        }

    if key is None:
        outcome = UNKNOWN_KEY
        record = None
    else:
        record = validate_key(key)
        outcome = None

    value = None
    if outcome is None:
        if counter is None:
            raise ValueError("an authenticated command must carry a counter")
        value = _integer(counter, "counter")
        if not key_is_valid_for(record, value):
            outcome = KEY_NOT_VALID
        else:
            freshness = counter_freshness(value, last_accepted_counter, window)
            if freshness != ACCEPTED:
                outcome = freshness
            elif not verify_tag(
                record, value, command_octets, carried_tag, tag_octets, digest
            ):
                outcome = TAG_MISMATCH
            else:
                outcome = ACCEPTED

    accepted = outcome in ACCEPTING_OUTCOMES
    return {
        "command": command_name.strip(),
        "authentication_required": required,
        "authentication_presented": True,
        "outcome": outcome,
        "act_on_command": accepted,
        "next_last_accepted_counter": value
        if accepted and value is not None
        else _integer(last_accepted_counter, "last_accepted_counter"),
        "key_id": record["id"] if record is not None else None,
    }
