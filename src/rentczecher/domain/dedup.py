"""Cross-source dedup's result shapes: the score behind one matched pair,
and the outcome of matching a whole batch of listings.

Kept apart from services/dedup.py's matching logic (which depends on the
gazetteer) so callers that only need these types stay free of that
dependency.
"""

import json
from dataclasses import dataclass
from enum import Enum

from rentczecher.domain.listing import Listing


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


def match_score_to_json(score: MatchScore) -> str:
    """A MatchScore as a JSON string, for the audit trail's match-reason column."""
    payload = {
        "total": score.total,
        "band": score.band.value,
        "factors": [
            {
                "name": factor.name,
                "contribution": factor.contribution,
                "evidence": factor.evidence,
            }
            for factor in score.factors
        ],
    }
    return json.dumps(payload)


@dataclass(frozen=True, slots=True)
class MergeDecision:
    """One merged pair, as scored - the original two listing ids, even when
    a later re-parenting moves what they were absorbed into."""

    keeper_id: str
    absorbed_id: str
    score: MatchScore


@dataclass(frozen=True, slots=True)
class UncertainPair:
    listing_id_a: str
    listing_id_b: str
    score: MatchScore


@dataclass(frozen=True, slots=True)
class DedupOutcome:
    survivors: list[Listing]
    merges: tuple[MergeDecision, ...]
    uncertain: tuple[UncertainPair, ...]

    def final_keeper_ids(self) -> dict[str, str]:
        """Absorbed listing id to its chain-final keeper id. When a keeper
        was itself later absorbed, the chain resolves to the listing that
        actually survived."""
        keeper_of = {merge.absorbed_id: merge.keeper_id for merge in self.merges}
        resolved: dict[str, str] = {}
        for absorbed_id, keeper_id in keeper_of.items():
            while keeper_id in keeper_of:
                keeper_id = keeper_of[keeper_id]
            resolved[absorbed_id] = keeper_id
        return resolved
