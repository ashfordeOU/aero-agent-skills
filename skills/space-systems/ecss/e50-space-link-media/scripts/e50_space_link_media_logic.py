"""Space link media selection and capability assessment.

Anchor: ECSS-E-ST-50C clause 5.6.12.1 -- requirements on the media carrying a
mission's space links. Paraphrased into an implementable procedure; no standard
text is reproduced.

Two normative obligations are implemented:
  (a) every space link names the transmission medium it uses, and that medium
      is one of the media the mission has declared and agreed, so a link can
      never be flown on an unstated or non-interoperable medium;
  (b) the medium named by a link supports what that link must deliver -- its
      required information rate, the range it has to close, and the
      availability the mission asked for -- so an under-capable medium is a
      design-time finding rather than a commissioning surprise.

Arithmetic stays with add, subtract, multiply and divide so the result is
reproducible across platforms, and every comparison against a bound carries a
relative tolerance so a link sized exactly to a medium's envelope comes out the
same way everywhere.
"""

import math

__all__ = [
    "MEDIUM_SUITABLE",
    "MEDIUM_MARGINAL",
    "MEDIUM_UNSUITABLE",
    "REL_TOL",
    "DEFAULT_MARGINAL_UTILISATION",
    "validate_positive",
    "validate_fraction",
    "normalize_medium",
    "normalize_link",
    "assess_link_medium",
    "rank_media_for_link",
    "assess_media_plan",
]

MEDIUM_SUITABLE = "medium-suitable"
MEDIUM_MARGINAL = "medium-marginal"
MEDIUM_UNSUITABLE = "medium-unsuitable"

# Relative tolerance for every bound comparison. A link sized exactly to the
# envelope of its medium must not be rejected by the last bit of a division.
REL_TOL = 1e-9

# Above this utilisation a medium still carries the link, but with no useful
# headroom left for growth, degradation or a revised operations concept.
DEFAULT_MARGINAL_UTILISATION = 0.9


def _validate_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number" % name)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite" % name)
    return number


def validate_positive(value, name="value"):
    """Return a strictly positive magnitude."""
    number = _validate_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def validate_fraction(value, name="fraction"):
    """Return a fraction in the closed interval zero to one."""
    number = _validate_number(value, name)
    if number < 0.0 or number > 1.0:
        raise ValueError(
            "%s must lie between 0 and 1 inclusive, got %r" % (name, value)
        )
    return number


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % name)
    return value.strip()


def normalize_medium(record):
    """Return one declared space link medium as a validated dict.

    A medium is a name plus the envelope it can actually deliver: the highest
    information rate it sustains, the greatest range it closes, and the
    availability it achieves once propagation losses are accounted for.
    """
    if not isinstance(record, dict):
        raise ValueError("medium must be a mapping with name and envelope")
    for key in ("name", "max_rate_bps", "max_range_m", "availability"):
        if key not in record:
            raise ValueError("medium is missing %s" % key)
    interoperable = record.get("interoperable", True)
    if not isinstance(interoperable, bool):
        raise ValueError("medium interoperable flag must be a boolean")
    return {
        "name": _text(record["name"], "medium name"),
        "max_rate_bps": validate_positive(record["max_rate_bps"], "max_rate_bps"),
        "max_range_m": validate_positive(record["max_range_m"], "max_range_m"),
        "availability": validate_fraction(record["availability"], "availability"),
        "interoperable": interoperable,
    }


def normalize_link(record):
    """Return one declared space link as a validated dict."""
    if not isinstance(record, dict):
        raise ValueError("link must be a mapping with name and medium")
    for key in ("name", "medium", "required_rate_bps", "required_range_m"):
        if key not in record:
            raise ValueError("link is missing %s" % key)
    availability = record.get("required_availability", 0.0)
    return {
        "name": _text(record["name"], "link name"),
        "medium": _text(record["medium"], "link medium"),
        "required_rate_bps": validate_positive(
            record["required_rate_bps"], "required_rate_bps"
        ),
        "required_range_m": validate_positive(
            record["required_range_m"], "required_range_m"
        ),
        "required_availability": validate_fraction(
            availability, "required_availability"
        ),
    }


def _normalize_media(media):
    if isinstance(media, dict) or not isinstance(media, (list, tuple)):
        raise ValueError("media must be a list or tuple of medium mappings")
    if not media:
        raise ValueError("media must not be empty")
    catalogue = {}
    for record in media:
        medium = normalize_medium(record)
        if medium["name"] in catalogue:
            raise ValueError("medium %r declared more than once" % medium["name"])
        catalogue[medium["name"]] = medium
    return catalogue


def _normalize_links(links):
    if isinstance(links, dict) or not isinstance(links, (list, tuple)):
        raise ValueError("links must be a list or tuple of link mappings")
    if not links:
        raise ValueError("links must not be empty")
    normalized = []
    seen = set()
    for record in links:
        link = normalize_link(record)
        if link["name"] in seen:
            raise ValueError("link %r declared more than once" % link["name"])
        seen.add(link["name"])
        normalized.append(link)
    return normalized


def assess_link_medium(link, medium, marginal_utilisation=DEFAULT_MARGINAL_UTILISATION):
    """Assess one link against the envelope of the medium it names.

    Returns the per-criterion utilisations, the availability shortfall, and a
    three-way verdict: the medium carries the link with headroom, carries it
    with none worth the name, or cannot carry it at all.
    """
    link = normalize_link(link)
    medium = normalize_medium(medium)
    threshold = validate_fraction(marginal_utilisation, "marginal_utilisation")

    rate_utilisation = link["required_rate_bps"] / medium["max_rate_bps"]
    range_utilisation = link["required_range_m"] / medium["max_range_m"]
    availability_shortfall = link["required_availability"] - medium["availability"]
    worst = max(rate_utilisation, range_utilisation)

    breaches = []
    if rate_utilisation > 1.0 + REL_TOL:
        breaches.append("required rate exceeds what the medium sustains")
    if range_utilisation > 1.0 + REL_TOL:
        breaches.append("required range exceeds what the medium closes")
    if availability_shortfall > REL_TOL:
        breaches.append("required availability exceeds what the medium achieves")

    if breaches:
        verdict = MEDIUM_UNSUITABLE
    elif worst > threshold + REL_TOL:
        verdict = MEDIUM_MARGINAL
    else:
        verdict = MEDIUM_SUITABLE

    return {
        "link": link["name"],
        "medium": medium["name"],
        "rate_utilisation": rate_utilisation,
        "range_utilisation": range_utilisation,
        "worst_utilisation": worst,
        "availability_shortfall": availability_shortfall,
        "interoperable": medium["interoperable"],
        "verdict": verdict,
        "breaches": breaches,
    }


def rank_media_for_link(link, media, marginal_utilisation=DEFAULT_MARGINAL_UTILISATION):
    """Return every medium that could carry this link, most headroom first.

    The link's own declared medium is ignored here on purpose: this answers
    which media are capable, which is the question asked while the medium is
    still being chosen.
    """
    link = normalize_link(link)
    catalogue = _normalize_media(media)
    candidates = []
    for name in sorted(catalogue):
        trial = dict(link)
        trial["medium"] = name
        assessment = assess_link_medium(trial, catalogue[name], marginal_utilisation)
        if assessment["verdict"] != MEDIUM_UNSUITABLE:
            candidates.append(assessment)
    candidates.sort(key=lambda item: (item["worst_utilisation"], item["medium"]))
    return candidates


def assess_media_plan(links, media, marginal_utilisation=DEFAULT_MARGINAL_UTILISATION):
    """Assess a whole set of links against the declared media catalogue.

    Reports the two obligations separately: whether every link names a medium
    the mission actually declared and agreed, and whether that medium supports
    what the link has to deliver.
    """
    normalized_links = _normalize_links(links)
    catalogue = _normalize_media(media)

    assessments = []
    findings = []
    undeclared = []
    non_interoperable = []
    unsuitable = []
    marginal = []
    used = set()

    for link in normalized_links:
        name = link["medium"]
        if name not in catalogue:
            undeclared.append(link["name"])
            assessments.append(
                {
                    "link": link["name"],
                    "medium": name,
                    "verdict": MEDIUM_UNSUITABLE,
                    "breaches": ["medium is not in the declared media catalogue"],
                }
            )
            continue
        used.add(name)
        assessment = assess_link_medium(link, catalogue[name], marginal_utilisation)
        assessments.append(assessment)
        if not assessment["interoperable"]:
            non_interoperable.append(link["name"])
        if assessment["verdict"] == MEDIUM_UNSUITABLE:
            unsuitable.append(link["name"])
        elif assessment["verdict"] == MEDIUM_MARGINAL:
            marginal.append(link["name"])

    unused = sorted(set(catalogue) - used)

    if undeclared:
        findings.append(
            "links name a medium that was never declared: %s" % ", ".join(undeclared)
        )
    if non_interoperable:
        findings.append(
            "links use a medium outside the agreed interoperable set: %s"
            % ", ".join(non_interoperable)
        )
    if unsuitable:
        findings.append(
            "links whose medium cannot carry them: %s" % ", ".join(unsuitable)
        )
    if marginal:
        findings.append(
            "links carried with no useful headroom: %s" % ", ".join(marginal)
        )
    if unused:
        findings.append(
            "media declared but carried no link: %s" % ", ".join(unused)
        )

    compliant = not (undeclared or non_interoperable or unsuitable)

    return {
        "assessments": assessments,
        "undeclared_media_links": undeclared,
        "non_interoperable_links": non_interoperable,
        "unsuitable_links": unsuitable,
        "marginal_links": marginal,
        "unused_media": unused,
        "compliant": compliant,
        "findings": findings,
    }
