from rentczecher_engine.adapters.api.models import ListingModel, PortalHealthModel, ProfileModel
from rentczecher_engine.adapters.api.run_manager import PortalHealthEntry
from rentczecher_engine.domain.disposition import Disposition
from rentczecher_engine.domain.listing import InboxCard, SiblingSource
from tests.profiles import profile


class TestProfileModel:
    def test_a_paused_profile_is_not_enabled(self):
        """A paused profile goes out as not enabled."""
        paused = profile(id="matej", name="Matěj", paused_at="2026-10-04T00:00:00+00:00")
        model = ProfileModel.from_profile(paused)
        assert model.enabled is False


class TestListingModel:
    def test_from_card_maps_every_field_by_name(self):
        """from_card carries every inbox card field into the wire model,
        siblings included."""
        card = InboxCard(
            id="sreality:1",
            source="sreality",
            url="https://example.com/1",
            title="Byt 2+kk",
            location_raw_text="Praha 7",
            property_location=None,
            size_m2=54,
            disposition_raw_text="2+kk",
            disposition=Disposition(rooms=2, kitchen="kitchenette"),
            first_seen_at="2026-09-01T00:00:00+00:00",
            viewed_at=None,
            favourited_at=None,
            price=25000,
            price_drop_from=27000,
            sibling_sources=(SiblingSource(source="bezrealitky", url="https://example.com/b"),),
        )
        assert ListingModel.from_card(card, None).model_dump() == {
            "id": "sreality:1",
            "source": "sreality",
            "url": "https://example.com/1",
            "title": "Byt 2+kk",
            "location_raw_text": "Praha 7",
            "resolved_location": None,
            "size_m2": 54,
            "disposition_raw_text": "2+kk",
            "disposition": "2+kk",
            "first_seen_at": "2026-09-01T00:00:00+00:00",
            "viewed_at": None,
            "favourited_at": None,
            "price": 25000,
            "price_drop_from": 27000,
            "sibling_sources": [{"source": "bezrealitky", "url": "https://example.com/b"}],
        }

    def test_from_card_sends_no_disposition_when_the_raw_text_names_none(self):
        """A raw text naming no layout maps to a null disposition."""
        card = InboxCard(
            id="sreality:1",
            source="sreality",
            url="https://example.com/1",
            title="Rodinný dům",
            location_raw_text=None,
            property_location=None,
            size_m2=None,
            disposition_raw_text="Rodinný",
            disposition=None,
            first_seen_at="2026-09-01T00:00:00+00:00",
            viewed_at=None,
            favourited_at=None,
            price=None,
            price_drop_from=None,
            sibling_sources=(),
        )
        assert ListingModel.from_card(card, None).disposition is None


class TestPortalHealthModel:
    def test_from_entry_folds_the_portal_name_in(self):
        """from_entry pairs the health entry with the portal it belongs to."""
        entry = PortalHealthEntry(
            status="ok", error=None, listing_count=143, checked_at="2026-09-01T00:00:00+00:00")
        assert PortalHealthModel.from_entry("sreality", entry).model_dump() == {
            "portal": "sreality",
            "status": "ok",
            "error": None,
            "listing_count": 143,
            "checked_at": "2026-09-01T00:00:00+00:00",
        }
