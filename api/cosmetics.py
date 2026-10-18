import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import aiohttp

from .cosmetic_data import (
    exclusive_cosmetics,
    get_cosmetic_type,
    mythic_ids,
    rarity_priority,
    sub_order,
)

logger = logging.getLogger(__name__)

idpattern = re.compile(r"athena(.*?):(.*?)_(.*?)")

COSMETICS_URL = "https://fortnite-api.com/v2/cosmetics/br"
BANNERS_URL = "https://fortnite-api.com/v1/banners"
# include shopHistory, used to tell whether a "mythic" item came back to the shop
CATALOG_PARAMS = {"responseFlags": 4}

TYPE_KEYS = {
    "Skins": "skins",
    "Mochilas": "backpacks",
    "Picos": "pickaxes",
    "Gestos": "emotes",
    "Planeadores": "gliders",
    "Envolturas": "wraps",
    "Sprays": "sprays",
    "Others": "others",
    "Banners": "banners",
}

MYTHIC_SET = {m.lower() for m in mythic_ids}
EXCLUSIVE_SET = {e.lower() for e in exclusive_cosmetics}

# A mythic that was sold in the item shop within this window is no longer rare
MYTHIC_RERELEASE_WINDOW = timedelta(days=730)

# Items re-released to everyone, where only the original owners have this style.
# Without the style they are a normal copy of the item.
OG_STYLES = {
    "cid_028_athena_commando_f": ("mat3", "OG Renegade Raider"),          # Black & Gold
    "cid_017_athena_commando_m": ("stage2", "OG Aerial Assault Trooper"),  # Black & Gold
    "cid_547_athena_commando_f_meteorwoman": ("mat3", "OG Paradigm"),      # Reality Warrior
    "cid_029_athena_commando_f_halloween": ("mat3", "OG Ghoul Trooper"),   # Pink
    "cid_030_athena_commando_m_halloween": ("mat1", "OG Skull Trooper"),   # Purple Glow
    "cid_315_athena_commando_m_teriyakifish": ("stage3", "World Cup Fishstick"),
}


class Catalog:
    def __init__(self) -> None:
        self.cosmetics: dict = {}
        self.banners: dict = {}

    async def refresh(self, session: aiohttp.ClientSession) -> None:
        async with session.get(COSMETICS_URL, params=CATALOG_PARAMS) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.cosmetics = {c["id"].lower(): c for c in data.get("data", [])}
            else:
                logger.warning(f"Could not load cosmetics catalog ({resp.status})")

        async with session.get(BANNERS_URL) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.banners = {b["id"].lower(): b for b in data.get("data", [])}
            else:
                logger.warning(f"Could not load banners catalog ({resp.status})")

        logger.info(f"Catalog loaded: {len(self.cosmetics)} cosmetics, {len(self.banners)} banners")

    async def refresh_forever(self, session: aiohttp.ClientSession, every_seconds: int) -> None:
        while True:
            await asyncio.sleep(every_seconds)
            try:
                await self.refresh(session)
            except Exception as e:
                logger.error(f"Catalog refresh failed: {e}")

    async def get(self, session: aiohttp.ClientSession, cosmetic_id: str) -> dict | None:
        cid_lower = cosmetic_id.lower()
        if cid_lower in self.cosmetics:
            return self.cosmetics[cid_lower]

        # released after the last refresh: ask fortnite-api for this one item
        async with session.get(f"{COSMETICS_URL}/{cosmetic_id}", params=CATALOG_PARAMS) as resp:
            if resp.status != 200:
                return None
            data = (await resp.json()).get("data")
            if data:
                self.cosmetics[cid_lower] = data
            return data


def parse_athena_items(athena: dict) -> dict:
    """Returns {cosmetic_id: owned_styles} for every athena cosmetic in the profile."""
    owned = {}
    for item in athena.get("items", {}).values():
        tid = item.get("templateId", "").lower()
        if "loadingscreen_character_lineup" in tid or not idpattern.match(tid):
            continue
        cid = tid.split(":")[1]
        styles = owned.setdefault(cid, [])
        for variant in item.get("attributes", {}).get("variants", []):
            styles.extend(variant.get("owned", []))
    return owned


def _sort_key(item: dict):
    return (
        rarity_priority.get(item["rarity"], 999),
        sub_order.get(item["id"], 9999),
        item["name"].lower(),
    )


def category_of(cosmetic_id: str) -> str:
    return TYPE_KEYS[get_cosmetic_type(cosmetic_id)]


def _recently_in_shop(info: dict) -> bool:
    history = info.get("shopHistory") or []
    if not history:
        return False
    last = datetime.fromisoformat(history[-1].replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - last < MYTHIC_RERELEASE_WINDOW


def _og_style(cid: str, styles: list) -> tuple[str, str] | None:
    """(style tag, OG name) when the player owns the original owners' style."""
    og = OG_STYLES.get(cid)
    if og and og[0] in {s.lower() for s in styles}:
        return og
    return None


def _style_image(info: dict, tag: str) -> str | None:
    for variant in info.get("variants") or []:
        for option in variant.get("options", []):
            if option.get("tag", "").lower() == tag:
                return option.get("image")
    return None


def cosmetic_entry(cid: str, styles: list, info: dict | None) -> dict:
    info = info or {}
    rarity = info.get("rarity", {}).get("displayValue", "Common")
    og = _og_style(cid, styles)
    if cid in OG_STYLES:
        is_mythic = og is not None
    else:
        is_mythic = cid in MYTHIC_SET and not _recently_in_shop(info)
    if is_mythic:
        rarity = "Mythic"
    images = info.get("images", {})
    return {
        "id": cid,
        "name": og[1] if og else info.get("name") or cid,
        "rarity": rarity,
        "series": (info.get("series") or {}).get("value"),
        "type": info.get("type", {}).get("value"),
        "images": {
            "icon": (og and _style_image(info, og[0])) or images.get("icon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/icon.png",
            "small_icon": images.get("smallIcon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/smallicon.png",
            "featured": images.get("featured"),
        },
        "owned_styles": styles,
        "is_exclusive": cid in EXCLUSIVE_SET,
        "is_mythic": is_mythic,
        "in_catalog": bool(info),
    }


def sort_items(items: list) -> None:
    items.sort(key=_sort_key)


async def build_locker(session: aiohttp.ClientSession, catalog: Catalog, athena: dict, banner_ids: list) -> dict:
    owned = parse_athena_items(athena)
    infos = await asyncio.gather(*[catalog.get(session, cid) for cid in owned])

    locker = {key: [] for key in TYPE_KEYS.values()}
    for (cid, styles), info in zip(owned.items(), infos):
        locker[category_of(cid)].append(cosmetic_entry(cid, styles, info))

    for bn in banner_ids:
        info = catalog.banners.get(bn)
        if not info or not info.get("images", {}).get("icon"):
            continue
        cid = f"banner_{bn}"
        locker["banners"].append({
            "id": cid,
            "name": info.get("devName") or cid,
            "rarity": "Mythic" if cid in MYTHIC_SET else "Uncommon",
            "series": None,
            "type": "banner",
            "images": {
                "icon": info["images"]["icon"],
                "small_icon": info["images"].get("smallIcon"),
                "featured": None,
            },
            "owned_styles": [],
            "is_exclusive": False,
            "is_mythic": cid in MYTHIC_SET,
            "in_catalog": True,
        })

    for items in locker.values():
        sort_items(items)
    return locker
