"""Evaluate the dedup matcher against owner-labeled listing pairs.

Shows how the current matcher performs against already reviewed pairs.
Only the saved facts and verdicts are replayed, so a review outlives the
listings themselves. Run this before and after any change to the
matcher's weights or thresholds.

Run: uv run python scripts/matcher_eval.py --data ~/dev/rentczecher-planning/matcher-eval

The data directory lives outside the repo and holds:

  snapshot-*.json   pair records with listing facts under "a" and "b"
  labels.json       {"<id>|<id>": "same" | "different"}

Reports how the verdicts fell per band, plus every misclassified pair
with its factor arithmetic.
"""

import argparse
import json
from pathlib import Path

from rentczecher.adapters.geocoding.gazetteer import Gazetteer, candidate_names
from rentczecher.domain.listing import Listing, ListingAnnotations, ScrapedListing
from rentczecher.domain.location import ParsedPlace
from rentczecher.services.dedup import (
    MatchBand,
    MatchScore,
    _listing_name_tiers,
    _shared_tier,
    _street_names,
    _streets_disagree,
    score_match,
)
from rentczecher.services.locate import locate_listings


def _rebuild(side: dict) -> Listing:
    scraped = ScrapedListing(
        id=side["id"],
        source=side["source"],
        title=side["title"],
        price=side["price"],
        location=side["location"],
        url=side["url"],
        image_url=side["image_url"],
        size_m2=side["size_m2"],
        disposition=side["disposition"],
        lat=side["lat"],
        lon=side["lon"],
        parsed_place=ParsedPlace(names=tuple(side["parsed_names"])),
    )
    return Listing(scraped=scraped, annotations=ListingAnnotations())


def load_sides(data_dir: Path) -> dict[str, dict]:
    sides: dict[str, dict] = {}
    for snapshot_path in sorted(data_dir.glob("snapshot-*.json")):
        for pair in json.loads(snapshot_path.read_text()):
            for side in (pair["a"], pair["b"]):
                sides[side["id"]] = side
    return sides


def score_labeled_pairs(
    labels: dict[str, str], sides: dict[str, dict], gazetteer: Gazetteer
) -> list[tuple[str, str, MatchScore]]:
    """(pair key, label, score) for every labeled pair present in a snapshot."""
    listing_ids = list(sides)
    located = locate_listings([_rebuild(sides[lid]) for lid in listing_ids], gazetteer)
    listings = dict(zip(listing_ids, located, strict=True))
    name_sets = {lid: set(candidate_names(l.parsed_place.names)) for lid, l in listings.items()}
    tier_maps = {
        lid: _listing_name_tiers(l, name_sets[lid], gazetteer) for lid, l in listings.items()
    }

    results = []
    for key, label in sorted(labels.items()):
        id_a, id_b = key.split("|")
        if id_a not in listings or id_b not in listings:
            print(f"skipping {key}: not in any snapshot")
            continue
        score = score_match(
            listings[id_a],
            listings[id_b],
            _shared_tier(tier_maps[id_a], tier_maps[id_b]),
            _streets_disagree(_street_names(tier_maps[id_a]), _street_names(tier_maps[id_b])),
        )
        results.append((key, label, score))
    return results


def report(results: list[tuple[str, str, MatchScore]]) -> None:
    for band in MatchBand:
        in_band = [(key, label, score) for key, label, score in results if score.band is band]
        same = sum(1 for _, label, _ in in_band if label == "same")
        print(f"{band.value:<9} {len(in_band):>3} pairs: {same} same, {len(in_band) - same} different")

    misclassified = [
        (key, label, score)
        for key, label, score in results
        if (label == "same") != (score.band is MatchBand.MATCH)
    ]
    print(f"\n{len(misclassified)} pairs outside the ideal (same <=> match) split:")
    for key, label, score in sorted(misclassified, key=lambda r: -r[2].total):
        factors = ", ".join(
            f"{f.name} {f.contribution:+.1f}" for f in score.factors if f.evidence
        )
        print(f"  {score.total:>6.1f} {score.band.value:<9} labeled {label:<9} {key}")
        print(f"         {factors}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True,
                        help="directory with snapshot-*.json and labels.json")
    args = parser.parse_args()

    labels = json.loads((args.data / "labels.json").read_text())
    sides = load_sides(args.data)
    results = score_labeled_pairs(labels, sides, Gazetteer())
    report(results)


if __name__ == "__main__":
    main()
