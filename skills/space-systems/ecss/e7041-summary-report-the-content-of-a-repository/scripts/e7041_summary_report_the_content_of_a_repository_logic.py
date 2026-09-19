"""Summary-report the content of a repository (file management service).

Anchor: ECSS-E-ST-70-41C clause 6.23.4.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

What a summary report is. The ground names one repository and the
on-board file management service answers with what that repository
directly holds: each object's name and whether it is a file or a
sub-repository, plus the counts. It is deliberately thinner than an
attribute report -- no per-file lock state, no creation time -- so
that a repository with many objects still fits one reply.

Shallow by construction. A summary names the immediate children and
stops. It does not walk into a sub-repository, so the count it gives
for a parent is the number of objects one level down, never the
number of files in the branch. An operator who reads a summary of a
parent as "the branch holds four things" has been given the right
number to the wrong question; the recursive total needs a walk, and
this module reports the two separately so they cannot be confused.

Bounded like every telemetry report. Past the entry capacity the
report is truncated, and the total object count still has to be
carried, because "8 objects" and "8 of 240 listed" lead to different
commands. The truncation is reported against the entry list only --
the counts are computed over everything the repository holds.

Octet totals. The summary carries the octets held directly, which is
what decides whether the repository can be downlinked in one pass.
The branch total is a different number and this module never lets
one stand in for the other.

Stdlib only, offline, deterministic.
"""

PATH_SEPARATOR = "/"
MAX_NAME_OCTETS = 64
MAX_PATH_OCTETS = 256
DEFAULT_ENTRY_CAPACITY = 20

TYPE_FILE = "file"
TYPE_REPOSITORY = "sub-repository"

OUTCOME_COMPLETE = "summary-complete"
OUTCOME_TRUNCATED = "summary-report-truncated"
OUTCOME_EMPTY = "summary-complete-repository-empty"
FAILURE_UNKNOWN = "failed-repository-not-found"

_FORBIDDEN_NAME_CHARS = (PATH_SEPARATOR, "\\", "\t", "\n", "\r", "\0")


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def validate_segment(name, label="name"):
    """Validate one file or repository name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("%s must be a non-empty string" % label)
    if name != name.strip():
        raise ValueError("%s %r has leading or trailing whitespace" % (label, name))
    for bad in _FORBIDDEN_NAME_CHARS:
        if bad in name:
            raise ValueError("%s %r contains a forbidden character" % (label, name))
    if name in (".", ".."):
        raise ValueError("%s %r is a relative marker, not a name" % (label, name))
    if len(name.encode("utf-8")) > MAX_NAME_OCTETS:
        raise ValueError("%s %r is longer than %d octets" % (label, name, MAX_NAME_OCTETS))
    return name


def split_path(path):
    """Split a repository path into validated segments."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("repository path must be a non-empty string")
    raw = path.split(PATH_SEPARATOR)
    if any(s == "" for s in raw[1:-1]):
        raise ValueError("repository path %r has an empty segment" % (path,))
    segments = [s for s in raw if s != ""]
    if not segments:
        raise ValueError("repository path %r names no repository" % (path,))
    for segment in segments:
        validate_segment(segment, "repository path segment")
    return segments


def normalize_path(path):
    """Normalize a repository path to its canonical form."""
    joined = PATH_SEPARATOR.join(split_path(path))
    if len(joined.encode("utf-8")) > MAX_PATH_OCTETS:
        raise ValueError("repository path %r is longer than %d octets" % (joined, MAX_PATH_OCTETS))
    return joined


def depth_of(path):
    """Depth of a repository path, the root counting as one."""
    return len(split_path(path))


def is_within(candidate, root):
    """Is this path the root itself or a repository beneath it?"""
    candidate_segments = split_path(candidate)
    root_segments = split_path(root)
    if len(candidate_segments) < len(root_segments):
        return False
    return candidate_segments[: len(root_segments)] == root_segments


def validate_tree(tree):
    """Validate a repository tree of path to list of file records."""
    if not isinstance(tree, dict) or not tree:
        raise ValueError("repository tree must be a non-empty mapping")
    normalized = {}
    for path, files in tree.items():
        canonical = normalize_path(path)
        if canonical in normalized:
            raise ValueError("duplicate repository path %r" % (canonical,))
        if not isinstance(files, list):
            raise ValueError("repository %s files must be a list" % canonical)
        records = []
        seen = set()
        for record in files:
            if not isinstance(record, dict):
                raise ValueError("repository %s file record must be a mapping" % canonical)
            name = validate_segment(record.get("name"), "file name")
            if name in seen:
                raise ValueError("repository %s lists file %r twice" % (canonical, name))
            seen.add(name)
            size = _integer("file %s size_octets" % name, record.get("size_octets"), 0)
            records.append({"name": name, "size_octets": size})
        normalized[canonical] = records
    for path in normalized:
        segments = split_path(path)
        if len(segments) > 1:
            parent = PATH_SEPARATOR.join(segments[:-1])
            if parent not in normalized:
                raise ValueError("repository %s has no parent %s in the tree" % (path, parent))
    return normalized


def direct_sub_repositories(tree, path):
    """Immediate sub-repository names, in name order."""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    depth = depth_of(canonical)
    return sorted(
        split_path(p)[-1]
        for p in working
        if is_within(p, canonical) and depth_of(p) == depth + 1
    )


def direct_octets(tree, path):
    """Octets held directly by this repository, sub-repositories excluded."""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    return sum(record["size_octets"] for record in working[canonical])


def branch_octets(tree, path):
    """Octets held by this repository and everything beneath it."""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    total = 0
    for other in working:
        if is_within(other, canonical):
            total += sum(record["size_octets"] for record in working[other])
    return total


def branch_file_count(tree, path):
    """Files held by this repository and everything beneath it."""
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        raise ValueError("repository %r is not in this tree" % (canonical,))
    return sum(len(working[o]) for o in working if is_within(o, canonical))


def summarize_repository(tree, path, entry_capacity=DEFAULT_ENTRY_CAPACITY):
    """Produce the shallow summary report for one repository."""
    _integer("entry_capacity", entry_capacity, 1)
    if not isinstance(tree, dict) or not tree:
        raise ValueError("repository tree must be a non-empty mapping")
    working = validate_tree(tree)
    canonical = normalize_path(path)
    if canonical not in working:
        return {
            "outcome": FAILURE_UNKNOWN,
            "repository_path": canonical,
            "entries": [],
            "object_count": 0,
            "file_count": 0,
            "sub_repository_count": 0,
            "listed_count": 0,
            "omitted_count": 0,
            "direct_octets": 0,
            "branch_octets": 0,
            "branch_file_count": 0,
            "report_is_authoritative": False,
        }
    entries = [
        {"name": record["name"], "type": TYPE_FILE, "size_octets": record["size_octets"]}
        for record in working[canonical]
    ]
    entries += [
        {"name": name, "type": TYPE_REPOSITORY, "size_octets": None}
        for name in direct_sub_repositories(working, canonical)
    ]
    entries.sort(key=lambda entry: (entry["type"], entry["name"]))
    listed = entries[:entry_capacity]
    omitted = len(entries) - len(listed)
    file_count = len(working[canonical])
    sub_count = len(direct_sub_repositories(working, canonical))
    if not entries:
        outcome = OUTCOME_EMPTY
    elif omitted:
        outcome = OUTCOME_TRUNCATED
    else:
        outcome = OUTCOME_COMPLETE
    return {
        "outcome": outcome,
        "repository_path": canonical,
        "entries": listed,
        "object_count": len(entries),
        "file_count": file_count,
        "sub_repository_count": sub_count,
        "listed_count": len(listed),
        "omitted_count": omitted,
        "direct_octets": direct_octets(working, canonical),
        "branch_octets": branch_octets(working, canonical),
        "branch_file_count": branch_file_count(working, canonical),
        "report_is_authoritative": omitted == 0,
    }


def summary_is_shallow(summary):
    """Does this summary describe less than the branch beneath it?"""
    if not isinstance(summary, dict):
        raise ValueError("summary must be a mapping")
    for key in ("file_count", "branch_file_count", "direct_octets", "branch_octets"):
        if key not in summary:
            raise ValueError("summary is missing %r" % (key,))
    return (
        summary["branch_file_count"] > summary["file_count"]
        or summary["branch_octets"] > summary["direct_octets"]
    )


def assess_summary_request(tree, path, entry_capacity=DEFAULT_ENTRY_CAPACITY):
    """Summarize a repository and advise on how the report may be read."""
    summary = summarize_repository(tree, path, entry_capacity)
    advice = []
    if summary["outcome"] == FAILURE_UNKNOWN:
        advice.append("the repository path does not exist; check the addressing")
    if summary["outcome"] == OUTCOME_TRUNCATED:
        advice.append(
            "%d of %d objects were omitted from the listing; the counts still "
            "cover the whole repository"
            % (summary["omitted_count"], summary["object_count"])
        )
    if summary["outcome"] == OUTCOME_EMPTY:
        advice.append("the repository holds nothing and can be deleted as it stands")
    if summary_is_shallow(summary):
        advice.append(
            "this summary is one level deep: the branch holds %d files and %d "
            "octets against the %d and %d listed here"
            % (
                summary["branch_file_count"],
                summary["branch_octets"],
                summary["file_count"],
                summary["direct_octets"],
            )
        )
    summary["advice"] = advice
    summary["deletable_as_is"] = summary["outcome"] == OUTCOME_EMPTY
    return summary
