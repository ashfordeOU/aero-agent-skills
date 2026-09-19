#!/usr/bin/env python3
"""Scan produced artefacts for the classic hermeticity violations.

A pipeline can be bit-identical on one machine and still be non-hermetic:
it only looks stable because the machine did not move. This scanner reads
artefact bytes and reports the traces that make an artefact machine- or
moment-specific:

  * embedded timestamps (ISO-8601, ctime, RFC 2822, epoch seconds/millis)
  * absolute filesystem paths (POSIX and Windows)
  * build ids (git object ids, UUIDs)
  * host and account names
  * locale-dependent number and date formatting
  * Python container reprs, which leak dict/set iteration order

Two kinds of rule are applied. Pattern rules are fixed regexes. Literal
rules are built at call time from values the caller knows about (the real
host name, the account name, the temporary directory of the run); a literal
match is the strongest possible evidence, because the artefact is quoting
the machine back at you.

Set ordering is NOT detectable by pattern alone. A stable-looking artefact
can still be ordered by a hash that happened not to move. The only honest
test is to move PYTHONHASHSEED and diff; perturb.py does that, and this
module only flags the reprs that make such leakage visible in text.

stdlib only, no network. Importable; also runnable:

    python3 hermeticity.py ARTEFACT [ARTEFACT ...]

Exit 1 if any finding of severity "high" is present, else 0.
"""

import argparse
import getpass
import os
import re
import socket
import sys

__all__ = [
    "Finding",
    "PATTERN_RULES",
    "scan_bytes",
    "scan_file",
    "literal_rules",
    "format_findings",
]

HIGH = "high"
MEDIUM = "medium"
LOW = "low"

_MONTH_EN = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
_DAY_EN = "Mon|Tue|Wed|Thu|Fri|Sat|Sun"

# Month names that only appear when a date was rendered through a locale
# other than C/English. Deliberately a short, unambiguous list: these words
# are not plausible English prose inside an engineering artefact.
_MONTH_NON_EN = (
    "Januar|Februar|M\u00e4rz|Dezember|"
    "janvier|f\u00e9vrier|avril|juillet|ao\u00fbt|d\u00e9cembre|"
    "enero|febrero|marzo|abril|mayo|agosto|diciembre|"
    "gennaio|febbraio|maggio|giugno|luglio|dicembre"
)


class Finding(object):
    """One hermeticity violation located in one artefact."""

    def __init__(self, rule, severity, offset, line, sample, why):
        self.rule = rule
        self.severity = severity
        self.offset = offset
        self.line = line
        self.sample = sample
        self.why = why

    def as_dict(self):
        return {
            "rule": self.rule,
            "severity": self.severity,
            "offset": self.offset,
            "line": self.line,
            "sample": self.sample,
            "why": self.why,
        }

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<Finding %s@%d %r>" % (self.rule, self.offset, self.sample)


def _rule(name, severity, pattern, why, post=None):
    return {
        "name": name,
        "severity": severity,
        "regex": re.compile(pattern),
        "why": why,
        "post": post,
    }


def _looks_like_an_object_id(text):
    """Keep hex blobs that carry both digits and hex letters.

    A length rule alone reports ordinary English ("effaced" is seven
    characters of a-f) and, worse, the digit runs inside real engineering
    numbers: the corpus contains a -6.020599913 dB midpoint and Earth's
    3.986004418e14 gravitational parameter, and both were reported as
    commit ids before this filter existed. The cost is honest and small: a
    seven-character abbreviated object id made only of digits slips past.
    Numbers of that length in the clock range are caught by the epoch rule.
    """
    return (any(c.isdigit() for c in text)
            and any(c in "abcdef" for c in text))


def _plausible_epoch(text):
    """Filter the epoch-second rule down to a believable wall-clock range."""
    try:
        value = int(text)
    except ValueError:  # pragma: no cover - regex guarantees digits
        return False
    if len(text) == 10:
        # 2001-09-09 .. 2065-01-24
        return 1000000000 <= value <= 3000000000
    if len(text) == 13:
        return 1000000000000 <= value <= 3000000000000
    return False


PATTERN_RULES = [
    _rule(
        "timestamp-iso8601",
        HIGH,
        r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}",
        "a rendered wall-clock instant changes on every run",
    ),
    _rule(
        "timestamp-date",
        MEDIUM,
        r"(?<![\d-])(?:19|20)\d{2}-\d{2}-\d{2}(?![\d-])",
        "a calendar date changes when the run crosses midnight or a timezone",
    ),
    _rule(
        "timestamp-ctime",
        HIGH,
        r"\b(?:%s)\s+(?:%s)\s+[ \d]?\d\s+\d{2}:\d{2}:\d{2}\b" % (_DAY_EN, _MONTH_EN),
        "a C-library ctime string is both clock- and locale-dependent",
    ),
    _rule(
        "timestamp-rfc2822",
        HIGH,
        r"\b(?:%s),\s+\d{1,2}\s+(?:%s)\s+\d{4}\b" % (_DAY_EN, _MONTH_EN),
        "an RFC 2822 date changes on every run",
    ),
    _rule(
        "timestamp-epoch",
        MEDIUM,
        r"(?<!\d)\d{10}(?!\d)|(?<!\d)\d{13}(?!\d)",
        "a value in the epoch-second or epoch-millisecond range looks like a clock read",
        post=_plausible_epoch,
    ),
    _rule(
        "abs-path-posix",
        HIGH,
        r"(?<![\w.~-])/(?:Users|home|root|private|var|tmp|opt|Volumes|"
        r"usr/local|Applications|System/Volumes)/[\w./+@-]+",
        "an absolute path pins the artefact to one machine's layout",
    ),
    _rule(
        "abs-path-windows",
        HIGH,
        r"\b[A-Za-z]:\\\\?[\w.\\ +-]{3,}",
        "an absolute Windows path pins the artefact to one machine's layout",
    ),
    _rule(
        "build-id-hex",
        MEDIUM,
        r"(?<![0-9a-zA-Z._-])[0-9a-f]{7,40}(?![0-9a-zA-Z._-])",
        "a hex blob of git-object length is usually a build or commit id",
        post=_looks_like_an_object_id,
    ),
    _rule(
        "uuid",
        HIGH,
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        "a UUID is fresh randomness; it cannot reproduce",
    ),
    _rule(
        "hostname-suffix",
        HIGH,
        r"\b[\w-]{2,}\.(?:local|localdomain|lan|internal|home\.arpa)\b",
        "a host-qualified name pins the artefact to one machine",
    ),
    _rule(
        "pid",
        MEDIUM,
        r"\b(?:pid|PID|process[_ ]id)\b\s*[=:]?\s*\d{2,7}",
        "a process id is fresh on every run",
    ),
    _rule(
        "tempdir-token",
        HIGH,
        r"/var/folders/[\w+-]{2}/[\w+-]{6,}|\b[Tt]mp[\w-]*[/\\][\w-]{6,}",
        "a per-run temporary directory name cannot reproduce",
    ),
    _rule(
        "locale-decimal-comma",
        MEDIUM,
        r"(?<![\w,])\d+,\d+(?![\d,])",
        "a comma between digits is a decimal separator in many locales "
        "and a thousands separator in others",
    ),
    _rule(
        "locale-digit-group-space",
        MEDIUM,
        "\\d[\u00a0\u202f\u2009]\\d{3}\\b",
        "a non-breaking or thin space grouping digits is locale-dependent",
    ),
    _rule(
        "locale-month-name",
        HIGH,
        r"\b(?:%s)\b" % _MONTH_NON_EN,
        "a month name rendered outside the C locale changes with LC_TIME",
    ),
    _rule(
        "python-container-repr",
        HIGH,
        # A double-quoted key alone is just JSON. Require a Python-only
        # literal on the value side, so `{"name":` in minified JSON is not a
        # finding while `{"it's": True}` still is.
        r"dict_keys\(|dict_values\(|dict_items\(|\bset\(\[|\{'[^'\n]{0,80}':"
        r"|\{\"[^\"\n]{0,80}\":\s*(?:True|False|None|')",
        "a Python container repr in an artefact exposes iteration order, "
        "which moves with PYTHONHASHSEED",
    ),
]

_RULES_BY_NAME = dict((r["name"], r) for r in PATTERN_RULES)


def literal_rules(hostname=None, username=None, extra=()):
    """Build rules that look for this machine's own names in an artefact.

    Every argument is optional so a caller can scan an artefact produced
    somewhere else. Empty and very short values are dropped: a one- or
    two-character account name would match ordinary prose.
    """
    rules = []
    seen = set()

    def add(name, value, severity, why):
        if not value:
            return
        value = str(value)
        if len(value) < 3 or value in seen:
            return
        seen.add(value)
        rules.append(_rule(name, severity, re.escape(value), why))

    add("literal-hostname", hostname, HIGH, "the artefact quotes this machine's host name")
    if hostname and "." in str(hostname):
        add(
            "literal-hostname-short",
            str(hostname).split(".")[0],
            HIGH,
            "the artefact quotes this machine's short host name",
        )
    add("literal-username", username, HIGH, "the artefact quotes the account it ran under")
    for value in extra:
        add("literal-env", value, HIGH, "the artefact quotes a value from the run environment")
    return rules


def _line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def scan_bytes(data, rules=None, hostname=None, username=None, extra_literals=(),
               only=None, max_per_rule=8):
    """Return the findings in one artefact's bytes.

    Bytes are decoded as UTF-8 with replacement so that offsets stay close
    to byte offsets for ASCII artefacts, and so a non-UTF-8 artefact still
    scans instead of raising.
    """
    if isinstance(data, bytes):
        text = data.decode("utf-8", "replace")
    else:
        text = data
    all_rules = list(PATTERN_RULES if rules is None else rules)
    if rules is None:
        all_rules += literal_rules(hostname, username, extra_literals)
    if only:
        wanted = set(only)
        all_rules = [r for r in all_rules if r["name"] in wanted]

    findings = []
    for rule in all_rules:
        count = 0
        for match in rule["regex"].finditer(text):
            sample = match.group(0)
            if rule["post"] is not None and not rule["post"](sample):
                continue
            count += 1
            if count > max_per_rule:
                break
            findings.append(
                Finding(
                    rule["name"],
                    rule["severity"],
                    match.start(),
                    _line_of(text, match.start()),
                    sample if len(sample) <= 120 else sample[:117] + "...",
                    rule["why"],
                )
            )
    findings.sort(key=lambda f: (f.offset, f.rule))
    return findings


def scan_file(path, **kwargs):
    with open(path, "rb") as handle:
        return scan_bytes(handle.read(), **kwargs)


def format_findings(label, findings):
    if not findings:
        return "%s: clean (0 findings)" % label
    lines = ["%s: %d finding(s)" % (label, len(findings))]
    for f in findings:
        lines.append(
            "  [%-6s] %-24s line %-5d offset %-7d %r"
            % (f.severity, f.rule, f.line, f.offset, f.sample)
        )
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("artefacts", nargs="+", help="files to scan")
    parser.add_argument("--no-literals", action="store_true",
                        help="skip the host/account literal rules")
    parser.add_argument("--rule", action="append", default=None,
                        help="restrict to one rule name (repeatable)")
    args = parser.parse_args(argv)

    hostname = None if args.no_literals else socket.gethostname()
    try:
        username = None if args.no_literals else getpass.getuser()
    except Exception:  # noqa: BLE001 - getuser raises when no passwd entry
        username = None
    extra = () if args.no_literals else tuple(
        v for v in (os.environ.get("TMPDIR"),) if v
    )

    worst = 0
    for path in args.artefacts:
        findings = scan_file(
            path, hostname=hostname, username=username,
            extra_literals=extra, only=args.rule,
        )
        print(format_findings(path, findings))
        if any(f.severity == HIGH for f in findings):
            worst = 1
    return worst


if __name__ == "__main__":
    sys.exit(main())
