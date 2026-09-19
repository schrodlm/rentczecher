"""Tests for notifier rendering.

Run: python3 -m pytest tests/test_notifier.py -v
"""

import email as email_lib
from email.header import decode_header

from rentczecher.adapters.notifiers.smtp import SmtpNotifier, _render_card
from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.search import SearchSpec
from rentczecher.services.diff import DiffResult
from rentczecher.services.notify import build_notification


def _make_listing(**kwargs):
    defaults = dict(
        id="sreality:1",
        source="sreality",
        title="Prodej domu 120 m2",
        price=3_000_000,
        location="Nekvasovy, okres Plzeň-jih",
        url="https://example.com/1",
    )
    defaults.update(kwargs)
    return Listing.build(**defaults)


class TestMapsLinkLocation:
    """Maps links use the listing's own location; no city is ever appended."""

    def test_non_prague_maps_link_has_no_praha(self):
        listing = _make_listing(location="Nekvasovy, okres Plzeň-jih")
        html = _render_card(listing, is_rent=False)
        assert "maps.google.com" in html
        assert "Praha" not in html

    def test_prague_listing_still_gets_maps_link(self):
        listing = _make_listing(location="Umělecká, Praha - Holešovice")
        html = _render_card(listing, is_rent=True)
        assert "maps.google.com" in html


class _RecordingSMTP:
    """Stands in for smtplib.SMTP, capturing the message handed to sendmail
    instead of opening a real connection."""

    sent: list = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, *args):
        pass

    def sendmail(self, from_addr, to_addrs, msg_string):
        type(self).sent.append((from_addr, list(to_addrs), msg_string))


class TestSmtpNotifierSend:
    """SmtpNotifier.send renders the same subject and body content the
    pipeline's diff produces, regardless of how the email actually gets
    delivered."""

    def test_sends_new_and_dropped_listings_with_a_combined_subject(self, monkeypatch):
        monkeypatch.setattr("rentczecher.adapters.notifiers.smtp.smtplib.SMTP", _RecordingSMTP)
        _RecordingSMTP.sent = []

        new_listing = _make_listing(id="sreality:new", title="Nový byt")
        dropped_listing = _make_listing(
            id="sreality:drop", title="Zlevněný byt", price=2_800_000
        ).with_annotations(price_drop_from=3_000_000)
        diff = DiffResult(new=[new_listing], price_drops=[dropped_listing], disappeared=[])
        spec = SearchSpec(offer_type="sale", estate_type="house", place="domazlice-okres")
        notification = build_notification(diff, {"name": "Test profil"}, spec)

        notifier = SmtpNotifier(
            smtp_host="smtp.example.com", smtp_port=587, smtp_user="user",
            smtp_password="secret", from_address="bot@example.com",
            recipients=("owner@example.com",),
        )

        assert notifier.send(notification) is True
        assert len(_RecordingSMTP.sent) == 1
        from_addr, to_addrs, msg_string = _RecordingSMTP.sent[0]
        assert from_addr == "bot@example.com"
        assert to_addrs == ["owner@example.com"]

        msg = email_lib.message_from_string(msg_string)
        subject_bytes, encoding = decode_header(msg["Subject"])[0]
        subject = subject_bytes.decode(encoding or "ascii")
        assert subject == "Test profil: 1 nových nabídek, 1 slev"
        parts = {part.get_content_type(): part.get_payload(decode=True).decode("utf-8")
                for part in msg.walk() if part.get_content_type() in ("text/plain", "text/html")}
        assert "Nový byt" in parts["text/plain"]
        assert "Zlevněný byt" in parts["text/plain"]
        assert "Nový byt" in parts["text/html"]
        assert "SLEVA" in parts["text/html"]

    def test_nothing_notable_sends_no_email(self, monkeypatch):
        monkeypatch.setattr("rentczecher.adapters.notifiers.smtp.smtplib.SMTP", _RecordingSMTP)
        _RecordingSMTP.sent = []

        diff = DiffResult(new=[], price_drops=[], disappeared=[])
        spec = SearchSpec(offer_type="rent", estate_type="flat", place="praha-7")
        notification = build_notification(diff, {"name": "Test profil"}, spec)

        notifier = SmtpNotifier(
            smtp_host="smtp.example.com", smtp_port=587, smtp_user="user",
            smtp_password="secret", from_address="bot@example.com",
            recipients=("owner@example.com",),
        )

        assert notifier.send(notification) is True
        assert _RecordingSMTP.sent == []
