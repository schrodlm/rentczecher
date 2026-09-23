from rentczecher.adapters.api.models import ListingModel, PortalHealthModel, ProfileModel
from rentczecher.adapters.api.run_manager import PortalHealthEntry
from rentczecher.domain.listing import InboxCard, SiblingSource


class TestProfileModel:
    def test_from_config_defaults_enabled_to_true(self):
        """A profile without an enabled key is enabled."""
        model = ProfileModel.from_config("matej", {"name": "Matěj"})
        assert model.model_dump() == {"id": "matej", "name": "Matěj", "enabled": True}

    def test_from_config_keeps_an_explicit_enabled_false(self):
        """A disabled profile stays disabled on the wire."""
        model = ProfileModel.from_config("matej", {"name": "Matěj", "enabled": False})
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
            location="Praha 7",
            size_m2=54,
            disposition="2+kk",
            first_seen_at="2026-09-01T00:00:00+00:00",
            viewed_at=None,
            favourited_at=None,
            price=25000,
            price_drop_from=27000,
            sibling_sources=(SiblingSource(source="bezrealitky", url="https://example.com/b"),),
        )
        assert ListingModel.from_card(card).model_dump() == {
            "id": "sreality:1",
            "source": "sreality",
            "url": "https://example.com/1",
            "title": "Byt 2+kk",
            "location": "Praha 7",
            "size_m2": 54,
            "disposition": "2+kk",
            "first_seen_at": "2026-09-01T00:00:00+00:00",
            "viewed_at": None,
            "favourited_at": None,
            "price": 25000,
            "price_drop_from": 27000,
            "sibling_sources": [{"source": "bezrealitky", "url": "https://example.com/b"}],
        }


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
