"""Reads RÚIAN's state-level exchange file (ST_UZSZ): every territorial unit
above the street, each with its official code, name, parent and definition
point."""

import xml.etree.ElementTree as ElementTree
import zipfile
from pathlib import Path

from pyproj import Transformer

from ..model import CastObce, Kraj, MestskaCast, Obec, Obvod, Okres, Position

_NAMESPACES = {
    "vf": "urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1",
    "gml": "http://www.opengis.net/gml/3.2",
    "vci": "urn:cz:isvs:ruian:schemas:VuscIntTypy:v1",
    "oki": "urn:cz:isvs:ruian:schemas:OkresIntTypy:v1",
    "opi": "urn:cz:isvs:ruian:schemas:OrpIntTypy:v1",
    "pui": "urn:cz:isvs:ruian:schemas:PouIntTypy:v1",
    "obi": "urn:cz:isvs:ruian:schemas:ObecIntTypy:v1",
    "mpi": "urn:cz:isvs:ruian:schemas:MopIntTypy:v1",
    "mci": "urn:cz:isvs:ruian:schemas:MomcIntTypy:v1",
    "coi": "urn:cz:isvs:ruian:schemas:CastObceIntTypy:v1",
}

# The element types read, by tag. In the file each type's container carries
# the same tag as its elements, so only tags with a gml:id are elements.
_ELEMENT_TAGS = {
    f"{{{_NAMESPACES['vf']}}}{name}": name
    for name in ("Vusc", "Okres", "Orp", "Pou", "Obec", "Mop", "Momc", "CastObce")
}
_GML_ID = f"{{{_NAMESPACES['gml']}}}id"


class RuianStateFile:
    """The units of one ST_UZSZ file, read once."""

    def __init__(self, path: Path):
        # Definition points are EPSG:5514 S-JTSK, negative-signed.
        self._to_wgs84 = Transformer.from_crs("EPSG:5514", "EPSG:4326", always_xy=True)
        self._elements: dict[str, list[ElementTree.Element]] = {name: [] for name in _ELEMENT_TAGS.values()}
        with zipfile.ZipFile(path) as bundle, bundle.open(bundle.namelist()[0]) as xml:
            for _, element in ElementTree.iterparse(xml, events=("end",)):
                name = _ELEMENT_TAGS.get(element.tag)
                if name is not None and element.get(_GML_ID) is not None:
                    self._elements[name].append(element)

    def kraje(self) -> list[Kraj]:
        return [
            Kraj(code=_code(element, "vci:Kod"), name=_text(element, "vci:Nazev"),
                 position=self._position(element))
            for element in self._elements["Vusc"]
        ]

    def okresy(self) -> list[Okres]:
        return [
            Okres(code=_code(element, "oki:Kod"), name=_text(element, "oki:Nazev"),
                  kraj_code=_code(element, "oki:Vusc/vci:Kod"), position=self._position(element))
            for element in self._elements["Okres"]
        ]

    def obce(self) -> list[Obec]:
        okres_kraj = {_code(e, "oki:Kod"): _code(e, "oki:Vusc/vci:Kod") for e in self._elements["Okres"]}
        # Since 2021 an ORP links to its okres, not its kraj, except Praha's,
        # which has no okres and still names its kraj.
        orp_kraj = {_code(e, "opi:Kod"): _optional_code(e, "opi:Vusc/vci:Kod") for e in self._elements["Orp"]}
        pou_orp = {_code(e, "pui:Kod"): _code(e, "pui:Orp/opi:Kod") for e in self._elements["Pou"]}
        obce = []
        for element in self._elements["Obec"]:
            okres_code = _optional_code(element, "obi:Okres/oki:Kod")
            if okres_code is not None:
                kraj_code = okres_kraj[okres_code]
            else:
                orp_kraj_code = orp_kraj[pou_orp[_code(element, "obi:Pou/pui:Kod")]]
                if orp_kraj_code is None:
                    raise ValueError(f"RÚIAN obec {_code(element, 'obi:Kod')} reaches no kraj")
                kraj_code = orp_kraj_code
            obce.append(Obec(code=_code(element, "obi:Kod"), name=_text(element, "obi:Nazev"),
                             okres_code=okres_code, kraj_code=kraj_code,
                             position=self._position(element)))
        return obce

    def obvody(self) -> list[Obvod]:
        return [
            Obvod(code=_code(element, "mpi:Kod"), name=_text(element, "mpi:Nazev"),
                  obec_code=_code(element, "mpi:Obec/obi:Kod"), position=self._position(element))
            for element in self._elements["Mop"]
        ]

    def mestske_casti(self) -> list[MestskaCast]:
        return [
            MestskaCast(code=_code(element, "mci:Kod"), name=_text(element, "mci:Nazev"),
                        obec_code=_code(element, "mci:Obec/obi:Kod"),
                        obvod_code=_optional_code(element, "mci:Mop/mpi:Kod"),
                        position=self._position(element))
            for element in self._elements["Momc"]
        ]

    def casti_obce(self) -> list[CastObce]:
        return [
            CastObce(code=_code(element, "coi:Kod"), name=_text(element, "coi:Nazev"),
                     obec_code=_code(element, "coi:Obec/obi:Kod"), position=self._position(element))
            for element in self._elements["CastObce"]
        ]

    def _position(self, element: ElementTree.Element) -> Position:
        """The unit's definition point. An obec's is a multipoint, whose first
        member is used."""
        pos = element.find(".//gml:pos", _NAMESPACES)
        if pos is None or pos.text is None:
            raise ValueError(f"RÚIAN element {element.get(_GML_ID)} has no definition point")
        x, y = (float(value) for value in pos.text.split())
        lon, lat = self._to_wgs84.transform(x, y)
        return Position(lat=round(lat, 6), lon=round(lon, 6))


def _text(element: ElementTree.Element, path: str) -> str:
    found = element.find(path, _NAMESPACES)
    if found is None or found.text is None:
        raise ValueError(f"RÚIAN element {element.get(_GML_ID)} has no {path}")
    return found.text


def _code(element: ElementTree.Element, path: str) -> int:
    return int(_text(element, path))


def _optional_code(element: ElementTree.Element, path: str) -> int | None:
    found = element.find(path, _NAMESPACES)
    return int(found.text) if found is not None and found.text is not None else None
