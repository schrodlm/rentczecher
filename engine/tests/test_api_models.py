from rentczecher_engine.adapters.api.models import PhotoModel, PortalHealthModel, ProfileModel, TrackedPropertyModel
from rentczecher_engine.adapters.api.run_manager import PortalHealthEntry
from rentczecher_engine.domain.disposition import Disposition
from rentczecher_engine.domain.geo import GeoPoint
from rentczecher_engine.domain.property import TrackedProperty, SiblingSource
from tests.profiles import profile


class TestProfileModel:
    def test_a_paused_profile_goes_out_with_its_paused_at(self):
        """A paused profile goes out with the time it was paused."""
        paused = profile(id="matej", name="Matěj", paused_at="2026-10-04T00:00:00+00:00")
        model = ProfileModel.from_profile(paused, named_places={})
        assert model.paused_at == "2026-10-04T00:00:00+00:00"


class TestTrackedPropertyModel:
    def test_from_tracked_property_maps_every_field_by_name(self):
        """from_tracked_property carries every tracked property field into the wire model,
        siblings included."""
        card = TrackedProperty(
            id="prop-1",
            index=7,
            listing_id="sreality:1",
            source="sreality",
            url="https://example.com/1",
            title="Byt 2+kk",
            location_raw_text="Praha 7",
            property_location=None,
            point=GeoPoint(lat=50.1029, lon=14.4293),
            size_m2=54,
            land_m2=None,
            disposition_raw_text="2+kk",
            disposition=Disposition(rooms=2, kitchen="kitchenette"),
            first_seen_at="2026-09-01T00:00:00+00:00",
            viewed_at=None,
            favourited_at=None,
            updated_at=None,
            price=25000,
            price_drop_from=27000,
            sibling_sources=(SiblingSource(source="bezrealitky", url="https://example.com/b"),),
        )
        main_photo = PhotoModel(url="/v1/photos/" + "a" * 32 + ".jpg?sig=s")
        assert TrackedPropertyModel.from_tracked_property(card, None, main_photo).model_dump() == {
            "id": "prop-1",
            "index": 7,
            "listing_id": "sreality:1",
            "source": "sreality",
            "url": "https://example.com/1",
            "title": "Byt 2+kk",
            "location_raw_text": "Praha 7",
            "resolved_location": None,
            "point": {"lat": 50.1029, "lon": 14.4293},
            "size_m2": 54,
            "land_m2": None,
            "disposition_raw_text": "2+kk",
            "disposition": "2+kk",
            "first_seen_at": "2026-09-01T00:00:00+00:00",
            "viewed_at": None,
            "favourited_at": None,
            "updated_at": None,
            "price": 25000,
            "price_drop_from": 27000,
            "sibling_sources": [{"source": "bezrealitky", "url": "https://example.com/b"}],
            "main_photo": {"url": "/v1/photos/" + "a" * 32 + ".jpg?sig=s"},
        }

    def test_from_tracked_property_sends_no_disposition_when_the_raw_text_names_none(self):
        """A raw text naming no layout maps to a null disposition."""
        card = TrackedProperty(
            id="prop-1",
            index=7,
            listing_id="sreality:1",
            source="sreality",
            url="https://example.com/1",
            title="Rodinný dům",
            location_raw_text=None,
            property_location=None,
            point=None,
            size_m2=None,
            land_m2=None,
            disposition_raw_text="Rodinný",
            disposition=None,
            first_seen_at="2026-09-01T00:00:00+00:00",
            viewed_at=None,
            favourited_at=None,
            updated_at=None,
            price=None,
            price_drop_from=None,
            sibling_sources=(),
        )
        assert TrackedPropertyModel.from_tracked_property(card, None, None).disposition is None


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
