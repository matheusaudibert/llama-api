import asyncio
import hashlib
import io
import logging
import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from .cosmetics import Catalog, category_of, cosmetic_entry, sort_items

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).parent / "assets"
FONT_PATH = ASSETS / "font.ttf"
LOGO_PATH = ASSETS / "epic-games.png"
ICON_CACHE = Path(tempfile.gettempdir()) / "llama-api-icons"
BRASILIA = timezone(timedelta(hours=-3))  # no DST since 2019

CARD = 256
MAX_WIDTH = 2048
MIN_COLS = 6
ITALIC_SHEAR = 0.2
BACKGROUND = (20, 20, 20, 255)
SUBTITLE = (150, 150, 150, 255)
NICK = (225, 225, 225, 255)
DOWNLOAD_CONCURRENCY = 16

SQUARES = {
    "common": "commun",
    "uncommon": "uncommun",
    "rare": "rare",
    "epic": "epico",
    "legendary": "legendary",
    "mythic": "mitico",
    "icon series": "idolo",
    "dark series": "dark",
    "star wars series": "starwars",
    "marvel series": "marvel",
    "dc series": "dc",
    "gaming legends series": "serie",
    "shadow series": "shadow",
    "slurp series": "slurp",
    "lava series": "lava",
    "frozen series": "hielo",
}

TITLES = {
    "skins": "TRAJES",
    "backpacks": "MOCHILAS",
    "pickaxes": "FERRAMENTAS DE COLETA",
    "gliders": "ASAS-DELTAS",
    "emotes": "GESTOS",
    "mythics": "MÍTICOS",
}
MYTHIC_CATEGORIES = ["skins", "backpacks", "pickaxes", "gliders", "emotes"]

_squares: dict[str, Image.Image] = {}


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size)


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int) -> ImageFont.FreeTypeFont:
    font = _font(size)
    while size > 8 and draw.textlength(text, font=font) > max_width:
        size -= 1
        font = _font(size)
    return font


def _square(rarity: str, series: str | None) -> Image.Image:
    name = SQUARES.get(rarity.lower()) or ("serie" if series else "commun")
    if name not in _squares:
        _squares[name] = Image.open(ASSETS / "squares" / f"{name}.png").convert("RGBA").resize((CARD, CARD), Image.Resampling.LANCZOS)
    return _squares[name]


async def _fetch_icon(session: aiohttp.ClientSession, sem: asyncio.Semaphore, item: dict) -> bytes | None:
    # keyed by URL too: an OG style has its own image
    url_hash = hashlib.sha1((item["images"]["icon"] or "").encode()).hexdigest()[:10]
    path = ICON_CACHE / f"{item['id']}-{url_hash}.png"
    if path.exists():
        return path.read_bytes()

    async with sem:
        for url in (item["images"]["icon"], item["images"]["small_icon"]):
            if not url:
                continue
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        break
            except aiohttp.ClientError as e:
                logger.warning(f"Could not download icon {url}: {e}")
        else:
            return None

    try:
        icon = Image.open(io.BytesIO(data)).convert("RGBA").resize((CARD, CARD), Image.Resampling.LANCZOS)
    except UnidentifiedImageError:
        return None
    out = io.BytesIO()
    icon.save(out, "PNG")
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.getvalue())
    return out.getvalue()


def _card(item: dict, icon: bytes | None) -> Image.Image:
    card = _square(item["rarity"], item["series"]).copy()
    if icon:
        fg = Image.open(io.BytesIO(icon)).convert("RGBA")
        card.alpha_composite(fg)

    bar_y = int(CARD * 0.84)
    bar = Image.new("RGBA", (CARD, CARD - bar_y), (0, 0, 0, int(255 * 0.55)))
    card.alpha_composite(bar, (0, bar_y))

    draw = ImageDraw.Draw(card)
    name = item["name"].upper()
    font = _fit_font(draw, name, CARD - 20, 30)
    # center on the cap height: "lm" centers on ascender/descender, which sits the uppercase text too low
    _, cap_top, _, baseline = font.getbbox("H", anchor="ls")
    y = bar_y + (CARD - bar_y) / 2 - (cap_top + baseline) / 2
    draw.text((10, y), name, font=font, fill="white", anchor="ls")
    return card


def _italic(text: str, font: ImageFont.FreeTypeFont, fill) -> Image.Image:
    left, top, right, bottom = font.getbbox(text)
    w, h = right - left, bottom - top
    shift = int(h * ITALIC_SHEAR)
    layer = Image.new("RGBA", (w + shift, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((-left, -top), text, font=font, fill=fill)
    return layer.transform(layer.size, Image.Transform.AFFINE, (1, ITALIC_SHEAR, -shift, 0, 1, 0), Image.Resampling.BICUBIC)


def _scaled(path: Path, height: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img.resize((max(1, int(img.width * height / img.height)), height), Image.Resampling.LANCZOS)


def _logo(height: int) -> Image.Image:
    if LOGO_PATH.exists():
        return _scaled(LOGO_PATH, height)

    # fallback until api/assets/epic-games.png is added: white shield with the wordmark
    w = int(height * 0.78)
    logo = Image.new("RGBA", (w, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo)
    tip = int(height * 0.82)
    draw.polygon([(0, 0), (w - 1, 0), (w - 1, tip), (w // 2, height - 1), (0, tip)], fill="white")
    epic = _fit_font(draw, "EPIC", int(w * 0.8), int(height * 0.42))
    games = _fit_font(draw, "GAMES", int(w * 0.6), int(height * 0.16))
    draw.text((w // 2, int(height * 0.36)), "EPIC", font=epic, fill="black", anchor="mm")
    draw.text((w // 2, int(height * 0.66)), "GAMES", font=games, fill="black", anchor="mm")
    return logo


def _header(width: int, height: int, category: str, count: int, display_name: str) -> Image.Image:
    header = Image.new("RGBA", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(header)
    pad = height // 8

    icon = _scaled(ASSETS / "categories" / f"{category}.png", int(height * 0.8))
    header.alpha_composite(icon, (pad, (height - icon.height) // 2))
    x = pad + icon.width + pad

    # the slanted divider between the icon and the title
    bar_w, bar_h = max(4, height // 22), int(height * 0.8)
    bar_top = (height - bar_h) // 2
    slant = int(bar_h * ITALIC_SHEAR)
    draw.polygon(
        [(x + slant, bar_top), (x + slant + bar_w, bar_top), (x + bar_w, bar_top + bar_h), (x, bar_top + bar_h)],
        fill=SUBTITLE,
    )
    x += slant + bar_w + pad

    title = _italic("LOCKER", _font(int(height * 0.46)), "white")
    subtitle = _italic(f"{TITLES[category]} ({count})", _font(int(height * 0.27)), SUBTITLE)
    gap = height // 14
    top = (height - title.height - gap - subtitle.height) // 2
    header.alpha_composite(title, (x, top))
    header.alpha_composite(subtitle, (x, top + title.height + gap))
    left_end = x + max(title.width, subtitle.width) + 2 * pad

    logo = _logo(int(height * 0.42))
    name_width = width - pad - left_end - logo.width - pad
    name_font = _fit_font(draw, display_name, max(name_width, 40), int(height * 0.34))
    date_font = _font(int(height * 0.15))
    date = datetime.now(BRASILIA).strftime("%d/%m/%Y")

    name_w = int(draw.textlength(display_name, font=name_font))
    mid = height // 2 - int(height * 0.06)
    draw.text((width - pad, mid), display_name, font=name_font, fill=NICK, anchor="rm")
    draw.text((width - pad, mid + int(height * 0.22)), date, font=date_font, fill=SUBTITLE, anchor="rm")
    header.alpha_composite(logo, (width - pad - name_w - pad - logo.width, mid - logo.height // 2))
    return header


def _compose(category: str, items: list, icons: list, display_name: str) -> bytes:
    cols = max(MIN_COLS, math.ceil(math.sqrt(len(items))))
    rows = math.ceil(len(items) / cols)
    gap = 4
    cell = min(CARD, (MAX_WIDTH - gap) // cols - gap)
    gap = max(2, cell // 26)

    width = cols * (cell + gap) + gap
    header_h = max(120, width // 12)
    image = Image.new("RGBA", (width, header_h + rows * (cell + gap) + gap), BACKGROUND)
    image.alpha_composite(_header(width, header_h, category, len(items), display_name))

    for idx, (item, icon) in enumerate(zip(items, icons)):
        card = _card(item, icon)
        if cell != CARD:
            card = card.resize((cell, cell), Image.Resampling.LANCZOS)
        x = gap + (idx % cols) * (cell + gap)
        y = header_h + gap + (idx // cols) * (cell + gap)
        image.alpha_composite(card, (x, y))

    out = io.BytesIO()
    image.convert("RGB").save(out, "PNG", optimize=True)
    return out.getvalue()


async def render_category(
    session: aiohttp.ClientSession, catalog: Catalog, category: str, owned: dict, display_name: str, language: str = "en"
) -> bytes | None:
    """owned is {cosmetic_id: owned_styles}. Returns PNG bytes, or None when nothing is in the category."""
    wanted = MYTHIC_CATEGORIES if category == "mythics" else [category]
    ids = [cid for cid in owned if category_of(cid) in wanted]
    infos = await asyncio.gather(*[catalog.get(session, cid) for cid in ids])
    items = [cosmetic_entry(cid, owned[cid], info, catalog.names_pt.get(cid)) for cid, info in zip(ids, infos)]
    if category == "mythics":
        items = [i for i in items if i["is_mythic"]]
    if not items:
        return None

    sort_items(items)
    # mythics: skins first, then backpacks, pickaxes, gliders and emotes
    items.sort(key=lambda i: wanted.index(category_of(i["id"])))
    if language == "pt-BR":
        # after sorting, so the order is the same in both languages
        for item in items:
            item["name"] = item["name_pt"]

    sem = asyncio.Semaphore(DOWNLOAD_CONCURRENCY)
    icons = await asyncio.gather(*[_fetch_icon(session, sem, item) for item in items])
    return await asyncio.to_thread(_compose, category, items, icons, display_name)
