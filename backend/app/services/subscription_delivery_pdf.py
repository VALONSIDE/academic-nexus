"""Ephemeral bilingual subscription-notice PDFs.

The caller receives bytes only. No PDF, delivery assignment, or subscription
Key plaintext is written to a database or the server filesystem.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import code128, code93, qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


_SONG_FONT = "STSong-Light"


def _register_fonts() -> None:
    if _SONG_FONT not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(_SONG_FONT))


def _date(value: datetime) -> str:
    current = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _song_bold(c: canvas.Canvas, text: str, *, x: float, y: float, size: float, copies: int = 2) -> None:
    """Give the built-in Song CID font a restrained print-like weight."""
    c.setFont(_SONG_FONT, size)
    c.drawString(x, y, text)
    for offset in range(1, copies):
        c.drawString(x + offset * 0.14 * mm, y, text)


def _fitted_value(c: canvas.Canvas, value: str, font: str, *, width: float, size: float, minimum: float = 6.8) -> tuple[str, float]:
    """Keep variable institution and account labels inside their machine-card field."""
    current = size
    while current > minimum and c.stringWidth(value, font, current) > width:
        current -= 0.25
    if c.stringWidth(value, font, current) <= width:
        return value, current
    suffix = "..."
    clipped = value
    while clipped and c.stringWidth(clipped + suffix, font, current) > width:
        clipped = clipped[:-1]
    return (clipped + suffix if clipped else suffix), current


def _field(c: canvas.Canvas, label_zh: str, label_en: str, value: str, *, x: float, y: float, width: float) -> None:
    c.setStrokeColorRGB(0.08, 0.08, 0.08)
    c.setLineWidth(0.35)
    c.line(x, y - 5.7 * mm, x + width, y - 5.7 * mm)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    _song_bold(c, label_zh, x=x, y=y, size=7.8, copies=2)
    c.setFont("Helvetica-Bold", 6.4)
    c.drawRightString(x + width, y + 0.2 * mm, label_en.upper())
    c.setFillColorRGB(0.04, 0.04, 0.04)
    if any(ord(char) > 127 for char in value):
        text, size = _fitted_value(c, value, _SONG_FONT, width=width, size=10.5)
        _song_bold(c, text, x=x, y=y - 4.25 * mm, size=size, copies=2)
    else:
        text, size = _fitted_value(c, value, "Helvetica-Bold", width=width, size=10.3)
        c.setFont("Helvetica-Bold", size)
        c.drawString(x, y - 4.25 * mm, text)


def _qr_code(c: canvas.Canvas, value: str, *, x: float, y: float, size: float) -> None:
    widget = qr.QrCodeWidget(value)
    x0, y0, x1, y1 = widget.getBounds()
    width, height = x1 - x0, y1 - y0
    drawing = Drawing(
        size,
        size,
        transform=[size / width, 0, 0, size / height, -x0 * size / width, -y0 * size / height],
    )
    drawing.add(widget)
    renderPDF.draw(drawing, c, x, y)


def _linear_barcodes(c: canvas.Canvas, value: str, *, x: float, y: float, width: float) -> None:
    """Render a common Code 128 and a less-common Code 93, both encoding Key."""
    common = code128.Code128(value, barWidth=0.31 * mm, barHeight=10 * mm, humanReadable=False)
    uncommon = code93.Standard93(value, barWidth=0.3 * mm, barHeight=10 * mm, humanReadable=False)
    common.drawOn(c, x, y)
    uncommon.drawOn(c, x + width / 2, y)
    c.setFont("Helvetica-Bold", 5.9)
    c.drawCentredString(x + width * 0.23, y - 3.2 * mm, "CODE 128 / STANDARD")
    c.drawCentredString(x + width * 0.74, y - 3.2 * mm, "CODE 93 / EXTENDED")


def render_subscription_delivery_pdf(
    *,
    document_number: str,
    recipient_name: str,
    recipient_username: str,
    institution_name: str,
    institution_abbr: str,
    plan_code: str,
    subscription_key: str,
    generated_at: datetime,
    general_delivery: bool = False,
) -> bytes:
    """Render an IELTS-card inspired, bilingual, print-ready entitlement notice."""
    _register_fonts()
    stream = BytesIO()
    c = canvas.Canvas(stream, pagesize=A4, pageCompression=1, invariant=1)
    page_width, page_height = A4
    margin = 13 * mm
    left = margin + 7 * mm
    right = page_width - margin - 7 * mm

    # Monochrome machine-readable frame and registration marks.
    c.setStrokeColorRGB(0.04, 0.04, 0.04)
    c.setLineWidth(1.05)
    c.rect(margin, margin, page_width - 2 * margin, page_height - 2 * margin, stroke=1, fill=0)
    c.setLineWidth(0.35)
    c.rect(margin + 3 * mm, margin + 3 * mm, page_width - 2 * margin - 6 * mm, page_height - 2 * margin - 6 * mm, stroke=1, fill=0)
    for x, y, sx, sy in (
        (margin, page_height - margin, 1, -1),
        (page_width - margin, page_height - margin, -1, -1),
        (margin, margin, 1, 1),
        (page_width - margin, margin, -1, 1),
    ):
        c.setLineWidth(1.3)
        c.line(x, y, x + sx * 7 * mm, y)
        c.line(x, y, x, y + sy * 7 * mm)

    # Text-only masthead: deliberately no logo on the notice itself.
    c.setFillColorRGB(0.03, 0.03, 0.03)
    _song_bold(c, "智导未来订阅服务", x=left, y=page_height - margin - 12 * mm, size=15.5, copies=3)
    c.setFont("Helvetica-Bold", 8.8)
    c.drawString(left, page_height - margin - 19 * mm, "ACADEMICNEXUS SUBSCRIPTION SERVICE")
    c.setFont("Helvetica-Bold", 6.8)
    c.drawRightString(right, page_height - margin - 12 * mm, "OFFLINE ENTITLEMENT NOTICE / 02")
    c.setFont("Helvetica", 6.6)
    c.drawRightString(right, page_height - margin - 18.2 * mm, document_number)
    c.setLineWidth(0.6)
    c.line(left, page_height - margin - 26 * mm, right, page_height - margin - 26 * mm)

    _song_bold(c, "高级订阅权益通知单", x=left, y=page_height - margin - 41 * mm, size=23.5, copies=3)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(left, page_height - margin - 48.5 * mm, "PREMIUM SUBSCRIPTION ENTITLEMENT CARD")
    c.setFont(_SONG_FONT, 8.7)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(left, page_height - margin - 55 * mm, "本通知单由院校管理员离线签发，平台服务器不保留其中的订阅 Key 明文。")
    c.setFont("Helvetica", 7.1)
    c.drawString(left, page_height - margin - 60.3 * mm, "ISSUED OFFLINE BY THE INSTITUTION ADMINISTRATOR. THE PLATFORM DOES NOT RETAIN THIS KEY IN PLAIN TEXT.")

    split = left + (right - left) * 0.52
    start_y = page_height - margin - 74 * mm
    recipient_label = "通用发放" if general_delivery else "受益人"
    recipient_en = "GENERAL DELIVERY" if general_delivery else "RECIPIENT"
    account_label = "不指定账户" if general_delivery else "系统账户"
    account_en = "UNASSIGNED ACCOUNT" if general_delivery else "ACCOUNT"
    _field(c, recipient_label, recipient_en, recipient_name, x=left, y=start_y, width=split - left - 5 * mm)
    _field(c, account_label, account_en, recipient_username, x=split + 5 * mm, y=start_y, width=right - split - 5 * mm)
    _field(c, "适用院校", "APPLICABLE INSTITUTION", institution_name, x=left, y=start_y - 18.5 * mm, width=split - left - 5 * mm)
    _field(c, "院校识别码", "INSTITUTION CODE", institution_abbr, x=split + 5 * mm, y=start_y - 18.5 * mm, width=right - split - 5 * mm)
    _field(c, "订阅档位", "SUBSCRIPTION TIER", plan_code.upper(), x=left, y=start_y - 37 * mm, width=split - left - 5 * mm)
    period_value = "激活起一个自然月" if not general_delivery else "符合条件的本校账户激活起一个自然月"
    _field(c, "权益有效期", "ENTITLEMENT PERIOD", period_value, x=split + 5 * mm, y=start_y - 37 * mm, width=right - split - 5 * mm)

    key_y = start_y - 65 * mm
    c.setFillColorRGB(0.04, 0.04, 0.04)
    c.roundRect(left, key_y - 21.5 * mm, right - left, 31 * mm, 1.8 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    _song_bold(c, "订阅 Key（仅限上述院校使用）", x=left + 5 * mm, y=key_y + 2.2 * mm, size=8.3, copies=2)
    c.setFont("Helvetica-Bold", 6.9)
    c.drawRightString(right - 5 * mm, key_y + 2.2 * mm, "REDEEM FROM YOUR SUBSCRIPTION PAGE")
    c.setFont("Helvetica-Bold", 23)
    c.drawCentredString((left + right) / 2, key_y - 11.8 * mm, subscription_key)

    note_y = key_y - 38 * mm
    c.setFillColorRGB(0.05, 0.05, 0.05)
    _song_bold(c, "使用说明", x=left, y=note_y, size=8.8, copies=2)
    c.setFont("Helvetica-Bold", 7.2)
    c.drawString(left + 22 * mm, note_y, "REDEMPTION NOTES")
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.setFont(_SONG_FONT, 7.6)
    chinese_notes = (
        "1. 登录对应账户，在“订阅”页面输入本 Key 完成激活；激活后 Key 立即失效。",
        "2. Key 与上述院校绑定，系统将以实时校验结果为准，不能跨校使用。",
        "3. 请妥善保管本通知单；平台不保存 Key 明文，遗失后无法从服务器找回。",
    )
    english_notes = (
        "1. Sign in and redeem this Key on the Subscription page. It is invalid immediately after redemption.",
        "2. The Key is bound to the institution above and cannot be used across institutions.",
        "3. Keep this notice secure. The platform cannot recover a lost plain-text Key.",
    )
    for index, (zh, en) in enumerate(zip(chinese_notes, english_notes, strict=True)):
        y = note_y - (index + 1) * 5.3 * mm
        c.drawString(left, y, zh)
        c.setFont("Helvetica", 5.75)
        c.drawString(left, y - 2.75 * mm, en)
        c.setFont(_SONG_FONT, 7.6)

    # Machine-readable Key zone: common QR and Code 128 plus less-common Code 93.
    code_top = margin + 17 * mm
    c.setLineWidth(0.35)
    c.line(left, code_top + 30.5 * mm, right, code_top + 30.5 * mm)
    c.setFillColorRGB(0.08, 0.08, 0.08)
    _song_bold(c, "机器可读 Key 区", x=left, y=code_top + 24.5 * mm, size=7.9, copies=2)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(left + 32 * mm, code_top + 24.7 * mm, "MACHINE-READABLE KEY ZONE")
    _qr_code(c, subscription_key, x=left, y=code_top, size=19 * mm)
    c.setFont("Helvetica-Bold", 5.9)
    c.drawCentredString(left + 9.5 * mm, code_top - 3.3 * mm, "QR / STANDARD")
    _linear_barcodes(c, subscription_key, x=left + 29 * mm, y=code_top + 1 * mm, width=right - left - 29 * mm)
    c.setFillColorRGB(0.28, 0.28, 0.28)
    c.setFont("Helvetica", 5.9)
    c.drawRightString(right, margin + 7 * mm, f"ISSUED { _date(generated_at) }  |  {document_number}")
    c.showPage()
    c.save()
    return stream.getvalue()
