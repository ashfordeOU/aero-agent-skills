"""On-board file systems: the model everything else is addressed against.

Anchor: ECSS-E-ST-70-41C clause 6.23.5.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

Only two normative items sit here, and they are the two that every
other request in the file management service depends on: what a file
system is, and how an object in it is named.

The model. A file system is a set of repositories. A repository holds
files and, if the file system is hierarchical, sub-repositories. A
file is addressed by two things -- the path of the repository holding
it and its name inside that repository -- never by name alone, because
the same name in two repositories is two different files.

Flat or hierarchical. A flat file system has repositories at one
level and no sub-repositories; every path is a single segment. A
hierarchical one nests them to a declared maximum depth. The choice
is a property of the on-board implementation, not of the request, so
a ground tool that assumes hierarchy against a flat system builds
paths that can never resolve.

Why a declaration is worth validating on its own. Every later request
inherits these limits: the separator, the name charset, the name and
path octet caps, the depth, and whether names differ by case. A
declaration that contradicts itself -- flat but a depth above one,
hierarchical but a depth of one, a separator inside the permitted name
charset -- produces paths that are legal by one rule and illegal by
another, and the contradiction surfaces much later as an addressing
failure nobody can reproduce.

Case is the quiet one. A file system that does not distinguish case
holds one object where a case-sensitive ground model holds two, so a
create that the ground thinks is new silently overwrites.

Stdlib only, offline, deterministic.
"""

KIND_FLAT = "flat"
KIND_HIERARCHICAL = "hierarchical"
VALID_KINDS = (KIND_FLAT, KIND_HIERARCHICAL)

DEFAULT_SEPARATOR = "/"
DEFAULT_MAX_NAME_OCTETS = 64
DEFAULT_MAX_PATH_OCTETS = 256
DEFAULT_MAX_DEPTH = 8

OBJECT_FILE = "file"
OBJECT_REPOSITORY = "repository"

FINDING_DEPTH_CONTRADICTS_KIND = "declared-depth-contradicts-declared-kind"
FINDING_SEPARATOR_IN_CHARSET = "separator-is-inside-the-permitted-name-charset"
FINDING_PATH_CAP_BELOW_NAME_CAP = "path-octet-cap-below-the-name-octet-cap"
FINDING_PATH_CAP_UNREACHABLE_DEPTH = "declared-depth-unreachable-within-the-path-cap"
FINDING_CASE_INSENSITIVE = "case-insensitive-names-collide-across-spellings"

RESOLVED = "object-identifier-resolved"
REJECTED_DEPTH = "rejected-path-deeper-than-declared"
REJECTED_SUB_REPOSITORY = "rejected-flat-file-system-has-no-sub-repositories"
REJECTED_NAME_OCTETS = "rejected-name-over-the-octet-cap"
REJECTED_PATH_OCTETS = "rejected-path-over-the-octet-cap"
REJECTED_CHARSET = "rejected-name-outside-the-permitted-charset"

_CONTROL_CHARS = ("\t", "\n", "\r", "\0")


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


def validate_declaration(declaration):
    """Validate one on-board file system declaration and normalize it."""
    if not isinstance(declaration, dict):
        raise ValueError("file system declaration must be a mapping")
    kind = declaration.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(
            "file system kind %r is unknown (expected one of %s)"
            % (kind, ", ".join(VALID_KINDS))
        )
    separator = declaration.get("separator", DEFAULT_SEPARATOR)
    if not isinstance(separator, str) or len(separator) != 1:
        raise ValueError("separator must be exactly one character, got %r" % (separator,))
    if separator in _CONTROL_CHARS:
        raise ValueError("separator %r is a control character" % (separator,))
    max_depth = _integer("max_depth", declaration.get("max_depth", DEFAULT_MAX_DEPTH), 1)
    max_name = _integer(
        "max_name_octets", declaration.get("max_name_octets", DEFAULT_MAX_NAME_OCTETS), 1
    )
    max_path = _integer(
        "max_path_octets", declaration.get("max_path_octets", DEFAULT_MAX_PATH_OCTETS), 1
    )
    charset = declaration.get("permitted_name_characters")
    if charset is not None:
        if not isinstance(charset, str) or not charset:
            raise ValueError("permitted_name_characters must be a non-empty string")
    case_sensitive = _flag(
        "case_sensitive_names", declaration.get("case_sensitive_names", True)
    )
    return {
        "kind": kind,
        "separator": separator,
        "max_depth": max_depth,
        "max_name_octets": max_name,
        "max_path_octets": max_path,
        "permitted_name_characters": charset,
        "case_sensitive_names": case_sensitive,
    }


def supports_sub_repositories(declaration):
    """Can this file system hold a repository inside a repository?"""
    return validate_declaration(declaration)["kind"] == KIND_HIERARCHICAL


def effective_max_depth(declaration):
    """Depth this file system can actually reach, kind taken into account."""
    decl = validate_declaration(declaration)
    if decl["kind"] == KIND_FLAT:
        return 1
    return decl["max_depth"]


def audit_declaration(declaration):
    """Audit a declaration for limits that contradict each other."""
    decl = validate_declaration(declaration)
    findings = []
    if decl["kind"] == KIND_FLAT and decl["max_depth"] > 1:
        findings.append(FINDING_DEPTH_CONTRADICTS_KIND)
    if decl["kind"] == KIND_HIERARCHICAL and decl["max_depth"] == 1:
        findings.append(FINDING_DEPTH_CONTRADICTS_KIND)
    charset = decl["permitted_name_characters"]
    if charset is not None and decl["separator"] in charset:
        findings.append(FINDING_SEPARATOR_IN_CHARSET)
    if decl["max_path_octets"] < decl["max_name_octets"]:
        findings.append(FINDING_PATH_CAP_BELOW_NAME_CAP)
    depth = effective_max_depth(decl)
    # The shortest path that reaches the declared depth is one octet per
    # segment plus the separators between them. Integer arithmetic only,
    # so this comparison is exact on every platform.
    shortest_deepest_path = depth + (depth - 1)
    if shortest_deepest_path > decl["max_path_octets"]:
        findings.append(FINDING_PATH_CAP_UNREACHABLE_DEPTH)
    if not decl["case_sensitive_names"]:
        findings.append(FINDING_CASE_INSENSITIVE)
    return {
        "declaration": decl,
        "findings": findings,
        "finding_count": len(findings),
        "coherent": not findings,
        "effective_max_depth": depth,
        "supports_sub_repositories": decl["kind"] == KIND_HIERARCHICAL,
    }


def validate_name(declaration, name):
    """Validate one name against the declared charset and octet cap."""
    decl = validate_declaration(declaration)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if name != name.strip():
        raise ValueError("name %r has leading or trailing whitespace" % (name,))
    if name in (".", ".."):
        raise ValueError("name %r is a relative marker, not a name" % (name,))
    for bad in _CONTROL_CHARS:
        if bad in name:
            raise ValueError("name %r contains a control character" % (name,))
    if decl["separator"] in name:
        raise ValueError("name %r contains the path separator" % (name,))
    return name


def canonical_name(declaration, name):
    """The form in which this file system compares two names."""
    decl = validate_declaration(declaration)
    validated = validate_name(decl, name)
    return validated if decl["case_sensitive_names"] else validated.upper()


def names_collide(declaration, first, second):
    """Would this file system treat these two names as one object?"""
    return canonical_name(declaration, first) == canonical_name(declaration, second)


def split_path(declaration, path):
    """Split a repository path into segments using the declared separator."""
    decl = validate_declaration(declaration)
    if not isinstance(path, str) or not path.strip():
        raise ValueError("repository path must be a non-empty string")
    raw = path.split(decl["separator"])
    if any(s == "" for s in raw[1:-1]):
        raise ValueError("repository path %r has an empty segment" % (path,))
    segments = [s for s in raw if s != ""]
    if not segments:
        raise ValueError("repository path %r names no repository" % (path,))
    for segment in segments:
        validate_name(decl, segment)
    return segments


def join_path(declaration, segments):
    """Join segments into a path using the declared separator."""
    decl = validate_declaration(declaration)
    if not isinstance(segments, (list, tuple)) or not segments:
        raise ValueError("segments must be a non-empty list")
    for segment in segments:
        validate_name(decl, segment)
    return decl["separator"].join(segments)


def _over_cap(text, cap):
    return len(text.encode("utf-8")) > cap


def resolve_object_identifier(declaration, repository_path, file_name=None):
    """Resolve a repository path, optionally plus a file name, to one object."""
    decl = validate_declaration(declaration)
    segments = split_path(decl, repository_path)
    path = join_path(decl, segments)
    depth = len(segments)
    object_type = OBJECT_REPOSITORY if file_name is None else OBJECT_FILE
    name = None if file_name is None else validate_name(decl, file_name)

    def rejection(reason, detail):
        return {
            "outcome": reason,
            "object_type": object_type,
            "repository_path": path,
            "file_name": name,
            "depth": depth,
            "identifier": None,
            "detail": detail,
        }

    if decl["kind"] == KIND_FLAT and depth > 1:
        return rejection(REJECTED_SUB_REPOSITORY, depth)
    if depth > effective_max_depth(decl):
        return rejection(REJECTED_DEPTH, depth)
    for segment in segments:
        if _over_cap(segment, decl["max_name_octets"]):
            return rejection(REJECTED_NAME_OCTETS, segment)
    if name is not None and _over_cap(name, decl["max_name_octets"]):
        return rejection(REJECTED_NAME_OCTETS, name)
    if _over_cap(path, decl["max_path_octets"]):
        return rejection(REJECTED_PATH_OCTETS, len(path.encode("utf-8")))
    charset = decl["permitted_name_characters"]
    if charset is not None:
        for candidate in list(segments) + ([name] if name is not None else []):
            for character in candidate:
                if character not in charset:
                    return rejection(REJECTED_CHARSET, candidate)
    identifier = {
        "repository_path": join_path(
            decl, [canonical_name(decl, s) for s in segments]
        ),
        "file_name": None if name is None else canonical_name(decl, name),
    }
    return {
        "outcome": RESOLVED,
        "object_type": object_type,
        "repository_path": path,
        "file_name": name,
        "depth": depth,
        "identifier": identifier,
        "detail": None,
    }


def assess_file_system(declaration, objects):
    """Audit a declaration and resolve a set of objects against it."""
    audit = audit_declaration(declaration)
    if not isinstance(objects, list):
        raise ValueError("objects must be a list")
    results = []
    for item in objects:
        if not isinstance(item, dict):
            raise ValueError("each object must be a mapping")
        results.append(
            resolve_object_identifier(
                declaration, item.get("repository_path"), item.get("file_name")
            )
        )
    rejected = [r for r in results if r["outcome"] != RESOLVED]
    grouped = {}
    for result in rejected:
        grouped[result["outcome"]] = grouped.get(result["outcome"], 0) + 1
    canonical_ids = [
        (r["identifier"]["repository_path"], r["identifier"]["file_name"])
        for r in results
        if r["outcome"] == RESOLVED
    ]
    return {
        "audit": audit,
        "results": results,
        "resolved_count": len(results) - len(rejected),
        "rejected_count": len(rejected),
        "rejections_by_reason": grouped,
        "distinct_object_count": len(set(canonical_ids)),
        "aliased_object_count": len(canonical_ids) - len(set(canonical_ids)),
        "all_resolved": not rejected,
    }
