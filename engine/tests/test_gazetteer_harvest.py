"""Tests for the portal harvest: each portal's parser against page snippets
shaped like the live sites, and the join of portal places to the official
ones against a small gazetteer."""

import json
import sqlite3
from dataclasses import dataclass, field

import pytest

from scripts.gazetteer.database import GazetteerDatabase
from scripts.gazetteer.harvest import harvest_portals
from scripts.gazetteer.model import Kraj, Obec, Obvod, Okres, Position
from scripts.gazetteer.portals import bezrealitky
from scripts.gazetteer.portals.bezrealitky import heading_names, parse_bundle, parse_regions
from scripts.gazetteer.portals.portal import MatchedDistrict, MatchedRegion, PortalPlaces, add_unique
from scripts.gazetteer.portals.remax import RemaxDistrict, parse_search_form
from scripts.gazetteer.portals.sreality import parse_search_page

_HERE = Position(50.0, 14.0)


def _facets(regions: list[dict], districts: list[dict]) -> str:
    """Two facets as Sreality's search page embeds them in its hydration data."""
    return (f'<script>..."idName":"locality_region_id","values":{json.dumps(regions)},"x":1...'
            f'"idName":"locality_district_id","values":{json.dumps(districts)},"y":2...</script>')


class TestSreality:
    def test_reads_regions_and_districts_from_the_facets(self):
        html = _facets([{"id": 2, "name": "Plzeňský kraj"}], [{"id": 8, "name": "Domažlice", "regionId": 2}])
        assert parse_search_page(html) == PortalPlaces(regions={"Plzeňský kraj": 2}, districts={"Domažlice": 8})

    def test_a_facet_streamed_twice_must_agree_with_itself(self):
        """A facet repeated with different values cannot be trusted."""
        html = (_facets([{"id": 2, "name": "Plzeňský kraj"}], [{"id": 8, "name": "Domažlice"}])
                + _facets([{"id": 3, "name": "Plzeňský kraj"}], [{"id": 8, "name": "Domažlice"}]))
        with pytest.raises(SystemExit, match="differing values"):
            parse_search_page(html)

    def test_a_page_without_the_facets_is_refused(self):
        with pytest.raises(SystemExit, match="has its shape changed"):
            parse_search_page("<html></html>")


_REMAX_FORM = """
<h4>Plzeňský</h4>
<input name="regions[43][3401]" type="checkbox"><label for="x">Domažlice</label>
<h4>Praha</h4>
<input name="regions[19][19]" type="checkbox"><label for="y">Praha 1</label>
<input name="regions[19][78]" type="checkbox"><label for="z">Praha 7</label>
<input name="regions[19][78]" type="checkbox"><label for="z">Praha 7</label>
"""


class TestRemax:
    def test_reads_each_district_as_its_region_and_district_pair(self):
        places = parse_search_form(_REMAX_FORM)
        assert places.regions == {"Plzeňský kraj": 43, "Hlavní město Praha": 19}
        assert places.districts["Domažlice"] == RemaxDistrict(region_id=43, district_id=3401)

    def test_a_district_listed_twice_with_the_same_ids_is_kept_once(self):
        """RE/MAX's form repeats some districts verbatim."""
        assert parse_search_form(_REMAX_FORM).districts["Praha 7"] == RemaxDistrict(region_id=19, district_id=78)

    def test_the_vysocina_heading_reads_as_kraj_vysocina(self):
        """The form's 'Vysočina' heading leaves out the 'Kraj' of the official name."""
        form = ('<h4>Vysočina</h4><input name="regions[63][3707]" type="checkbox">'
                '<label for="x">Jihlava</label>')
        assert parse_search_form(form).regions == {"Kraj Vysočina": 63}

    def test_a_form_without_checkboxes_is_refused(self):
        with pytest.raises(SystemExit, match="has its shape changed"):
            parse_search_form("<h4>Plzeňský</h4>")


class TestBezrealitky:
    def test_reads_kraje_and_okresy_from_the_api(self):
        payload = {"data": {"czechRegions": [
            {"name": "Plzeňský kraj", "osmId": 442466, "children": [{"name": "okres Domažlice", "osmId": 441864}]},
        ]}}
        assert parse_regions(payload) == ({"Plzeňský kraj": "R442466"}, {"Domažlice": "R441864"})

    def test_prahas_children_in_the_api_are_skipped(self):
        """Under Praha the API lists části obce, which are not search districts."""
        payload = {"data": {"czechRegions": [
            {"name": "Praha", "osmId": 435514, "children": [{"name": "Holešovice", "osmId": 1}]},
        ]}}
        assert parse_regions(payload) == ({"Hlavní město Praha": "R435514"}, {})

    def test_an_empty_api_answer_is_refused(self):
        with pytest.raises(SystemExit, match="returned no regions"):
            parse_regions({"data": {"czechRegions": []}})

    def test_reads_prahas_ids_from_the_bundle_table(self):
        javascript = 'x={name:"Praha",osmId:"R435541"},{name:"Praha 7",osmId:"R20000064250"},y'
        assert parse_bundle(javascript) == ({"Hlavní město Praha": "R435541"}, {"Praha 7": "R20000064250"})

    def test_a_bundle_without_the_table_is_refused(self):
        with pytest.raises(SystemExit, match="no Praha ids in the bundle"):
            parse_bundle("console.log(1)")

    def test_the_bundles_praha_id_replaces_the_apis(self, monkeypatch):
        monkeypatch.setattr(bezrealitky, "_api_places",
                            lambda client: ({"Hlavní město Praha": "R1", "Plzeňský kraj": "R2"}, {}))
        monkeypatch.setattr(bezrealitky, "_bundle_places",
                            lambda client: ({"Hlavní město Praha": "R3"}, {"Praha 7": "R4"}))
        places = bezrealitky.Bezrealitky().fetch(client=None)
        assert places.regions == {"Plzeňský kraj": "R2", "Hlavní město Praha": "R3"}

    def test_a_search_page_heading_naming_the_place_confirms_its_id(self):
        html = "<h1>Všechny typy nabídek <span>•</span> okres Domažlice</h1>"
        assert heading_names(html, "Domažlice")
        assert not heading_names(html, "Kdyně")


class TestAddUnique:
    def test_a_name_repeated_with_different_ids_is_refused(self):
        places = {"Praha 7": 78}
        with pytest.raises(SystemExit, match="appears with two ids"):
            add_unique(places, "Praha 7", 79, "remax")


@dataclass
class FakePortal:
    """A portal serving fixed places and recording what the harvest hands it."""

    places: PortalPlaces[str, str]
    name: str = "fake"
    verified: list = field(default_factory=list)
    stored: list = field(default_factory=list)

    def fetch(self, client) -> PortalPlaces[str, str]:
        return self.places

    def verify(self, client, regions: list[MatchedRegion[str]], districts: list[MatchedDistrict[str]]) -> None:
        self.verified.append((regions, districts))

    def store(self, conn, regions: list[MatchedRegion[str]], districts: list[MatchedDistrict[str]]) -> None:
        self.stored.append((regions, districts))


class WritingPortal(FakePortal):
    """A fake portal whose store really writes its regions, into the table
    Sreality uses, so a test can see whether they were committed."""

    def store(self, conn, regions: list[MatchedRegion[str]], districts: list[MatchedDistrict[str]]) -> None:
        stmt = "INSERT INTO sreality_regions (kraj_code, region_id) VALUES (?, ?)"
        conn.executemany(stmt, [(region.kraj_code, 1) for region in regions])


@pytest.fixture
def gazetteer(tmp_path):
    """Two kraje, okres Domažlice and Praha's obvod Praha 7."""
    path = tmp_path / "gazetteer.sqlite"
    database = GazetteerDatabase.create(path)
    database.insert_kraje([Kraj(19, "Hlavní město Praha", _HERE), Kraj(43, "Plzeňský kraj", _HERE)])
    database.insert_okresy([Okres(3401, "Domažlice", 43, _HERE)])
    database.insert_obce([Obec(554782, "Praha", None, 19, _HERE)])
    database.insert_obvody([Obvod(78, "Praha 7", 554782, _HERE)])
    database.commit()
    database.close()
    return path


def _complete_places() -> PortalPlaces[str, str]:
    return PortalPlaces(
        regions={"Praha": "r19", "Plzeňský": "r43"},
        districts={"okres Domažlice": "d3401", "Praha 7": "d78", "Praha 13": "d13"},
    )


class TestHarvest:
    def test_each_portal_name_is_joined_to_its_official_place(self, gazetteer):
        """Names match despite the portal's wording, and the codes reach the portal."""
        portal = FakePortal(_complete_places())
        harvest_portals(gazetteer, client=None, portals=[portal])
        regions, districts = portal.stored[0]
        assert {(r.kraj_code, r.ids) for r in regions} == {(19, "r19"), (43, "r43")}
        assert {(d.okres_code, d.obvod_code, d.ids) for d in districts} == {(3401, None, "d3401"), (None, 78, "d78")}

    def test_the_portal_verifies_exactly_what_it_then_stores(self, gazetteer):
        portal = FakePortal(_complete_places())
        harvest_portals(gazetteer, client=None, portals=[portal])
        assert portal.verified == portal.stored

    def test_a_name_matching_no_search_place_is_left_out(self, gazetteer, capsys):
        """Praha 13 is a městská část, not an obvod, so it is reported and skipped."""
        portal = FakePortal(_complete_places())
        harvest_portals(gazetteer, client=None, portals=[portal])
        assert "Praha 13" in capsys.readouterr().out
        assert all(d.ids != "d13" for d in portal.stored[0][1])

    def test_a_search_place_the_portal_does_not_map_aborts(self, gazetteer):
        """Every okres must be mapped, since a profile may search it."""
        places = PortalPlaces(regions={"Praha": "r19", "Plzeňský": "r43"}, districts={"Praha 7": "d78"})
        with pytest.raises(SystemExit, match="no mapping for 1 okresy: Domažlice"):
            harvest_portals(gazetteer, client=None, portals=[FakePortal(places)])

    def test_two_portal_names_for_one_kraj_abort(self, gazetteer):
        places = PortalPlaces(regions={"Praha": "r19", "Hlavní město Praha": "r19b", "Plzeňský": "r43"},
                              districts={"Domažlice": "d3401", "Praha 7": "d78"})
        with pytest.raises(SystemExit, match="both name kraj Hlavní město Praha"):
            harvest_portals(gazetteer, client=None, portals=[FakePortal(places)])

    def test_a_failed_harvest_stores_nothing(self, gazetteer):
        """The harvest commits once, after every portal, so rows a portal
        already wrote are discarded when a later portal aborts."""
        complete = WritingPortal(_complete_places(), name="complete")
        incomplete = FakePortal(PortalPlaces(regions={}, districts={}), name="incomplete")
        with pytest.raises(SystemExit):
            harvest_portals(gazetteer, client=None, portals=[complete, incomplete])
        conn = sqlite3.connect(gazetteer)
        assert conn.execute("SELECT count(*) FROM sreality_regions").fetchone() == (0,)
