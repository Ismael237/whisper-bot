from __future__ import annotations

from io import BytesIO
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pilmoji import Pilmoji
from pilmoji.source import AppleEmojiSource as _EmojiSource


def _vertical_gradient(
    size: Tuple[int, int],
    top_rgb: Tuple[int, int, int],
    bottom_rgb: Tuple[int, int, int],
) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (w, h), top_rgb)
    top = Image.new("RGB", (w, h), bottom_rgb)
    # Create gradient mask
    mask = Image.new("L", (w, h))
    mask_draw = ImageDraw.Draw(mask)
    for y in range(h):
        # Linear gradient 0..255
        val = int(255 * (y / (h - 1)))
        mask_draw.line([(0, y), (w, y)], fill=val)
    base.paste(top, (0, 0), mask)
    return base


def _rounded_rect(
    size: Tuple[int, int],
    radius: int,
) -> Image.Image:
    w, h = size
    rect = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(rect)
    # Use (w-1, h-1) to avoid drawing outside the image bounds which can clip corners
    d.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=radius, fill=255)
    return rect


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    # simple greedy wrap
    words = text.split()
    lines = []
    current = []
    for w in words:
        test = (" ".join(current + [w])).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current.append(w)
        else:
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def _multiline_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    line_spacing: int,
) -> Tuple[int, int, int]:
    """Return (max_line_width, total_height, line_count) for given multiline text."""
    lines = text.split("\n") if text else [""]
    max_w = 0
    total_h = 0
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        max_w = max(max_w, w)
        total_h += h
        if i < len(lines) - 1:
            total_h += line_spacing
    return max_w, total_h, len(lines)


def _draw_multiline_centered(
    pm: Pilmoji,
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    box_w: int,
    line_spacing: int,
    fill=(0, 0, 0),
) -> None:
    """Draw multiline text centered within a box width starting at (x,y)."""
    lines = text.split("\n") if text else [""]
    cy = y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        lx = x + (box_w - lw) // 2
        pm.text((lx, cy), line, font=font, fill=fill)
        cy += lh + (line_spacing if i < len(lines) - 1 else 0)


def create_share_card(
    message_text: str,
    bot_username: str,
    title_font_path: str,
    body_font_path: str,
    size: Tuple[int, int] = (1080, 0),
    title_text: str = "send me anonymous messages!",
) -> BytesIO:
    """Create a shareable PNG card with gradient header, rounded card, drop shadow, emoji rendering and Telegram footer.

    Returns BytesIO positioned at start.
    """
    W, _ = size

    # Card/container metrics based on width
    margin = int(W * 0.08)
    radius = int(W * 0.07)
    title_side_pad = int(W * 0.06)
    title_v_pad = int(W * 0.05)
    body_side_pad = int(W * 0.07)
    body_v_pad = int(W * 0.05)
    line_spacing_ratio = 0.35  # relative to font size

    # Fonts
    try:
        title_font = ImageFont.truetype(title_font_path, size=int(W * 0.070))
        body_font = ImageFont.truetype(body_font_path, size=int(W * 0.060))
    except Exception:
        # Fallback default
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Measurement context
    meas_img = Image.new("RGB", (W, W), (255, 255, 255))
    meas_draw = ImageDraw.Draw(meas_img)

    # Compute card width
    card_w = W - 2 * margin

    # Wrap and measure title (constrain to max 2 lines by reducing font size if needed)
    title_max_w = card_w - 2 * title_side_pad
    wrapped_title = _wrap_text(meas_draw, title_text, title_font, title_max_w)
    title_line_spacing = int(title_font.size * line_spacing_ratio)
    _, title_text_h, title_lines = _multiline_size(meas_draw, wrapped_title, title_font, title_line_spacing)
    # Reduce title font size iteratively until it fits within 2 lines
    while title_lines > 2 and title_font.size > 10:
        new_size = max(10, int(title_font.size * 0.94))
        try:
            title_font = ImageFont.truetype(title_font_path, size=new_size)
        except Exception:
            break
        wrapped_title = _wrap_text(meas_draw, title_text, title_font, title_max_w)
        title_line_spacing = int(title_font.size * line_spacing_ratio)
        _, title_text_h, title_lines = _multiline_size(meas_draw, wrapped_title, title_font, title_line_spacing)
    # Ensure top rounded corners have enough height to look good
    title_h = max(2 * radius - int(radius * 0.6), title_text_h + 2 * title_v_pad)

    # Wrap and measure body
    body_max_w = card_w - 2 * body_side_pad
    wrapped_body = _wrap_text(meas_draw, message_text, body_font, body_max_w)
    body_line_spacing = int(body_font.size * line_spacing_ratio)
    _, body_text_h, _ = _multiline_size(meas_draw, wrapped_body, body_font, body_line_spacing)
    # Body box height to ensure symmetric top/bottom padding
    body_h = body_text_h + 2 * body_v_pad

    # No footer: remove footer measurements entirely

    # Compute final card and canvas height
    card_h = title_h + body_h
    H = 2 * margin + card_h

    # Background gradient (Instagram-like pink -> orange)
    bg = _vertical_gradient((W, H), (255, 94, 98), (255, 163, 71))
    canvas = bg.convert("RGBA")

    # Shadows matching CSS:
    # box-shadow: 0px 1px 3px 0px rgba(0,0,0,0.1), 0px 6px 12px 0px rgba(0,0,0,0.08)
    # We'll draw two separate blurred rounded-rect shadows on full-size transparent layers
    shadow_layer_1 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow_layer_2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # Create masks for rounded card
    card_mask = _rounded_rect((card_w, card_h), radius)
    # First shadow: offset (0,1), blur 3, alpha 0.1
    tmp1 = Image.new("RGBA", (card_w, card_h), (0, 0, 0, int(255 * 0.10)))
    tmp1.putalpha(card_mask)
    shadow_layer_1.alpha_composite(tmp1, (margin + 0, margin + 1))
    shadow_layer_1 = shadow_layer_1.filter(ImageFilter.GaussianBlur(radius=3))
    # Second shadow: offset (0,6), blur 12, alpha 0.08
    tmp2 = Image.new("RGBA", (card_w, card_h), (0, 0, 0, int(255 * 0.08)))
    tmp2.putalpha(card_mask)
    shadow_layer_2.alpha_composite(tmp2, (margin + 0, margin + 6))
    shadow_layer_2 = shadow_layer_2.filter(ImageFilter.GaussianBlur(radius=12))
    # Composite shadows under card
    canvas.alpha_composite(shadow_layer_2)
    canvas.alpha_composite(shadow_layer_1)

    # Foreground card (white)
    card = Image.new("RGBA", (card_w, card_h), (255, 255, 255, 255))
    c_mask = _rounded_rect((card_w, card_h), radius)
    canvas.paste(card, (margin, margin), c_mask)

    # Title area with gradient overlay sized to content
    title_area = _vertical_gradient((card_w, title_h), (255, 108, 181), (255, 90, 90))
    # Clip title to rounded top corners only (mask must be black outside)
    title_mask = Image.new("L", (card_w, title_h), 0)
    d_mask = ImageDraw.Draw(title_mask)
    # Fill center top between arcs to avoid any white bar under the arcs
    d_mask.rectangle([(radius, 0), (card_w - radius, title_h)], fill=255)
    # Fill the area below the arc bottoms
    d_mask.rectangle([(0, radius), (card_w, title_h)], fill=255)
    d_mask.pieslice([(0, 0), (2 * radius, 2 * radius)], 180, 270, fill=255)
    d_mask.pieslice([(card_w - 2 * radius, 0), (card_w, 2 * radius)], 270, 360, fill=255)
    canvas.paste(title_area.convert("RGBA"), (margin, margin), title_mask)

    draw = ImageDraw.Draw(canvas)

    # Title text (centered horizontally, vertically centered within title area for equal top/bottom paddings)
    with Pilmoji(canvas, source=_EmojiSource) as pm:  # type: ignore
        ty = margin + (title_h - title_text_h) // 2
        _draw_multiline_centered(
            pm,
            draw,
            wrapped_title,
            title_font,
            margin + title_side_pad,
            ty,
            card_w - 2 * title_side_pad,
            title_line_spacing,
            fill=(255, 255, 255),
        )

    # Body text (centered and wrapped within side padding) on white area
    # Vertically center to ensure equal top/bottom paddings
    body_top = margin + title_h + (body_h - body_text_h) // 2
    with Pilmoji(canvas, source=_EmojiSource) as pm:  # type: ignore
        _draw_multiline_centered(
            pm,
            draw,
            wrapped_body,
            body_font,
            margin + body_side_pad,
            body_top,
            card_w - 2 * body_side_pad,
            body_line_spacing,
            fill=(30, 30, 30),
        )

    # No footer rendering

    # Export PNG
    out = BytesIO()
    canvas = canvas.convert("RGB")
    canvas.save(out, format="PNG", optimize=True)
    out.seek(0)
    return out