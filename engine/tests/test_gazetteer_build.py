"""Tests for the gazetteer build: the RÚIAN readers, the database writer and
the verification, against miniature RÚIAN files built in the test."""

import sqlite3
import zipfile

import pytest

from scripts.gazetteer.build import build_gazetteer
from scripts.gazetteer.database import SCHEMA_VERSION, GazetteerDatabase
from scripts.gazetteer.model import Kraj, Obec, Position, Ulice
from scripts.gazetteer.ruian.address_dump import RuianAddressDump
from scripts.gazetteer.ruian.state_file import RuianStateFile
from scripts.gazetteer.verify import verify_gazetteer

_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<vf:VymennyFormat xmlns:gml="http://www.opengis.net/gml/3.2"
 xmlns:vf="urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1"
 xmlns:vci="urn:cz:isvs:ruian:schemas:VuscIntTypy:v1"
 xmlns:oki="urn:cz:isvs:ruian:schemas:OkresIntTypy:v1"
 xmlns:opi="urn:cz:isvs:ruian:schemas:OrpIntTypy:v1"
 xmlns:pui="urn:cz:isvs:ruian:schemas:PouIntTypy:v1"
 xmlns:obi="urn:cz:isvs:ruian:schemas:ObecIntTypy:v1"
 xmlns:mpi="urn:cz:isvs:ruian:schemas:MopIntTypy:v1"
 xmlns:mci="urn:cz:isvs:ruian:schemas:MomcIntTypy:v1"
 xmlns:coi="urn:cz:isvs:ruian:schemas:CastObceIntTypy:v1"><vf:Data>"""


def _point(prefix: str, gml_id: str) -> str:
    """An S-JTSK definition point in Praha, as RÚIAN writes it."""
    return (f"<{prefix}:Geometrie><{prefix}:DefinicniBod><gml:Point gml:id=\"D{gml_id}\">"
            f"<gml:pos>-743100.00 -1043300.00</gml:pos></gml:Point></{prefix}:DefinicniBod></{prefix}:Geometrie>")


# A miniature state file: Praha with two obvody, two MČ and two části obce,
# and okres Domažlice with Domažlice and Kdyně.
_STATE = _HEADER + (
    "<vf:Vusc>"
    f'<vf:Vusc gml:id="VC.19"><vci:Kod>19</vci:Kod><vci:Nazev>Hlavní město Praha</vci:Nazev>{_point("vci", "VC19")}</vf:Vusc>'
    f'<vf:Vusc gml:id="VC.43"><vci:Kod>43</vci:Kod><vci:Nazev>Plzeňský kraj</vci:Nazev>{_point("vci", "VC43")}</vf:Vusc>'
    "</vf:Vusc><vf:Okresy>"
    f'<vf:Okres gml:id="OK.3401"><oki:Kod>3401</oki:Kod><oki:Nazev>Domažlice</oki:Nazev>'
    f'<oki:Vusc><vci:Kod>43</vci:Kod></oki:Vusc>{_point("oki", "OK3401")}</vf:Okres>'
    "</vf:Okresy><vf:Orp>"
    '<vf:Orp gml:id="OP.19"><opi:Kod>19</opi:Kod><opi:Vusc><vci:Kod>19</vci:Kod></opi:Vusc></vf:Orp>'
    "</vf:Orp><vf:Pou>"
    '<vf:Pou gml:id="PU.19"><pui:Kod>19</pui:Kod><pui:Orp><opi:Kod>19</opi:Kod></pui:Orp></vf:Pou>'
    "</vf:Pou><vf:Obce>"
    f'<vf:Obec gml:id="OB.554782"><obi:Kod>554782</obi:Kod><obi:Nazev>Praha</obi:Nazev>'
    f'<obi:Pou><pui:Kod>19</pui:Kod></obi:Pou>{_point("obi", "OB554782")}</vf:Obec>'
    f'<vf:Obec gml:id="OB.553425"><obi:Kod>553425</obi:Kod><obi:Nazev>Domažlice</obi:Nazev>'
    f'<obi:Okres><oki:Kod>3401</oki:Kod></obi:Okres><obi:Pou><pui:Kod>1015</pui:Kod></obi:Pou>{_point("obi", "OB553425")}</vf:Obec>'
    f'<vf:Obec gml:id="OB.553760"><obi:Kod>553760</obi:Kod><obi:Nazev>Kdyně</obi:Nazev>'
    f'<obi:Okres><oki:Kod>3401</oki:Kod></obi:Okres><obi:Pou><pui:Kod>1015</pui:Kod></obi:Pou>{_point("obi", "OB553760")}</vf:Obec>'
    "</vf:Obce><vf:Mop>"
    f'<vf:Mop gml:id="MP.60"><mpi:Kod>60</mpi:Kod><mpi:Nazev>Praha 6</mpi:Nazev><mpi:Obec><obi:Kod>554782</obi:Kod></mpi:Obec>{_point("mpi", "MP60")}</vf:Mop>'
    f'<vf:Mop gml:id="MP.78"><mpi:Kod>78</mpi:Kod><mpi:Nazev>Praha 7</mpi:Nazev><mpi:Obec><obi:Kod>554782</obi:Kod></mpi:Obec>{_point("mpi", "MP78")}</vf:Mop>'
    "</vf:Mop><vf:Momc>"
    f'<vf:Momc gml:id="MC.500178"><mci:Kod>500178</mci:Kod><mci:Nazev>Praha 6</mci:Nazev>'
    f'<mci:Mop><mpi:Kod>60</mpi:Kod></mci:Mop><mci:Obec><obi:Kod>554782</obi:Kod></mci:Obec>{_point("mci", "MC500178")}</vf:Momc>'
    f'<vf:Momc gml:id="MC.500186"><mci:Kod>500186</mci:Kod><mci:Nazev>Praha 7</mci:Nazev>'
    f'<mci:Mop><mpi:Kod>78</mpi:Kod></mci:Mop><mci:Obec><obi:Kod>554782</obi:Kod></mci:Obec>{_point("mci", "MC500186")}</vf:Momc>'
    "</vf:Momc><vf:CastiObci>"
    f'<vf:CastObce gml:id="CO.490016"><coi:Kod>490016</coi:Kod><coi:Nazev>Bubeneč</coi:Nazev>'
    f'<coi:Obec><obi:Kod>554782</obi:Kod></coi:Obec>{_point("coi", "CO490016")}</vf:CastObce>'
    f'<vf:CastObce gml:id="CO.490229"><coi:Kod>490229</coi:Kod><coi:Nazev>Holešovice</coi:Nazev>'
    f'<coi:Obec><obi:Kod>554782</obi:Kod></coi:Obec>{_point("coi", "CO490229")}</vf:CastObce>'
    f'<vf:CastObce gml:id="CO.32247"><coi:Kod>32247</coi:Kod><coi:Nazev>Kdyně</coi:Nazev>'
    f'<coi:Obec><obi:Kod>553760</obi:Kod></coi:Obec>{_point("coi", "CO32247")}</vf:CastObce>'
    "</vf:CastiObci></vf:Data></vf:VymennyFormat>"
)

_ADDRESS_HEADER = ("Kód ADM;Kód obce;Název obce;Kód MOMC;Název MOMC;Kód obvodu Prahy;"
                   "Název obvodu Prahy;Kód části obce;Název části obce;Kód ulice;Název ulice;"
                   "Typ SO;Číslo domovní;Číslo orientační;Znak čísla orientačního;PSČ;"
                   "Souřadnice Y;Souřadnice X;Platí Od")

# Address rows. Přístavní lies in Holešovice, MČ Praha 7. Bubeneč has
# addresses in both Praha 6 and Praha 7. Bubenečská has an address without
# coordinates only. Náměstí lies in Kdyně, which has no MČ.
_ADDRESSES = [
    "1;554782;Praha;500186;Praha 7;78;Praha 7;490229;Holešovice;467103;Přístavní;č.p.;1;;;17000;741000.00;1042000.00;",
    "2;554782;Praha;500186;Praha 7;78;Praha 7;490229;Holešovice;467103;Přístavní;č.p.;2;;;17000;741002.00;1042002.00;",
    "3;554782;Praha;500178;Praha 6;60;Praha 6;490016;Bubeneč;100001;Pod Kaštany;č.p.;3;;;16000;743000.00;1041000.00;",
    "4;554782;Praha;500186;Praha 7;78;Praha 7;490016;Bubeneč;100002;Nad Štolou;č.p.;4;;;17000;742000.00;1041500.00;",
    "5;554782;Praha;500186;Praha 7;78;Praha 7;490016;Bubeneč;100003;Bubenečská;č.p.;5;;;17000;;;",
    "6;553760;Kdyně;;;;;32247;Kdyně;200001;Náměstí;č.p.;6;;;34506;845000.00;1105000.00;",
]


@pytest.fixture
def state_file(tmp_path):
    path = tmp_path / "ST_UZSZ.xml.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("ST_UZSZ.xml", _STATE.encode("utf-8"))
    return path


@pytest.fixture
def address_dump(tmp_path):
    path = tmp_path / "OB_ADR_csv.zip"
    by_obec: dict[str, list[str]] = {}
    for row in _ADDRESSES:
        by_obec.setdefault(row.split(";")[1], []).append(row)
    with zipfile.ZipFile(path, "w") as bundle:
        for obec_code, rows in by_obec.items():
            content = "\n".join([_ADDRESS_HEADER, *rows]) + "\n"
            bundle.writestr(f"CSV/OB_{obec_code}_ADR.csv", content.encode("cp1250"))
    return path


@pytest.fixture
def built(tmp_path, state_file, address_dump):
    """A gazetteer built from the miniature files, opened for reading."""
    path = tmp_path / "gazetteer.sqlite"
    build_gazetteer(state_file, address_dump, path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestStateFile:
    def test_reads_every_unit_with_its_official_name(self, state_file):
        """Each kind comes out with the code and name RÚIAN gives it."""
        state = RuianStateFile(state_file)
        assert {(k.code, k.name) for k in state.kraje()} == {(19, "Hlavní město Praha"), (43, "Plzeňský kraj")}
        assert [(o.code, o.name) for o in state.okresy()] == [(3401, "Domažlice")]
        assert {o.name for o in state.obvody()} == {"Praha 6", "Praha 7"}
        assert {c.name for c in state.casti_obce()} == {"Bubeneč", "Holešovice", "Kdyně"}

    def test_an_obec_reaches_its_kraj_through_its_okres(self, state_file):
        """Kdyně belongs to okres Domažlice, so to its kraj."""
        obce = {o.name: o for o in RuianStateFile(state_file).obce()}
        assert (obce["Kdyně"].okres_code, obce["Kdyně"].kraj_code) == (3401, 43)

    def test_praha_reaches_its_kraj_without_an_okres(self, state_file):
        """Praha has no okres, so its kraj comes through its POU and ORP."""
        praha = next(o for o in RuianStateFile(state_file).obce() if o.name == "Praha")
        assert (praha.okres_code, praha.kraj_code) == (None, 19)

    def test_a_prague_mestska_cast_names_its_obvod(self, state_file):
        """MČ Praha 7 lies in obec Praha and in obvod Praha 7."""
        mestske_casti = {m.code: m for m in RuianStateFile(state_file).mestske_casti()}
        assert (mestske_casti[500186].obec_code, mestske_casti[500186].obvod_code) == (554782, 78)

    def test_definition_points_become_latitude_and_longitude(self, state_file):
        """The S-JTSK definition point lands in Praha in WGS84."""
        kraj = next(k for k in RuianStateFile(state_file).kraje() if k.code == 19)
        assert 50.0 < kraj.position.lat < 50.2 and 14.3 < kraj.position.lon < 14.6


class TestAddressDump:
    def test_a_street_sits_at_the_mean_of_its_addresses(self, address_dump):
        """Přístavní's two addresses average to one position, in Praha."""
        streets = {u.name: u for u in RuianAddressDump(address_dump).ulice()}
        pristavni = streets["Přístavní"]
        assert (pristavni.code, pristavni.obec_code) == (467103, 554782)
        assert 50.0 < pristavni.position.lat < 50.2 and 14.3 < pristavni.position.lon < 14.6

    def test_a_street_without_located_addresses_is_left_out(self, address_dump):
        """Bubenečská has no coordinates, so it is not stored, and neither are its links."""
        dump = RuianAddressDump(address_dump)
        assert "Bubenečská" not in {u.name for u in dump.ulice()}
        assert all(street != 100003 for street, _ in dump.overlaps().ulice_casti_obce)

    def test_a_cast_obce_spanning_two_mestske_casti_links_to_both(self, address_dump):
        """Bubeneč has addresses in Praha 6 and Praha 7."""
        pairs = RuianAddressDump(address_dump).overlaps().casti_obce_mestske_casti
        assert {mc for part, mc in pairs if part == 490016} == {500178, 500186}

    def test_a_street_links_to_its_cast_obce_and_mestska_cast(self, address_dump):
        """Přístavní's addresses link it to Holešovice and to MČ Praha 7."""
        overlaps = RuianAddressDump(address_dump).overlaps()
        assert (467103, 490229) in overlaps.ulice_casti_obce
        assert (467103, 500186) in overlaps.ulice_mestske_casti

    def test_an_obec_without_mestske_casti_records_no_mestska_cast_links(self, address_dump):
        """Kdyně is not a divided city, so its street links only to its část obce."""
        overlaps = RuianAddressDump(address_dump).overlaps()
        assert (200001, 32247) in overlaps.ulice_casti_obce
        assert all(street != 200001 for street, _ in overlaps.ulice_mestske_casti)


class TestDatabase:
    def test_a_new_gazetteer_records_its_schema_version(self, tmp_path):
        """The engine checks this version before reading the file."""
        database = GazetteerDatabase.create(tmp_path / "g.sqlite")
        database.commit()
        database.close()
        conn = sqlite3.connect(tmp_path / "g.sqlite")
        assert conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone() == (str(SCHEMA_VERSION),)

    def test_a_place_whose_parent_is_missing_is_refused(self, tmp_path):
        """Foreign keys are on: a street in an unknown obec fails the insert."""
        database = GazetteerDatabase.create(tmp_path / "g.sqlite")
        with pytest.raises(sqlite3.IntegrityError):
            database.insert_ulice([Ulice(code=1, name="Nikde", obec_code=999, position=Position(50.0, 14.0))])

    def test_names_are_stored_normalized_for_lookup(self, tmp_path):
        """Each name gets its lowercase, diacritics-free lookup form."""
        database = GazetteerDatabase.create(tmp_path / "g.sqlite")
        database.insert_kraje([Kraj(code=19, name="Hlavní město Praha", position=Position(50.0, 14.0))])
        database.insert_obce([Obec(code=1, name="Kdyně", okres_code=None, kraj_code=19, position=Position(49.4, 13.0))])
        database.commit()
        conn = sqlite3.connect(tmp_path / "g.sqlite")
        assert conn.execute("SELECT name_norm FROM obce").fetchone() == ("kdyne",)


class TestBuild:
    def test_every_place_is_reachable_by_name_with_its_kind_and_code(self, built):
        """The places view answers a name with the kind, code and obec."""
        stmt = "SELECT kind, code, obec_code FROM places WHERE name_norm = 'pristavni'"
        assert [tuple(row) for row in built.execute(stmt)] == [("ulice", 467103, 554782)]

    def test_an_obec_and_its_cast_obce_with_one_name_are_two_places(self, built):
        """Kdyně is both an obec and a část obce: two rows, two kinds."""
        stmt = "SELECT kind FROM places WHERE name_norm = 'kdyne' ORDER BY kind"
        assert [row["kind"] for row in built.execute(stmt)] == ["cast_obce", "obec"]

    def test_a_cast_obce_reaches_the_obvody_it_touches_through_its_mestske_casti(self, built):
        """Bubeneč touches Praha 6 and Praha 7, through the MČ its addresses lie in."""
        stmt = """
            SELECT ob.name FROM casti_obce_mestske_casti cm
            JOIN mestske_casti m ON m.code = cm.mestska_cast_code
            JOIN obvody ob ON ob.code = m.obvod_code
            WHERE cm.cast_obce_code = 490016 ORDER BY ob.name
        """
        assert [row["name"] for row in built.execute(stmt)] == ["Praha 6", "Praha 7"]


class TestVerification:
    def test_a_miniature_gazetteer_fails_only_on_its_size(self, tmp_path, state_file, address_dump):
        """The known places check out, but a handful of rows is no gazetteer."""
        path = tmp_path / "gazetteer.sqlite"
        build_gazetteer(state_file, address_dump, path)
        with pytest.raises(SystemExit) as failure:
            verify_gazetteer(path)
        message = str(failure.value)
        assert "kraje: 2 rows" in message
        assert "Přístavní" not in message and "Kdyně" not in message and "Bubeneč" not in message
        assert "foreign key" not in message

    def test_a_contradiction_in_the_hierarchy_is_reported(self, tmp_path, state_file, address_dump):
        """An obec whose kraj differs from its okres's fails verification."""
        path = tmp_path / "gazetteer.sqlite"
        build_gazetteer(state_file, address_dump, path)
        conn = sqlite3.connect(path)
        conn.execute("UPDATE obce SET kraj_code = 19 WHERE name = 'Kdyně'")
        conn.commit()
        conn.close()
        with pytest.raises(SystemExit, match="obce name a kraj other than their okres"):
            verify_gazetteer(path)
