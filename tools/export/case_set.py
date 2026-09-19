#!/usr/bin/env python3
"""The case-set file format for the router evidence bundle.

A case set is a JSON Lines file: one JSON object per line, UTF-8, LF endings,
no trailing comma, no enclosing array. Every object has these fields.

    uid             str   unique within the file. "<source stem>:<case_id>".
                          Case ids are unique inside one source file but NOT
                          across files, which is why the uid carries both.
    case_id         str   the id as written in the source file.
    query           str   the natural-language task given to the router.
    expected_skill  str   the skill path the router must return as rank 1,
                          relative to the skills root (e.g.
                          "avionics/do178c/development").
    intent          str   why this case exists. Commentary: the runner never
                          reads it, it is here so a reviewer can judge whether
                          the case is fair.
    source          str   repository-relative path of the file it came from.
    gated           bool  true when the repository's own hit1 gate executes
                          this case; false when it does not. See README.md --
                          this distinction is the point of the bundle.

Two hashes are recorded for each case set in manifest.json:

    sha256_file     the bytes of the .jsonl file, so a reviewer can tell the
                    file apart from any edited copy;
    sha256_cases    a canonical digest over (uid, query, expected_skill) of
                    every case, sorted by uid. This is the assertion content:
                    it ignores line order and ignores commentary, so it stays
                    stable under reformatting and changes the moment a query
                    or an expected answer changes.
"""

import hashlib
import json

FIELDS = ("uid", "case_id", "query", "expected_skill", "intent", "source", "gated")


def dump_cases(records, path):
    """Write records as JSON Lines, sorted by uid, with stable key order."""
    ordered = sorted(records, key=lambda r: r["uid"])
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in ordered:
            row = {key: record[key] for key in FIELDS}
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    return ordered


def load_cases(path):
    """Read a case-set file. Raises ValueError on a malformed record."""
    records = []
    seen = set()
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise ValueError("%s line %d is not JSON: %s" % (path, line_no, exc))
            for field in ("uid", "query", "expected_skill"):
                if not isinstance(record.get(field), str) or not record[field]:
                    raise ValueError("%s line %d: missing or empty %r"
                                     % (path, line_no, field))
            if record["uid"] in seen:
                raise ValueError("%s line %d: duplicate uid %r"
                                 % (path, line_no, record["uid"]))
            seen.add(record["uid"])
            records.append(record)
    if not records:
        raise ValueError("%s contains no cases" % path)
    return records


def cases_digest(records):
    """Canonical digest over the assertion content of a case set."""
    sha = hashlib.sha256()
    for record in sorted(records, key=lambda r: r["uid"]):
        sha.update(record["uid"].encode("utf-8"))
        sha.update(b"\x00")
        sha.update(record["query"].encode("utf-8"))
        sha.update(b"\x00")
        sha.update(record["expected_skill"].encode("utf-8"))
        sha.update(b"\n")
    return sha.hexdigest()


def file_digest(path):
    """sha256 of the raw bytes of a file."""
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()
