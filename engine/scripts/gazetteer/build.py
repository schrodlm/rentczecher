"""Builds a gazetteer file from the two RÚIAN files."""

from datetime import date
from pathlib import Path

from .database import GazetteerDatabase
from .ruian.address_dump import RuianAddressDump
from .ruian.state_file import RuianStateFile


def build_gazetteer(state_file: Path, address_dump: Path, out: Path) -> None:
    """Writes every place into a new gazetteer at out. Parents go in before
    their children, so each foreign key is checked as its row arrives."""
    print(f"Reading {state_file.name}")
    state = RuianStateFile(state_file)
    print(f"Reading {address_dump.name}")
    dump = RuianAddressDump(address_dump)

    database = GazetteerDatabase.create(out)
    try:
        database.set_meta("generated_at", date.today().isoformat())
        database.set_meta("source", f"{state_file.name} {address_dump.name}")
        database.insert_kraje(state.kraje())
        database.insert_okresy(state.okresy())
        database.insert_obce(state.obce())
        database.insert_obvody(state.obvody())
        database.insert_mestske_casti(state.mestske_casti())
        database.insert_casti_obce(state.casti_obce())
        database.insert_ulice(dump.ulice())
        database.insert_overlaps(dump.overlaps())
        database.commit()
    finally:
        database.close()
