import asyncio
import logging
import re

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


class Catalog:
    def __init__(self) -> None:
        self.cosmetics: dict = {}
        self.banners: dict = {}

    async def refresh(self, session: aiohttp.ClientSession) -> None:
        async with session.get(COSMETICS_URL) as resp:
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
        async with session.get(f"{COSMETICS_URL}/{cosmetic_id}") as resp:
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


async def build_locker(session: aiohttp.ClientSession, catalog: Catalog, athena: dict, banner_ids: list) -> dict:
    owned = parse_athena_items(athena)
    infos = await asyncio.gather(*[catalog.get(session, cid) for cid in owned])

    locker = {key: [] for key in TYPE_KEYS.values()}
    for (cid, styles), info in zip(owned.items(), infos):
        info = info or {}
        rarity = info.get("rarity", {}).get("displayValue", "Common")
        if cid in MYTHIC_SET:
            rarity = "Mythic"
        images = info.get("images", {})
        locker[TYPE_KEYS[get_cosmetic_type(cid)]].append({
            "id": cid,
            "name": info.get("name") or cid,
            "rarity": rarity,
            "series": (info.get("series") or {}).get("value"),
            "type": info.get("type", {}).get("value"),
            "images": {
                "icon": images.get("icon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/icon.png",
                "small_icon": images.get("smallIcon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/smallicon.png",
                "featured": images.get("featured"),
            },
            "owned_styles": styles,
            "is_exclusive": cid in EXCLUSIVE_SET,
            "is_mythic": cid in MYTHIC_SET,
            "in_catalog": bool(info),
        })

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
        items.sort(key=_sort_key)
    return locker
