"""Report the attributes of a file (on-board file management service).

Anchor: ECSS-E-ST-70-41C clause 6.23.4.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the request is. The ground names one file by the repository that
holds it and the name it has inside that repository, and the on-board
file management service answers with what it knows about that file:
how many octets it occupies, whether it is locked against change, and
whether some other on-board activity -- an uplink still writing it, a
downlink still reading it -- currently holds it open.

Why the three failure cases are kept apart. A request can fail because
the repository path names nothing, because the repository exists but
holds no such file, or because the name given as a file is in fact a
sub-repository. Collapsing those into one "not found" is the defect
this module exists to prevent: the first is an addressing mistake on
the ground, the second is usually a file already deleted or never
produced, and the third is an operator asking a directory for a size.
Each sends the operator somewhere different.

What the report is good for. Size decides whether the file fits the
downlink budget for the pass. The lock state and the open-transfer
state together decide whether a delete or an overwrite issued right
now would be accepted, which is the question behind most attribute
requests. Reading is never blocked by either, so a locked file is
still downlinkable; that asymmetry is easy to get backwards.

Stdlib only, offline, deterministic.
"""

PATH_SEPARATOR = "/"
MAX_PATH_OCTETS = 256
MAX_NAME_OCTETS = 64

OUTCOME_REPORTED = "attributes-reported"
FAILURE_REPOSITORY_UNKNOWN = "failed-repository-not-found"
FAILURE_FILE_UNKNOWN = "failed-file-not-found-in-repository"
FAILURE_NAME_IS_A_REPOSITORY = "failed-name-denotes-a-repository"

TRANSFER_IDLE = "idle"
TRANSFER_UPLINK = "uplink-in-progress"
TRANSFER_DOWNLINK = "downlink-in-progress"
VALID_TRANSFER_STATES = (TRANSFER_IDLE, TRANSFER_UPLINK, TRANSFER_DOWNLINK)

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


def validate_object_name(name, label="object name"):
    """Validate one path segment or file name and return it unchanged."""
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
        raise ValueError(
            "%s %r is longer than %d octets" % (label, name, MAX_NAME_OCTETS)
        )
    return name


def normalize_repository_path(path):
    """Normalize a repository path to its canonical separator-joined form."""
    if not isinstance(path, str) or not path.strip():
        raise ValueError("repository path must be a non-empty string")
    segments = [s for s in path.split(PATH_SEPARATOR)]
    if any(s == "" for s in segments[1:-1]):
        raise ValueError("repository path %r has an empty segment" % (path,))
    segments = [s for s in segments if s != ""]
    if not segments:
        raise ValueError("repository path %r names no repository" % (path,))
    for segment in segments:
        validate_object_name(segment, "repository path segment")
    canonical = PATH_SEPARATOR.join(segments)
    if len(canonical.encode("utf-8")) > MAX_PATH_OCTETS:
        raise ValueError(
            "repository path %r is longer than %d octets" % (path, MAX_PATH_OCTETS)
        )
    return canonical


def path_depth(path):
    """Number of segments in a repository path."""
    return len(normalize_repository_path(path).split(PATH_SEPARATOR))


def validate_file_record(record):
    """Validate one stored file record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("file record must be a mapping")
    name = validate_object_name(record.get("name"), "file name")
    size = _integer("file %s size_octets" % name, record.get("size_octets"), 0)
    locked = _flag("file %s locked" % name, record.get("locked", False))
    state = record.get("transfer_state", TRANSFER_IDLE)
    if state not in VALID_TRANSFER_STATES:
        raise ValueError("file %s has unknown transfer state %r" % (name, state))
    created = _integer("file %s creation_time" % name, record.get("creation_time", 0), 0)
    return {
        "name": name,
        "size_octets": size,
        "locked": locked,
        "transfer_state": state,
        "creation_time": created,
    }


def validate_repository(repository):
    """Validate one repository and return a normalized copy."""
    if not isinstance(repository, dict):
        raise ValueError("repository must be a mapping")
    path = normalize_repository_path(repository.get("path"))
    files = repository.get("files", [])
    if not isinstance(files, list):
        raise ValueError("repository %s files must be a list" % path)
    normalized = [validate_file_record(f) for f in files]
    seen = set()
    for record in normalized:
        if record["name"] in seen:
            raise ValueError(
                "repository %s holds two files named %r" % (path, record["name"])
            )
        seen.add(record["name"])
    subs = repository.get("sub_repositories", [])
    if not isinstance(subs, list):
        raise ValueError("repository %s sub_repositories must be a list" % path)
    sub_names = []
    for sub in subs:
        sub_name = validate_object_name(sub, "sub-repository name")
        if sub_name in sub_names:
            raise ValueError("repository %s lists %r twice" % (path, sub_name))
        if sub_name in seen:
            raise ValueError(
                "repository %s uses %r for both a file and a sub-repository"
                % (path, sub_name)
            )
        sub_names.append(sub_name)
    return {"path": path, "files": normalized, "sub_repositories": sub_names}


def build_file_system(repositories):
    """Build a lookup of repository path to repository from a list."""
    if not isinstance(repositories, list) or not repositories:
        raise ValueError("repositories must be a non-empty list")
    table = {}
    for repository in repositories:
        normalized = validate_repository(repository)
        if normalized["path"] in table:
            raise ValueError("duplicate repository path %r" % (normalized["path"],))
        table[normalized["path"]] = normalized
    return table


def find_repository(file_system, repository_path):
    """Return the repository at this path, or None when there is none."""
    if not isinstance(file_system, dict) or not file_system:
        raise ValueError("file system must be a non-empty mapping")
    return file_system.get(normalize_repository_path(repository_path))


def derive_permissions(record):
    """Derive from a validated file record what may be done to it now."""
    held = record["transfer_state"] != TRANSFER_IDLE
    changeable = (not record["locked"]) and (not held)
    return {
        "deletable": changeable,
        "overwritable": changeable,
        "renameable": changeable,
        "readable": True,
        "held_by_transfer": held,
    }


def report_file_attributes(file_system, repository_path, file_name):
    """Answer one attribute request for one named file."""
    path = normalize_repository_path(repository_path)
    name = validate_object_name(file_name, "file name")
    repository = find_repository(file_system, path)
    if repository is None:
        return {
            "outcome": FAILURE_REPOSITORY_UNKNOWN,
            "repository_path": path,
            "file_name": name,
            "attributes": None,
        }
    if name in repository["sub_repositories"]:
        return {
            "outcome": FAILURE_NAME_IS_A_REPOSITORY,
            "repository_path": path,
            "file_name": name,
            "attributes": None,
        }
    for record in repository["files"]:
        if record["name"] == name:
            attributes = dict(record)
            attributes.update(derive_permissions(record))
            attributes["repository_path"] = path
            return {
                "outcome": OUTCOME_REPORTED,
                "repository_path": path,
                "file_name": name,
                "attributes": attributes,
            }
    return {
        "outcome": FAILURE_FILE_UNKNOWN,
        "repository_path": path,
        "file_name": name,
        "attributes": None,
    }


def report_file_attributes_batch(file_system, requests):
    """Answer a list of attribute requests in the order they were given."""
    if not isinstance(requests, list):
        raise ValueError("requests must be a list")
    answers = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("each request must be a mapping")
        answers.append(
            report_file_attributes(
                file_system,
                request.get("repository_path"),
                request.get("file_name"),
            )
        )
    return answers


def downlink_octets(answers):
    """Total octets the successfully reported files would cost to downlink."""
    if not isinstance(answers, list):
        raise ValueError("answers must be a list")
    total = 0
    for answer in answers:
        if answer.get("outcome") == OUTCOME_REPORTED:
            total += answer["attributes"]["size_octets"]
    return total


def assess_attribute_requests(repositories, requests):
    """Run a request set against a file system and summarize the answers."""
    file_system = build_file_system(repositories)
    answers = report_file_attributes_batch(file_system, requests)
    failures = {}
    for answer in answers:
        if answer["outcome"] != OUTCOME_REPORTED:
            failures[answer["outcome"]] = failures.get(answer["outcome"], 0) + 1
    reported = [a for a in answers if a["outcome"] == OUTCOME_REPORTED]
    return {
        "answers": answers,
        "reported_count": len(reported),
        "failed_count": len(answers) - len(reported),
        "failures_by_code": failures,
        "downlink_octets": downlink_octets(answers),
        "locked_count": sum(1 for a in reported if a["attributes"]["locked"]),
        "held_count": sum(
            1 for a in reported if a["attributes"]["held_by_transfer"]
        ),
        "all_reported": not failures,
    }
