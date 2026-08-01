"""Tests for the location-data harvest parsers and the shipped place table.

Run: python3 -m pytest tests/test_location_data.py -v
"""

import importlib.util
import json
import re
from pathlib import Path

import httpx
import pytest

_spec = importlib.util.spec_from_file_location(
    "refresh_location_data",
    Path(__file__).parent.parent / "scripts" / "refresh_location_data.py",
)
harvest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harvest)

FIXTURES = Path(__file__).parent / "fixtures" / "location"


class TestSrealityFacetParsing:
    """The region and district facets embedded in the search page parse into
    id/name/region rows."""

    def test_parses_regions_and_districts(self):
        html = (FIXTURES / "sreality_search.html").read_text()
        regions, districts = harvest.parse_sreality_facets(html)
        assert {"id": 2, "name": "Plzeňský kraj"} in regions
        assert {"id": 8, "name": "Domažlice", "region_id": 2} in districts
        assert {"id": 5007, "name": "Praha 7", "region_id": 10} in districts

    def test_missing_facet_aborts(self):
        with pytest.raises(SystemExit, match="facet"):
            harvest.parse_sreality_facets("<html>redesigned</html>")


class TestRemaxFormParsing:
    """The two-level checkbox tree parses into region/district rows; headings
    without checkboxes are ignored."""

    def test_parses_checkbox_tree(self):
        html = (FIXTURES / "remax_form.html").read_text()
        rows = harvest.parse_remax_form(html)
        assert {"region_name": "Plzeňský", "region_id": 43,
                "district_id": 3401, "district_name": "Domažlice"} in rows
        assert all(r["region_name"] != "Typ nemovitosti" for r in rows)
        praha = [r for r in rows if r["region_name"] == "Praha"]
        assert praha and all(r["region_id"] == 19 for r in praha)

    def test_formless_page_aborts(self):
        with pytest.raises(SystemExit, match="checkboxes"):
            harvest.parse_remax_form("<html>redesigned</html>")


class TestBezrealitkyRegionParsing:
    """czechRegions maps normalized kraj and okres names to osmIds."""

    PAYLOAD = {"data": {"czechRegions": [
        {"id": "489", "name": "Plzeňský kraj", "osmId": 442466, "children": [
            {"id": "650", "name": "okres Domažlice", "osmId": 441864},
        ]},
        {"id": "486", "name": "Praha", "osmId": 435514, "children": []},
    ]}}

    def test_maps_kraje_and_okresy(self):
        kraje, okresy = harvest.parse_bezrealitky_regions(self.PAYLOAD)
        assert kraje["plzensky"] == 442466
        assert kraje["praha"] == 435514
        assert okresy["domazlice"] == 441864

    def test_empty_payload_aborts(self):
        with pytest.raises(SystemExit, match="czechRegions"):
            harvest.parse_bezrealitky_regions({"data": {"czechRegions": []}})


class TestBezrealitkyIdVerification:
    """An id counts as verified only when the server-rendered <h1> names the
    exact expected place."""

    def _client(self, h1: str | None):
        body = f"<html><body><h1>{h1}</h1></body></html>" if h1 is not None else "<html></html>"

        def handler(request):
            return httpx.Response(200, text=body)

        return httpx.Client(transport=httpx.MockTransport(handler))

    @pytest.fixture(autouse=True)
    def _no_pacing(self, monkeypatch):
        monkeypatch.setattr(harvest, "REQUEST_SPACING_S", 0)

    def test_matching_heading_verifies(self):
        client = self._client("Všechny typy nabídek • okres Domažlice")
        assert harvest.verify_bezrealitky_id(client, "R441864", "Domažlice") is True

    def test_prefix_of_another_district_does_not_verify(self):
        # 'Praha 1' must not pass verification against a 'Praha 10' page.
        client = self._client("Všechny typy nabídek • Praha 10")
        assert harvest.verify_bezrealitky_id(client, "R123", "Praha 1") is False

    def test_unrecognized_id_page_does_not_verify(self):
        client = self._client("Všechny typy nabídek")
        assert harvest.verify_bezrealitky_id(client, "R99999999999", "Domažlice") is False

    def test_missing_heading_does_not_verify(self):
        client = self._client(None)
        assert harvest.verify_bezrealitky_id(client, "R441864", "Domažlice") is False



def _sreality_page(regions, districts):
    return ('<html><script>{"idName":"locality_region_id","values":'
            + json.dumps(regions, ensure_ascii=False)
            + '},{"idName":"locality_district_id","values":'
            + json.dumps(districts, ensure_ascii=False) + '}</script></html>')


def _remax_page(sections):
    parts = []
    for region_name, rows in sections.items():
        parts.append(f"<h4>{region_name}</h4>")
        for region_id, district_id, label in rows:
            parts.append(f'<input type="checkbox" name="regions[{region_id}][{district_id}]">'
                         f'<label for="regions[{region_id}][{district_id}]">{label}</label>')
    return "<html><body>" + "".join(parts) + "</body></html>"


def _harvest_client(sreality_html, remax_html, graphql_payload, ssr_names):
    """Fake all four portal endpoints; ssr_names maps a regionOsmIds value to
    the place name its verification page shows."""

    def handler(request):
        host = request.url.host
        if host == "www.sreality.cz":
            return httpx.Response(200, text=sreality_html)
        if host == "www.remax-czech.cz":
            return httpx.Response(200, text=remax_html)
        if host == "api.bezrealitky.cz":
            return httpx.Response(200, json=graphql_payload)
        if host == "www.bezrealitky.cz":
            name = ssr_names.get(request.url.params.get("regionOsmIds"))
            heading = f"Všechny typy nabídek • {name}" if name else "Všechny typy nabídek"
            return httpx.Response(200, text=f"<html><body><h1>{heading}</h1></body></html>")
        raise AssertionError(f"unexpected host {host}")

    return httpx.Client(transport=httpx.MockTransport(handler))


class TestBuildPlaces:
    """The cross-portal join emits a row per sreality district with all three
    portals' ids, applies overrides before checking completeness, and aborts
    on any unmatched name or failed verification."""

    @pytest.fixture(autouse=True)
    def _no_pacing(self, monkeypatch):
        monkeypatch.setattr(harvest, "REQUEST_SPACING_S", 0)
        monkeypatch.setattr(harvest, "load_overrides",
                            lambda: {"regions": {}, "districts": {}})

    SREALITY = _sreality_page(
        [{"id": 2, "name": "Plzeňský kraj"}],
        [{"id": 8, "name": "Domažlice", "regionId": 2},
         {"id": 11, "name": "Klatovy", "regionId": 2}],
    )
    REMAX = _remax_page({"Plzeňský": [(43, 3401, "Domažlice"), (43, 3404, "Klatovy")]})
    GRAPHQL = {"data": {"czechRegions": [
        {"name": "Plzeňský kraj", "osmId": 442466, "children": [
            {"name": "okres Domažlice", "osmId": 441864},
            {"name": "okres Klatovy", "osmId": 441183},
        ]},
    ]}}
    SSR_NAMES = {"R442466": "Plzeňský kraj", "R441864": "okres Domažlice",
                 "R441183": "okres Klatovy"}

    def test_joins_all_three_portals_by_normalized_name(self):
        client = _harvest_client(self.SREALITY, self.REMAX, self.GRAPHQL, self.SSR_NAMES)
        places = harvest.build_places(client)
        assert [r["slug"] for r in places["regions"]] == ["plzensky"]
        domazlice = next(d for d in places["districts"] if d["slug"] == "domazlice")
        assert domazlice == {
            "name": "Domažlice", "slug": "domazlice", "region_slug": "plzensky",
            "sreality_district_id": 8, "remax_region_id": 43,
            "remax_district_id": 3401, "bezrealitky_region_id": "R441864",
        }

    def test_district_missing_on_one_portal_aborts(self):
        remax = _remax_page({"Plzeňský": [(43, 3401, "Domažlice")]})  # no Klatovy
        client = _harvest_client(self.SREALITY, remax, self.GRAPHQL, self.SSR_NAMES)
        with pytest.raises(SystemExit, match="join failed"):
            harvest.build_places(client)

    def test_region_missing_on_one_portal_aborts(self):
        graphql = {"data": {"czechRegions": [
            {"name": "Jihočeský kraj", "osmId": 442321, "children": [
                {"name": "okres Domažlice", "osmId": 441864},
                {"name": "okres Klatovy", "osmId": 441183},
            ]},
        ]}}  # Plzeňský kraj itself is gone
        client = _harvest_client(self.SREALITY, self.REMAX, graphql, self.SSR_NAMES)
        with pytest.raises(SystemExit, match="join failed"):
            harvest.build_places(client)

    def test_failed_id_verification_aborts(self):
        ssr = dict(self.SSR_NAMES)
        del ssr["R441183"]  # Klatovy id no longer recognized by the portal
        client = _harvest_client(self.SREALITY, self.REMAX, self.GRAPHQL, ssr)
        with pytest.raises(SystemExit, match="verification"):
            harvest.build_places(client)

    def test_two_places_normalizing_identically_abort(self):
        remax = _remax_page({"Plzeňský": [(43, 3401, "Domažlice"), (43, 3404, "Klatovy"),
                                          (43, 9999, "okres Domažlice")]})
        client = _harvest_client(self.SREALITY, remax, self.GRAPHQL, self.SSR_NAMES)
        with pytest.raises(SystemExit, match="collision"):
            harvest.build_places(client)

    def test_override_shadowing_a_harvested_value_is_reported(self, monkeypatch, capsys):
        # If the portal starts supplying a value an override works around,
        # the run must say so instead of hiding the fresh data forever.
        monkeypatch.setattr(harvest, "load_overrides", lambda: {
            "regions": {}, "districts": {"domazlice": {"bezrealitky_region_id": "R999"}},
        })
        ssr = dict(self.SSR_NAMES)
        ssr["R999"] = "okres Domažlice"
        client = _harvest_client(self.SREALITY, self.REMAX, self.GRAPHQL, ssr)
        places = harvest.build_places(client)
        assert next(d for d in places["districts"]
                    if d["slug"] == "domazlice")["bezrealitky_region_id"] == "R999"
        notice = [line for line in capsys.readouterr().out.splitlines() if "NOTICE" in line]
        assert len(notice) == 1
        assert "R441864" in notice[0] and "R999" in notice[0]

    def test_override_filling_an_absent_value_is_not_reported(self, monkeypatch, capsys):
        monkeypatch.setattr(harvest, "load_overrides", lambda: {
            "regions": {"praha": {"bezrealitky_region_id": "R435541"}},
            "districts": {"praha-7": {"bezrealitky_region_id": "R20000064250"}},
        })
        sreality = _sreality_page(
            [{"id": 10, "name": "Hlavní město Praha"}],
            [{"id": 5007, "name": "Praha 7", "regionId": 10}],
        )
        remax = _remax_page({"Praha": [(19, 78, "Praha 7")]})
        graphql = {"data": {"czechRegions": [{"name": "Praha", "osmId": 435514, "children": []}]}}
        ssr = {"R435541": "Praha", "R20000064250": "Praha 7"}
        client = _harvest_client(sreality, remax, graphql, ssr)
        harvest.build_places(client)
        notices = [line for line in capsys.readouterr().out.splitlines() if "NOTICE" in line]
        # The praha REGION notice fires (czechRegions supplies a conflicting
        # id); the praha-7 DISTRICT one must not (czechRegions supplies none).
        assert len(notices) == 1 and "Praha 7" not in notices[0]

    def test_override_supplies_ids_the_portals_lack(self, monkeypatch):
        sreality = _sreality_page(
            [{"id": 10, "name": "Hlavní město Praha"}],
            [{"id": 5007, "name": "Praha 7", "regionId": 10}],
        )
        remax = _remax_page({"Praha": [(19, 78, "Praha 7")]})
        graphql = {"data": {"czechRegions": [
            {"name": "Praha", "osmId": 435514, "children": []},
        ]}}
        monkeypatch.setattr(harvest, "load_overrides", lambda: {
            "regions": {"praha": {"bezrealitky_region_id": "R435541"}},
            "districts": {"praha-7": {"bezrealitky_region_id": "R20000064250"}},
        })
        ssr = {"R435541": "Praha", "R20000064250": "Praha 7"}
        client = _harvest_client(sreality, remax, graphql, ssr)
        places = harvest.build_places(client)
        assert places["regions"][0]["bezrealitky_region_id"] == "R435541"
        assert places["districts"][0]["bezrealitky_region_id"] == "R20000064250"


PLACES_PATH = (Path(__file__).parent.parent / "src" / "rentczecher" / "adapters"
               / "scrapers" / "location_data" / "places.json")


@pytest.fixture(scope="module")
def places():
    return json.loads(PLACES_PATH.read_text())


# The Czech Republic's district-level division, unchanged since 2007, written
# from geography rather than derived from places.json so a silent edit to the
# table cannot satisfy it by construction.
REFERENCE_DISTRICTS = {
    "praha": ["praha-1", "praha-2", "praha-3", "praha-4", "praha-5",
              "praha-6", "praha-7", "praha-8", "praha-9", "praha-10"],
    "stredocesky": ["benesov", "beroun", "kladno", "kolin", "kutna-hora", "melnik",
                    "mlada-boleslav", "nymburk", "praha-vychod", "praha-zapad",
                    "pribram", "rakovnik"],
    "jihocesky": ["ceske-budejovice", "cesky-krumlov", "jindrichuv-hradec", "pisek",
                  "prachatice", "strakonice", "tabor"],
    "plzensky": ["domazlice", "klatovy", "plzen-mesto", "plzen-jih", "plzen-sever",
                 "rokycany", "tachov"],
    "karlovarsky": ["cheb", "karlovy-vary", "sokolov"],
    "ustecky": ["decin", "chomutov", "litomerice", "louny", "most", "teplice",
                "usti-nad-labem"],
    "liberecky": ["ceska-lipa", "jablonec-nad-nisou", "liberec", "semily"],
    "kralovehradecky": ["hradec-kralove", "jicin", "nachod", "rychnov-nad-kneznou",
                        "trutnov"],
    "pardubicky": ["chrudim", "pardubice", "svitavy", "usti-nad-orlici"],
    "vysocina": ["havlickuv-brod", "jihlava", "pelhrimov", "trebic",
                 "zdar-nad-sazavou"],
    "jihomoravsky": ["blansko", "brno-mesto", "brno-venkov", "breclav", "hodonin",
                     "vyskov", "znojmo"],
    "olomoucky": ["jesenik", "olomouc", "prostejov", "prerov", "sumperk"],
    "zlinsky": ["kromeriz", "uherske-hradiste", "vsetin", "zlin"],
    "moravskoslezsky": ["bruntal", "frydek-mistek", "karvina", "novy-jicin",
                        "opava", "ostrava-mesto"],
}


class TestShippedPlaceTable:
    """Structural invariants and production-proven anchors of the committed
    places.json."""

    def test_covers_all_czech_regions_and_districts(self, places):
        # 14 kraje; 76 okresy + Praha 1-10 = 86 district-level rows.
        assert len(places["regions"]) == 14
        assert len(places["districts"]) == 86

    def test_every_district_maps_to_its_real_region(self, places):
        shipped = {d["slug"]: d["region_slug"] for d in places["districts"]}
        reference = {district: region
                     for region, districts in REFERENCE_DISTRICTS.items()
                     for district in districts}
        assert shipped == reference

    def test_shipped_regions_are_the_real_kraje(self, places):
        assert {r["slug"] for r in places["regions"]} == set(REFERENCE_DISTRICTS)

    def test_every_row_has_ids_for_all_three_portals(self, places):
        for row in places["regions"]:
            assert row["sreality_region_id"] and row["remax_region_id"], row["slug"]
            assert row["bezrealitky_region_id"], row["slug"]
        for row in places["districts"]:
            assert row["sreality_district_id"], row["slug"]
            assert row["remax_region_id"] and row["remax_district_id"], row["slug"]
            assert row["bezrealitky_region_id"], row["slug"]

    def test_slugs_are_unique(self, places):
        slugs = [r["slug"] for r in places["regions"]] + [d["slug"] for d in places["districts"]]
        assert len(slugs) == len(set(slugs))

    def test_portal_ids_are_unique(self, places):
        districts = places["districts"]
        for field in ("sreality_district_id", "bezrealitky_region_id"):
            ids = [d[field] for d in districts]
            assert len(ids) == len(set(ids)), field
        remax_pairs = [(d["remax_region_id"], d["remax_district_id"]) for d in districts]
        assert len(remax_pairs) == len(set(remax_pairs))

    def test_every_district_belongs_to_a_shipped_region(self, places):
        region_slugs = {r["slug"] for r in places["regions"]}
        for district in places["districts"]:
            assert district["region_slug"] in region_slugs, district["slug"]

    def test_praha_7_anchor_matches_production_proven_values(self, places):
        praha7 = next(d for d in places["districts"] if d["slug"] == "praha-7")
        assert praha7["sreality_district_id"] == 5007
        assert praha7["bezrealitky_region_id"] == "R20000064250"
        assert praha7["remax_region_id"] == 19

    def test_domazlice_anchor_matches_production_proven_values(self, places):
        domazlice = next(d for d in places["districts"] if d["slug"] == "domazlice")
        assert domazlice["sreality_district_id"] == 8
        assert domazlice["bezrealitky_region_id"] == "R441864"
        assert (domazlice["remax_region_id"], domazlice["remax_district_id"]) == (43, 3401)

    def test_praha_region_anchor(self, places):
        praha = next(r for r in places["regions"] if r["slug"] == "praha")
        assert praha["sreality_region_id"] == 10
        assert praha["remax_region_id"] == 19

    def test_bezrealitky_ids_have_the_right_shape_per_namespace(self, places):
        # Regular districts carry real OSM relation ids (6-7 digits); Prague
        # districts carry the portal's synthetic bundle ids (11 digits,
        # R2000...). A swapped or garbled id on an unanchored row breaks this
        # even though no anchor pins that row directly.
        for district in places["districts"]:
            digits = district["bezrealitky_region_id"].removeprefix("R")
            if district["region_slug"] == "praha":
                assert len(digits) == 11 and digits.startswith("2000"), district["slug"]
            else:
                assert len(digits) <= 7, district["slug"]

    def test_praha_1_anchor_pins_remax_global_id_numbering(self, places):
        # RE/MAX ids come from one global sequence: Praha 1's district id 19
        # equals the Praha region id itself. The pair is the key, not the
        # district id alone, and this row pins that quirk as intentional.
        praha1 = next(d for d in places["districts"] if d["slug"] == "praha-1")
        assert praha1["sreality_district_id"] == 5001
        assert (praha1["remax_region_id"], praha1["remax_district_id"]) == (19, 19)
        assert praha1["bezrealitky_region_id"] == "R20000061612"


@pytest.mark.live
class TestShippedIdsLive:
    """Sampled proof that shipped ids still work on the real portals - the
    test that catches a portal renumbering its taxonomy (like RE/MAX retiring
    district 3402)."""

    @pytest.fixture(scope="class")
    def client(self):
        import httpx as _httpx
        headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"}
        with _httpx.Client(timeout=30, follow_redirects=True, headers=headers) as c:
            yield c

    def _sample(self, places):
        by_slug = {d["slug"]: d for d in places["districts"]}
        return [by_slug["praha-1"], by_slug["praha-7"], by_slug["domazlice"], by_slug["olomouc"]]

    def test_sreality_ids_filter_searches(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get("https://www.sreality.cz/api/v1/estates/search",
                              params={"locality_district_id": district["sreality_district_id"],
                                      "per_page": 1, "lang": "cs"},
                              headers={"Accept": "application/json"})
            assert resp.status_code == 200, district["slug"]
            assert resp.json()["pagination"]["total"] > 0, district["slug"]

    def test_bezrealitky_ids_resolve_to_their_names(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get("https://www.bezrealitky.cz/vyhledat",
                              params={"regionOsmIds": district["bezrealitky_region_id"]})
            assert resp.status_code == 200, district["slug"]
            heading = re.search(r"<h1[^>]*>(.*?)</h1>", resp.text, re.DOTALL)
            assert heading is not None, district["slug"]
            assert harvest.normalize_name(district["name"]) in [
                harvest.normalize_name(part)
                for part in re.sub(r"<[^>]+>", "", heading.group(1)).split("•")
            ], district["slug"]

    def test_remax_ids_are_accepted_by_the_search_form(self, places, client):
        import time
        for district in self._sample(places):
            time.sleep(1)
            resp = client.get(
                "https://www.remax-czech.cz/reality/vyhledavani/",
                params={"hledani": 1,
                        f"regions[{district['remax_region_id']}][{district['remax_district_id']}]": "on"},
            )
            assert resp.status_code == 200, district["slug"]
