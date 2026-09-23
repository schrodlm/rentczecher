import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from html import escape

from rentczecher.adapters.scrapers.base import Listing
from rentczecher.domain.listing import DisappearedListing
from rentczecher.services.notify import Notification

log = logging.getLogger("rentczecher")

NBSP = "\u00a0"  # Non-breaking space (works in both HTML and plain text)


def _safe_url(url: str) -> str:
    if url and url.startswith(("https://", "http://")):
        return escape(url, quote=True)
    return "#"


def _format_price(price: int, is_rent: bool) -> str:
    """Format price with non-breaking spaces as thousand separator + Kč."""
    formatted = f"{price:,}".replace(",", NBSP)
    if is_rent:
        return f"{formatted}{NBSP}Kč/měsíc"
    return f"{formatted}{NBSP}Kč"


def _format_price_plain(price: int, is_rent: bool) -> str:
    """Format price for plain text (regular spaces)."""
    formatted = f"{price:,}".replace(",", " ")
    if is_rent:
        return f"{formatted} Kč/měsíc"
    return f"{formatted} Kč"


def _render_card(listing: Listing, is_rent: bool) -> str:
    source = escape(listing.source)
    title = escape(listing.title)
    location = escape(listing.location)
    disposition = escape(listing.disposition) if listing.disposition else ""
    url = _safe_url(listing.url)

    badge_colors = {
        "sreality": ("background:#e8f0fe;color:#1a73e8;", "Sreality"),
        "bezrealitky": ("background:#fce8e6;color:#d93025;", "Bezrealitky"),
        "remax": ("background:#e6f4ea;color:#1e8e3e;", "RE/MAX"),
    }
    badge_style, badge_label = badge_colors.get(listing.source, ("background:#eee;color:#333;", source))

    # Image - natural aspect ratio, constrained width, no clipping
    img_html = ""
    if listing.image_url:
        img_url = _safe_url(listing.image_url)
        alt_text = escape(f"{listing.title} - {listing.disposition or ''} {listing.location}".strip(" -"))
        img_html = (
            f'<div style="width:100%;background:#f0f0f0;">'
            f'<img src="{img_url}" alt="{alt_text}" width="660" '
            f'style="width:100%;max-width:660px;height:auto;display:block;border:0;" />'
            f'</div>'
        )

    # Price
    price_str = _format_price(listing.price, is_rent)
    price_html = f'<div style="font-size:20px;font-weight:700;color:#1a8917;margin-bottom:8px;">{price_str}'

    if listing.price_drop_from:
        old_price = _format_price(listing.price_drop_from, is_rent)
        savings = listing.price_drop_from - listing.price
        savings_str = f"{savings:,}".replace(",", NBSP)
        price_html += (
            f' <span style="font-size:13px;color:#d93025;font-weight:600;">'
            f'SLEVA z {old_price} (-{savings_str}{NBSP}Kč)</span>'
        )

    if listing.charges and is_rent:
        charges_str = f"{listing.charges:,}".replace(",", NBSP)
        price_html += f' <span style="font-size:13px;color:#888;">+{NBSP}{charges_str} poplatky</span>'

    price_html += '</div>'

    # Details
    details = []
    if disposition:
        details.append(disposition)
    if listing.size_m2:
        details.append(f"{listing.size_m2}{NBSP}m&sup2;")
        if is_rent and listing.size_m2 > 0:
            ppm2 = round(listing.price / listing.size_m2)
            details.append(f"{ppm2}{NBSP}Kč/m&sup2;")
    if listing.land_m2:
        land_str = f"{listing.land_m2:,}".replace(",", NBSP)
        details.append(f"pozemek {land_str}{NBSP}m&sup2;")
    if location:
        details.append(location)

    details_html = " &middot; ".join(
        f'<span style="display:inline-block;margin-right:4px;">{d}</span>' for d in details
    )

    # Score badge
    score_html = ""
    if listing.score > 0:
        if listing.score >= 70:
            score_color = "#1a8917"
        elif listing.score >= 40:
            score_color = "#e8a317"
        else:
            score_color = "#888"
        score_html = (
            f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
            f'font-size:11px;font-weight:700;background:{score_color};color:#fff;margin-right:4px;">'
            f'{listing.score}%</span>'
        )

    # Cross-source badge
    cross_html = ""
    if listing.cross_source:
        sites = ", ".join(listing.cross_source)
        cross_html = (
            f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
            f'font-size:11px;background:#f0f0f0;color:#555;margin-right:4px;">'
            f'také na: {escape(sites)}</span>'
        )

    # Maps link - prefer address search for accuracy (GPS from some sources is approximate)
    maps_html = ""
    if listing.location:
        from urllib.parse import quote as url_quote
        maps_query = url_quote(f"{listing.location}, Česko")
        maps_url = f"https://maps.google.com/?q={maps_query}"
        maps_html = f' <a href="{escape(maps_url, quote=True)}" style="font-size:12px;color:#1a73e8;text-decoration:none;">[mapa]</a>'
    elif listing.lat is not None and listing.lon is not None:
        maps_url = f"https://maps.google.com/?q={listing.lat},{listing.lon}"
        maps_html = f' <a href="{escape(maps_url, quote=True)}" style="font-size:12px;color:#1a73e8;text-decoration:none;">[mapa]</a>'

    card_border = "border-left:4px solid #d93025;" if listing.price_drop_from else ""

    return f"""
    <div style="background:#fff;border-radius:8px;overflow:hidden;margin-bottom:16px;border:1px solid #e0e0e0;{card_border}">
      {img_html}
      <div style="padding:16px;">
        <div style="font-size:16px;font-weight:600;margin:0 0 8px;">
          <a href="{url}" style="color:#1a73e8;text-decoration:none;">{title}</a>{maps_html}
        </div>
        {price_html}
        <div style="color:#555;font-size:13px;margin-bottom:8px;">{details_html}</div>
        {score_html}
        <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase;{badge_style}">{badge_label}</span>
        {cross_html}
      </div>
    </div>"""


def _render_disappeared_section(disappeared: list[DisappearedListing], is_rent: bool) -> str:
    if not disappeared:
        return ""
    rows = []
    for d in disappeared[:10]:
        title = escape(d.title or "?")
        price = d.price or 0
        url = _safe_url(d.url)
        price_str = _format_price(price, is_rent) if price else "?"
        rows.append(
            f'<div style="padding:8px 0;border-bottom:1px solid #eee;font-size:13px;">'
            f'<a href="{url}" style="color:#999;text-decoration:line-through;">{title}</a>'
            f' - {price_str}</div>'
        )
    extra = f'<div style="color:#999;font-size:12px;margin-top:8px;">...a dalších {len(disappeared) - 10}</div>' if len(disappeared) > 10 else ''
    return f"""
    <div style="margin-top:24px;padding:16px;background:#fff;border-radius:8px;border:1px solid #e0e0e0;">
      <div style="font-size:16px;font-weight:600;color:#d93025;margin-bottom:12px;">
        Zmizelo {len(disappeared)} nabídek
      </div>
      {''.join(rows)}
      {extra}
    </div>"""


def _subtitle(notification: Notification) -> str:
    new_count = sum(1 for l in notification.listings if not l.price_drop_from)
    drop_count = sum(1 for l in notification.listings if l.price_drop_from)
    parts = []
    if new_count:
        parts.append(f"{new_count} nových")
    if drop_count:
        parts.append(f"{drop_count} slev")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return ", ".join(parts) + f" ({now})"


def _render_html(notification: Notification) -> str:
    profile_name = notification.profile_name
    cards_html = "\n".join(_render_card(l, notification.is_rent) for l in notification.listings)
    disappeared_html = _render_disappeared_section(list(notification.disappeared), notification.is_rent)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{escape(profile_name)}</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;margin:0;padding:20px;">
<div style="max-width:700px;margin:0 auto;">
  <h1 style="color:#1a1a1a;font-size:22px;margin-bottom:4px;">{escape(profile_name)}</h1>
  <p style="color:#666;font-size:14px;margin-bottom:24px;">{_subtitle(notification)}</p>
  {cards_html}
  {disappeared_html}
  <p style="text-align:center;color:#999;font-size:12px;margin-top:24px;">Byt Watchdog</p>
</div>
</body>
</html>"""


def _render_plain(notification: Notification) -> str:
    lines = [f"{notification.profile_name} - {_subtitle(notification)}\n"]
    for l in notification.listings:
        extras = []
        if l.price_drop_from:
            extras.append(f"SLEVA z {_format_price_plain(l.price_drop_from, notification.is_rent)}")
        if l.land_m2:
            extras.append(f"pozemek {l.land_m2} m2")
        extra_str = " | ".join(extras)
        if extra_str:
            extra_str = f" | {extra_str}"
        lines.append(f"- [{l.score}%] {l.title} | "
                     f"{_format_price_plain(l.price, notification.is_rent)}{extra_str} | {l.url}")
    return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class SmtpNotifier:
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_address: str
    recipients: tuple[str, ...]

    def send(self, notification: Notification) -> bool:
        if not notification.listings:
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = notification.subject
        msg["From"] = self.from_address
        msg["To"] = ", ".join(self.recipients)
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain="byt-watchdog")
        msg.attach(MIMEText(_render_plain(notification), "plain", "utf-8"))
        msg.attach(MIMEText(_render_html(notification), "html", "utf-8"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_address, self.recipients, msg.as_string())
        log.info("Email sent to %s with %d listing(s)", ", ".join(self.recipients), len(notification.listings))
        return True


def build_smtp_notifier(email_cfg: dict, profile_id: str, recipients: list[str]) -> SmtpNotifier | None:
    if not recipients:
        return None
    return SmtpNotifier(
        smtp_host=email_cfg["smtp_host"],
        smtp_port=email_cfg["smtp_port"],
        smtp_user=email_cfg["smtp_user"],
        smtp_password=email_cfg["smtp_password"],
        from_address=email_cfg["from"],
        recipients=tuple(recipients),
    )


class NoRecipientsNotifier:
    """Stands in for a profile with no configured recipients: a run still
    persists its outcome, it just never sends anything. The warning only
    fires when there was actually something to notify about."""

    def __init__(self, profile_id: str):
        self._profile_id = profile_id

    def send(self, notification: Notification) -> bool:
        log.error("Profile %s has no 'to' recipients configured - skipping email", self._profile_id)
        return True
