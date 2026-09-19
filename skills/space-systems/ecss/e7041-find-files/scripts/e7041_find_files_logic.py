"""Find files in an on-board repository (file management service).

Anchor: ECSS-E-ST-70-41C clause 6.23.4.4 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the request is. The ground names a repository and a search
pattern, and the on-board file management service walks that
repository -- optionally its sub-repositories too -- and reports every
file whose name matches. The answer is a list of repository path plus
file name pairs, not just names, because the same name can exist in
several repositories and a bare name would be useless to act on.

The wildcard. A pattern is a name with two wildcards in it: one that
stands for any run of characters including none, and one that stands
for exactly one character. They match within a name only; neither
crosses a path separator, so a pattern can never widen a search into a
sub-repository by accident -- the recursion flag is the only thing
that does that, and it is a deliberate choice with a cost.

The bounded report. The reply is a telemetry report and telemetry
reports have a size. A search that matches more files than the report
can carry does not silently return the first few: it reports that it
was truncated and how many matched in total, because "12 files match"
and "12 files were reported out of 340" lead to opposite decisions.
An unbounded search on a large repository is the request that produces
that, and narrowing the pattern is the fix, not raising the bound.

Ordering. The result is sorted by repository path then file name, so
two runs of the same search over an unchanged repository produce the
same report and a diff between two passes means something.

Stdlib only, offline, deterministic.
"""

PATH_SEPARATOR = "/"
WILDCARD_ANY = "*"
WILDCARD_ONE = "?"
MAX_NAME_OCTETS = 64
MAX_PATH_OCTETS = 256
DEFAULT_REPORT_CAPACITY = 32

OUTCOME_COMPLETE = "search-complete"
OUTCOME_TRUNCATED = "search-report-truncated"
OUTCOME_NO_MATCH = "search-complete-no-match"
FAILURE_REPOSITORY_UNKNOWN = "failed-repository-not-found"

_FORBIDDEN_NAME_CHARS = (PATH_SEPARATOR, "\\", "\t", "\n", "\r", "\0")


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def validate_name(name, label="file name"):
    """Validate a literal file or repository segment name."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("%s must be a non-empty string" % label)
    for bad in _FORBIDDEN_NAME_CHARS:
        if bad in name:
            raise ValueError("%s %r contains a forbidden character" % (label, name))
    if WILDCARD_ANY in name or WILDCARD_ONE in name:
        raise ValueError("%s %r contains a wildcard; a stored name is literal" % (label, name))
    if name in (".", ".."):
        raise ValueError("%s %r is a relative marker, not a name" % (label, name))
    if len(name.encode("utf-8")) > MAX_NAME_OCTETS:
        raise ValueError("%s %r is longer than %d octets" % (label, name, MAX_NAME_OCTETS))
    return name


def normalize_repository_path(path):
    """Normalize a repository path to its canonical separator-joined form."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("repository path must be a non-empty string")
    raw = path.split(PATH_SEPARATOR)
    if any(s == "" for s in raw[1:-1]):
        raise ValueError("repository path %r has an empty segment" % (path,))
    segments = [s for s in raw if s != ""]
    if not segments:
        raise ValueError("repository path %r names no repository" % (path,))
    for segment in segments:
        validate_name(segment, "repository path segment")
    canonical = PATH_SEPARATOR.join(segments)
    if len(canonical.encode("utf-8")) > MAX_PATH_OCTETS:
        raise ValueError("repository path %r is longer than %d octets" % (path, MAX_PATH_OCTETS))
    return canonical


def validate_pattern(pattern):
    """Validate a search pattern: a name that may carry the two wildcards."""
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("search pattern must be a non-empty string")
    if PATH_SEPARATOR in pattern:
        raise ValueError(
            "search pattern %r crosses a path separator; a pattern matches a "
            "name, and only the recursion flag reaches a sub-repository" % (pattern,)
        )
    for bad in ("\\", "\t", "\n", "\r", "\0"):
        if bad in pattern:
            raise ValueError("search pattern %r contains a forbidden character" % (pattern,))
    if len(pattern.encode("utf-8")) > MAX_NAME_OCTETS:
        raise ValueError(
            "search pattern %r is longer than the %d octet name cap"
            % (pattern, MAX_NAME_OCTETS)
        )
    return pattern


def pattern_matches(pattern, name):
    """Does a wildcard pattern match a literal file name?

    Iterative backtracking matcher: the any-run wildcard remembers the
    last position it could have consumed one more character from, so a
    pattern with several of them still runs in linear time over the
    name rather than exploding combinatorially.
    """
    validate_pattern(pattern)
    if not isinstance(name, str) or name == "":
        raise ValueError("name to match must be a non-empty string")
    p = n = 0
    star = -1
    resume = 0
    while n < len(name):
        if p < len(pattern) and pattern[p] == WILDCARD_ONE:
            p += 1
            n += 1
        elif p < len(pattern) and pattern[p] == WILDCARD_ANY:
            star = p
            resume = n
            p += 1
        elif p < len(pattern) and pattern[p] == name[n]:
            p += 1
            n += 1
        elif star >= 0:
            p = star + 1
            resume += 1
            n = resume
        else:
            return False
    while p < len(pattern) and pattern[p] == WILDCARD_ANY:
        p += 1
    return p == len(pattern)


def pattern_is_unbounded(pattern):
    """Is this a pattern that matches every name in the repository?"""
    validate_pattern(pattern)
    return set(pattern) == {WILDCARD_ANY}


def validate_repository(repository):
    """Validate one repository and return a normalized copy."""
    if not isinstance(repository, dict):
        raise ValueError("repository must be a mapping")
    path = normalize_repository_path(repository.get("path"))
    files = repository.get("files", [])
    if not isinstance(files, list):
        raise ValueError("repository %s files must be a list" % path)
    names = []
    for name in files:
        validated = validate_name(name)
        if validated in names:
            raise ValueError("repository %s lists file %r twice" % (path, validated))
        names.append(validated)
    return {"path": path, "files": names}


def build_file_system(repositories):
    """Build a canonical path-to-repository table."""
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("repositories must be a non-empty list")
    table = {}
    for repository in repositories:
        normalized = validate_repository(repository)
        if normalized["path"] in table:
            raise ValueError("duplicate repository path %r" % (normalized["path"],))
        table[normalized["path"]] = normalized
    return table


def is_under(candidate_path, root_path):
    """Is this repository path the root itself or a repository beneath it?"""
    root = normalize_repository_path(root_path)
    candidate = normalize_repository_path(candidate_path)
    return candidate == root or candidate.startswith(root + PATH_SEPARATOR)


def repositories_in_scope(file_system, root_path, recursive):
    """Canonical paths the search will walk, in deterministic order."""
    if not isinstance(file_system, dict) or not file_system:
        raise ValueError("file system must be a non-empty mapping")
    root = normalize_repository_path(root_path)
    _flag("recursive", recursive)
    if root not in file_system:
        raise ValueError("repository %r is not in this file system" % (root,))
    if not recursive:
        return [root]
    return sorted(p for p in file_system if is_under(p, root))


def find_files(
    file_system,
    root_path,
    pattern,
    recursive=False,
    report_capacity=DEFAULT_REPORT_CAPACITY,
):
    """Search a repository for files matching a pattern; bounded report."""
    root = normalize_repository_path(root_path)
    validate_pattern(pattern)
    _flag("recursive", recursive)
    _integer("report_capacity", report_capacity, 1)
    if not isinstance(file_system, dict) or not file_system:
        raise ValueError("file system must be a non-empty mapping")
    if root not in file_system:
        return {
            "outcome": FAILURE_REPOSITORY_UNKNOWN,
            "root_path": root,
            "pattern": pattern,
            "recursive": recursive,
            "entries": [],
            "match_count": 0,
            "reported_count": 0,
            "omitted_count": 0,
            "repositories_searched": 0,
        }
    scope = repositories_in_scope(file_system, root, recursive)
    matches = []
    for path in scope:
        for name in sorted(file_system[path]["files"]):
            if pattern_matches(pattern, name):
                matches.append({"repository_path": path, "file_name": name})
    matches.sort(key=lambda entry: (entry["repository_path"], entry["file_name"]))
    reported = matches[:report_capacity]
    omitted = len(matches) - len(reported)
    if not matches:
        outcome = OUTCOME_NO_MATCH
    elif omitted:
        outcome = OUTCOME_TRUNCATED
    else:
        outcome = OUTCOME_COMPLETE
    return {
        "outcome": outcome,
        "root_path": root,
        "pattern": pattern,
        "recursive": recursive,
        "entries": reported,
        "match_count": len(matches),
        "reported_count": len(reported),
        "omitted_count": omitted,
        "repositories_searched": len(scope),
    }


def assess_search_request(repositories, request):
    """Run one search request against a file system and advise on it."""
    file_system = build_file_system(repositories)
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    result = find_files(
        file_system,
        request.get("root_path"),
        request.get("pattern"),
        request.get("recursive", False),
        request.get("report_capacity", DEFAULT_REPORT_CAPACITY),
    )
    advice = []
    if result["outcome"] == FAILURE_REPOSITORY_UNKNOWN:
        advice.append("the root repository path does not exist; check the addressing")
    if result["outcome"] == OUTCOME_TRUNCATED:
        advice.append(
            "narrow the pattern or search a sub-repository; %d of %d matches were "
            "omitted from the report" % (result["omitted_count"], result["match_count"])
        )
        if pattern_is_unbounded(result["pattern"]):
            advice.append(
                "the pattern matches every name, so the search was never narrowed"
            )
    if result["outcome"] == OUTCOME_NO_MATCH:
        advice.append(
            "no file matched; confirm the pattern and whether the search had to recurse"
        )
    result["advice"] = advice
    result["report_is_authoritative"] = result["omitted_count"] == 0
    return result
