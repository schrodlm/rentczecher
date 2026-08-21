"""Cross-source deduplication - detect same property listed on multiple sites.

Each pair of listings is scored on independent evidence factors (GPS
distance, a shared gazetteer-normalized place name, disposition, price,
size). No factor can veto on its own - only the combined score, gated by
an evidence floor, decides a match.
"""

from dataclasses import dataclass
from enum import Enum

from rentczecher.adapters.geocoding.gazetteer import Gazetteer, candidate_names
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.disposition import normalize_disposition
from rentczecher.domain.geo import haversine_m

# Tiers a resolved point or a shared name can land at, most specific first.
# "gps" is a portal-provided point, tied with "street" for the tightest ceiling.
_TIERS_MOST_SPECIFIC_FIRST = ("gps", "street", "municipality_part", "city_district", "municipality")

# GPS factor: weight ceiling and (near, far) distance bounds in meters, keyed
# by the LOOSER of the two points' tiers - a coarse tier earns less trust and
# tolerates more distance before turning negative.
_GPS_CEILING = {
    "gps": 35.0, "street": 35.0,
    "municipality_part": 20.0, "city_district": 10.0, "municipality": 6.0,
}
_GPS_BOUNDS_M = {
    "gps": (100, 1500), "street": (400, 2500),
    "municipality_part": (1200, 5000), "city_district": (3000, 12000),
    "municipality": (5000, 25000),
}

# Shared-name factor: weight by the most specific tier the two listings' place
# names agree on.
_SHARED_NAME_WEIGHT = {
    "street": 30.0,
    "municipality_part": 5.0, "city_district": 5.0,
    "municipality": 2.0,
}

_PRICE_NEAR_WEIGHT = 15.0
_PRICE_NEAR_BOUND = 0.10
_PRICE_FAR_WEIGHT = 25.0
_PRICE_FAR_SPAN = 0.20

_SIZE_NEAR_WEIGHT = 10.0
_SIZE_NEAR_BOUND = 2.0
_SIZE_MID_BOUND = 6.0
_SIZE_FAR_WEIGHT = 15.0
_SIZE_FAR_SPAN = 10.0

_DISPOSITION_AGREE = 15.0
_DISPOSITION_DISAGREE = -35.0

_NO_SHARED_NAME_PENALTY = -8.0

# Both sides name a street and agree on none: two different streets are strong
# evidence of two different properties, and no coarser shared name may mask it.
_STREETS_DISAGREE_PENALTY = -35.0

# Calibrated on owner-labeled real cross-portal pairs; move them only with
# the evidence of scripts/matcher_eval.py, never by feel.
_MATCH_THRESHOLD = 55.0
_UNCERTAIN_THRESHOLD = 30.0

FactorResult = tuple[float, bool]


@dataclass(frozen=True, slots=True)
class FactorContribution:
    name: str
    contribution: float
    evidence: bool

class MatchBand(Enum):
    MATCH = "match"
    UNCERTAIN = "uncertain"
    NO_MATCH = "no_match"


@dataclass(frozen=True, slots=True)
class MatchScore:
    total: float
    factors: tuple[FactorContribution, ...]
    band: MatchBand


def _looser_tier(tier_a: str, tier_b: str) -> str | None:
    """The less specific of two gazetteer tiers, or None when either falls
    outside the scored tiers (the gazetteer's district fallback)."""
    if tier_a not in _TIERS_MOST_SPECIFIC_FIRST or tier_b not in _TIERS_MOST_SPECIFIC_FIRST:
        return None
    return max((tier_a, tier_b), key=_TIERS_MOST_SPECIFIC_FIRST.index)


def _coords_and_tier(listing: Listing) -> tuple[float, float, str]:
    """The listing's own GPS when given (the more precise source), else the
    resolved place's centroid at its tier.

    Callers only reach here once listing.place has been confirmed present.
    """
    if listing.lat is not None and listing.lon is not None:
        return listing.lat, listing.lon, "gps"
    place = listing.place
    assert place is not None
    return place.lat, place.lon, place.tier


def _gps_factor(a: Listing, b: Listing) -> FactorResult:
    if a.place is None or b.place is None:
        return 0.0, False
    lat_a, lon_a, tier_a = _coords_and_tier(a)
    lat_b, lon_b, tier_b = _coords_and_tier(b)
    tier = _looser_tier(tier_a, tier_b)
    if tier is None:
        return 0.0, False
    ceiling = _GPS_CEILING[tier]
    near_m, far_m = _GPS_BOUNDS_M[tier]
    dist = haversine_m(lat_a, lon_a, lat_b, lon_b)
    if dist <= near_m:
        return ceiling, True
    if dist >= far_m:
        return -ceiling, True
    span = far_m - near_m
    fraction = (dist - near_m) / span
    return ceiling - 2 * ceiling * fraction, True


def _shared_name_factor(
    shared_name_tier: str | None, has_names_a: bool, has_names_b: bool, streets_disagree: bool
) -> FactorResult:
    if not has_names_a or not has_names_b:
        return 0.0, False
    if streets_disagree:
        return _STREETS_DISAGREE_PENALTY, True
    if shared_name_tier is None:
        return _NO_SHARED_NAME_PENALTY, True
    return _SHARED_NAME_WEIGHT[shared_name_tier], True


def _disposition_factor(a: Listing, b: Listing) -> FactorResult:
    disp_a = normalize_disposition(a.disposition)
    disp_b = normalize_disposition(b.disposition)
    if disp_a is None or disp_b is None:
        return 0.0, False
    if disp_a == disp_b:
        return _DISPOSITION_AGREE, True
    return _DISPOSITION_DISAGREE, True


def _price_factor(a: Listing, b: Listing) -> FactorResult:
    if not a.price or not b.price:
        return 0.0, False
    diff = abs(a.price - b.price) / max(a.price, b.price)
    if diff <= _PRICE_NEAR_BOUND:
        return _PRICE_NEAR_WEIGHT * (1 - diff / _PRICE_NEAR_BOUND), True
    fraction = min(1.0, (diff - _PRICE_NEAR_BOUND) / _PRICE_FAR_SPAN)
    return -_PRICE_FAR_WEIGHT * fraction, True


def _size_factor(a: Listing, b: Listing) -> FactorResult:
    if not a.size_m2 or not b.size_m2:
        return 0.0, False
    diff = abs(a.size_m2 - b.size_m2)
    if diff <= _SIZE_NEAR_BOUND:
        return _SIZE_NEAR_WEIGHT, True
    if diff <= _SIZE_MID_BOUND:
        span = _SIZE_MID_BOUND - _SIZE_NEAR_BOUND
        return _SIZE_NEAR_WEIGHT * (1 - (diff - _SIZE_NEAR_BOUND) / span), True
    fraction = min(1.0, (diff - _SIZE_MID_BOUND) / _SIZE_FAR_SPAN)
    return -_SIZE_FAR_WEIGHT * fraction, True


def _band(total: float, evidence_floor_met: bool) -> MatchBand:
    if not evidence_floor_met:
        return MatchBand.NO_MATCH
    if total >= _MATCH_THRESHOLD:
        return MatchBand.MATCH
    if total >= _UNCERTAIN_THRESHOLD:
        return MatchBand.UNCERTAIN
    return MatchBand.NO_MATCH


def score_match(
    a: Listing,
    b: Listing,
    shared_name_tier: str | None,
    streets_disagree: bool = False,
) -> MatchScore:
    """Score one pair of listings on independent evidence factors.

    No factor vetoes: a match needs the combined total to clear a band
    threshold, gated by an evidence floor (GPS or a shared place name).
    """
    gps_contribution, gps_evidence = _gps_factor(a, b)
    name_contribution, name_evidence = _shared_name_factor(
        shared_name_tier, bool(a.parsed_place.names), bool(b.parsed_place.names), streets_disagree
    )
    disposition_contribution, disposition_evidence = _disposition_factor(a, b)
    price_contribution, price_evidence = _price_factor(a, b)
    size_contribution, size_evidence = _size_factor(a, b)

    factors = (
        FactorContribution("gps", gps_contribution, gps_evidence),
        FactorContribution("shared_name", name_contribution, name_evidence),
        FactorContribution("disposition", disposition_contribution, disposition_evidence),
        FactorContribution("price", price_contribution, price_evidence),
        FactorContribution("size", size_contribution, size_evidence),
    )
    total = sum(factor.contribution for factor in factors)
    evidence_floor_met = gps_evidence or name_evidence
    return MatchScore(total=total, factors=factors, band=_band(total, evidence_floor_met))


def _listing_name_tiers(
    listing: Listing, names: set[str], gazetteer: Gazetteer
) -> dict[str, str]:
    """Tier of each of the listing's names, asked within its resolved
    municipality - the whole country only when none resolved. A name found
    at several tiers keeps the coarsest one: an ambiguous name must not
    earn a specific name's credit, nor shield against its penalties."""
    muni = listing.place.muni_name if listing.place is not None else None
    tiers: dict[str, str] = {}
    for name in names:
        known = gazetteer.name_tiers(name, muni) & set(_TIERS_MOST_SPECIFIC_FIRST)
        if known:
            tiers[name] = max(known, key=_TIERS_MOST_SPECIFIC_FIRST.index)
    return tiers


def _shared_tier(tiers_a: dict[str, str], tiers_b: dict[str, str]) -> str | None:
    """Most specific tier of any name both listings carry, each shared name
    read at the looser of what the two sides' municipalities say it is."""
    shared = tiers_a.keys() & tiers_b.keys()
    if not shared:
        return None
    tiers = [
        max((tiers_a[name], tiers_b[name]), key=_TIERS_MOST_SPECIFIC_FIRST.index)
        for name in shared
    ]
    return min(tiers, key=_TIERS_MOST_SPECIFIC_FIRST.index)


def _street_names(name_tiers: dict[str, str]) -> set[str]:
    return {name for name, tier in name_tiers.items() if tier == "street"}


def _streets_disagree(street_names_a: set[str], street_names_b: set[str]) -> bool:
    return bool(street_names_a) and bool(street_names_b) and not (street_names_a & street_names_b)


def cross_source_dedup(
    listings: list[Listing], gazetteer: Gazetteer | None = None
) -> list[Listing]:
    """Detect same property listed on multiple sites.

    Listings must already carry their resolved place.

    Uses strict pairwise matching (no transitive grouping).
    For each cross-source pair found, keeps the listing with more data
    and annotates it with the other source.
    """
    if len(listings) < 2:
        return listings
    if gazetteer is None:
        gazetteer = Gazetteer()

    name_sets = [set(candidate_names(listing.parsed_place.names)) for listing in listings]
    tier_maps = [
        _listing_name_tiers(listing, names, gazetteer)
        for listing, names in zip(listings, name_sets, strict=True)
    ]
    street_name_sets = [_street_names(tiers) for tiers in tier_maps]

    # For each listing, track which other listing it's a duplicate of
    # Key: index to remove -> Value: index of the keeper
    remove_to_keeper: dict[int, int] = {}

    for i in range(len(listings)):
        if i in remove_to_keeper:
            continue
        for j in range(i + 1, len(listings)):
            if j in remove_to_keeper:
                continue
            if listings[i].source == listings[j].source:
                continue

            shared_tier = _shared_tier(tier_maps[i], tier_maps[j])
            streets_disagree = _streets_disagree(street_name_sets[i], street_name_sets[j])
            score = score_match(
                listings[i], listings[j], shared_tier, streets_disagree
            )
            # Only confident matches merge. An uncertain pair stays separate:
            # a wrong merge hides a real listing, a missed merge only repeats
            # one - the band survives for the audit trail.
            if score.band is not MatchBand.MATCH:
                continue

            # Determine which to keep (more data = better)
            li, lj = listings[i], listings[j]
            i_score = sum([
                li.lat is not None,
                li.charges is not None,
                li.land_m2 is not None,
                li.size_m2 is not None,
                bool(li.image_url),
            ])
            j_score = sum([
                lj.lat is not None,
                lj.charges is not None,
                lj.land_m2 is not None,
                lj.size_m2 is not None,
                bool(lj.image_url),
            ])

            if i_score >= j_score:
                keeper_idx, remove_idx = i, j
            else:
                keeper_idx, remove_idx = j, i

            remove_to_keeper[remove_idx] = keeper_idx

    # A removed listing can itself have already absorbed others (it was a
    # keeper before a third listing displaced it)
    def _final_keeper(idx: int) -> int:
        while idx in remove_to_keeper:
            idx = remove_to_keeper[idx]
        return idx

    absorbed_sources: dict[int, tuple[str, ...]] = {}
    for remove_idx in remove_to_keeper:
        keeper_idx = _final_keeper(remove_idx)
        removed = listings[remove_idx]
        sources = absorbed_sources.get(keeper_idx, ())
        for source in (removed.source, *removed.cross_source):
            if source != listings[keeper_idx].source and source not in sources:
                sources += (source,)
        absorbed_sources[keeper_idx] = sources

    replacements = {
        keeper_idx: listings[keeper_idx].with_annotations(cross_source=sources)
        for keeper_idx, sources in absorbed_sources.items()
    }

    return [replacements.get(i, l) for i, l in enumerate(listings) if i not in remove_to_keeper]


def _location_evidence(listing: Listing) -> tuple[float, float, str] | None:
    """The listing's own coordinates and their tier - its own GPS when
    given, else its resolved place's centroid and tier - or None when
    neither source has anything to offer."""
    if listing.lat is not None and listing.lon is not None:
        return listing.lat, listing.lon, "gps"
    if listing.place is not None:
        return listing.place.lat, listing.place.lon, listing.place.tier
    return None


def _more_specific_tier(kept_tier: str | None, absorbed_tier: str | None) -> bool:
    """Whether the absorbed listing's tier outranks the kept listing's -
    an untiered side never outranks a tiered one."""
    if absorbed_tier is None or absorbed_tier not in _TIERS_MOST_SPECIFIC_FIRST:
        return False
    if kept_tier is None or kept_tier not in _TIERS_MOST_SPECIFIC_FIRST:
        return True
    return _TIERS_MOST_SPECIFIC_FIRST.index(absorbed_tier) < _TIERS_MOST_SPECIFIC_FIRST.index(kept_tier)


def _record_difference(differences: dict, field: str, canonical: object, listing_value: object) -> None:
    if listing_value is not None and listing_value != canonical:
        differences[field] = {"canonical": canonical, "listing": listing_value}


def _promote_gap_fill(kept: Listing, absorbed: Listing, field: str) -> object:
    kept_value = getattr(kept, field)
    return kept_value if kept_value is not None else getattr(absorbed, field)


def promote_fields(kept: Listing, absorbed: Listing) -> tuple[dict, dict]:
    """Canonical field values for a kept/absorbed pair, and every genuine
    disagreement between them.

    Kept's value wins wherever present; absorbed only fills a gap kept
    left (None or missing). Location and its coordinates promote together,
    by whichever side's place evidence sits at the more specific tier
    (locate()'s own tier ordering), not by source. Nothing here writes to
    a property row yet - the property-row writer arrives later.
    """
    canonical: dict = {}
    differences: dict = {}

    canonical["title"] = kept.title if kept.title else absorbed.title
    _record_difference(differences, "title", canonical["title"], absorbed.title)

    kept_evidence = _location_evidence(kept)
    absorbed_evidence = _location_evidence(absorbed)
    kept_tier = kept_evidence[2] if kept_evidence else None
    absorbed_tier = absorbed_evidence[2] if absorbed_evidence else None
    if _more_specific_tier(kept_tier, absorbed_tier):
        assert absorbed_evidence is not None
        canonical["location"] = absorbed.location
        canonical["lat"] = absorbed_evidence[0]
        canonical["lon"] = absorbed_evidence[1]
    else:
        canonical["location"] = kept.location
        canonical["lat"] = kept_evidence[0] if kept_evidence else None
        canonical["lon"] = kept_evidence[1] if kept_evidence else None
    _record_difference(differences, "location", canonical["location"], absorbed.location)

    canonical_disposition = normalize_disposition(kept.disposition) or normalize_disposition(absorbed.disposition)
    canonical["disposition"] = canonical_disposition
    absorbed_disposition = normalize_disposition(absorbed.disposition)
    _record_difference(differences, "disposition", canonical_disposition, absorbed_disposition)

    for field in ("size_m2", "land_m2"):
        canonical[field] = _promote_gap_fill(kept, absorbed, field)
        _record_difference(differences, field, canonical[field], getattr(absorbed, field))

    return canonical, differences
