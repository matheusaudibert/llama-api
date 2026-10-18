import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import aiohttp

from .cosmetic_data import (
    exclusive_cosmetics,
    get_cosmetic_type,
    mythic_ids,
    rarity_priority,
    sub_order,
)
from .logs import fields
from .rarities import background_path

logger = logging.getLogger("api.catalog")

idpattern = re.compile(r"athena(.*?):(.*?)_(.*?)")

COSMETICS_URL = "https://fortnite-api.com/v2/cosmetics/br"
BANNERS_URL = "https://fortnite-api.com/v1/banners"
# include shopHistory, used to tell whether a "mythic" item came back to the shop
CATALOG_PARAMS = {"responseFlags": 4}
PT_LANGUAGE = "pt-BR"

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
# (style tag, OG name, Portuguese name template filled with the item's Portuguese name)
OG_STYLES = {
    "cid_028_athena_commando_f": ("mat3", "OG Renegade Raider", "OG {}"),          # Black & Gold
    "cid_017_athena_commando_m": ("stage2", "OG Aerial Assault Trooper", "OG {}"),  # Black & Gold
    "cid_547_athena_commando_f_meteorwoman": ("mat3", "OG Paradigm", "OG {}"),      # Reality Warrior
    "cid_029_athena_commando_f_halloween": ("mat3", "OG Ghoul Trooper", "OG {}"),   # Pink
    "cid_030_athena_commando_m_halloween": ("mat1", "OG Skull Trooper", "OG {}"),   # Purple Glow
    "cid_315_athena_commando_m_teriyakifish": ("stage3", "World Cup Fishstick", "{} da Copa do Mundo"),
}


class Catalog:
    def __init__(self) -> None:
        self.cosmetics: dict = {}
        self.names_pt: dict[str, str] = {}
        self.banners: dict = {}

    async def refresh(self, session: aiohttp.ClientSession) -> None:
        started = time.perf_counter()
        async with session.get(COSMETICS_URL, params=CATALOG_PARAMS) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.cosmetics = {c["id"].lower(): c for c in data.get("data", [])}
            else:
                logger.warning("Could not load the cosmetics catalog", extra=fields(status=resp.status))

        # only the names are kept, so the second catalog costs little memory
        async with session.get(COSMETICS_URL, params={"language": PT_LANGUAGE}) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.names_pt = {c["id"].lower(): c["name"].strip() for c in data.get("data", []) if c.get("name")}
            else:
                logger.warning("Could not load the Portuguese cosmetic names", extra=fields(status=resp.status))

        async with session.get(BANNERS_URL) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.banners = {b["id"].lower(): b for b in data.get("data", [])}
            else:
                logger.warning("Could not load the banners catalog", extra=fields(status=resp.status))

        logger.info("Catalog loaded", extra=fields(
            cosmetics=len(self.cosmetics),
            names_pt=len(self.names_pt),
            banners=len(self.banners),
            ms=round((time.perf_counter() - started) * 1000),
        ))

    async def refresh_forever(self, session: aiohttp.ClientSession, every_seconds: int) -> None:
        while True:
            await asyncio.sleep(every_seconds)
            try:
                await self.refresh(session)
            except Exception:
                # the previous catalog stays in memory
                logger.exception("Catalog refresh failed")

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
            logger.info("Fetched an item missing from the catalog", extra=fields(item=cid_lower))
            self.cosmetics[cid_lower] = data
            async with session.get(f"{COSMETICS_URL}/{cosmetic_id}", params={"language": PT_LANGUAGE}) as resp:
                if resp.status == 200:
                    name = ((await resp.json()).get("data") or {}).get("name")
                    if name:
                        self.names_pt[cid_lower] = name.strip()
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


def _og_style(cid: str, styles: list) -> tuple[str, str, str] | None:
    """(style tag, OG name, Portuguese template) when the player owns the original owners' style."""
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


def cosmetic_entry(cid: str, styles: list, info: dict | None, name_pt: str | None = None) -> dict:
    info = info or {}
    name = info.get("name") or cid
    name_pt = name_pt or name
    rarity = info.get("rarity", {}).get("displayValue", "Common")
    og = _og_style(cid, styles)
    if cid in OG_STYLES:
        is_mythic = og is not None
    else:
        is_mythic = cid in MYTHIC_SET and not _recently_in_shop(info)
    if is_mythic:
        rarity = "Mythic"
    images = info.get("images", {})
    series = (info.get("series") or {}).get("value")
    return {
        "id": cid,
        "name": og[1] if og else name,
        "name_pt": og[2].format(name_pt) if og else name_pt,
        "rarity": rarity,
        "series": series,
        "type": info.get("type", {}).get("value"),
        "images": {
            "icon": (og and _style_image(info, og[0])) or images.get("icon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/icon.png",
            "small_icon": images.get("smallIcon") or f"https://fortnite-api.com/images/cosmetics/br/{cid}/smallicon.png",
            "featured": images.get("featured"),
            "background": background_path(rarity, series),
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
        locker[category_of(cid)].append(cosmetic_entry(cid, styles, info, catalog.names_pt.get(cid)))

    for bn in banner_ids:
        entry = banner_entry(catalog, bn)
        if entry:
            locker["banners"].append(entry)

    for items in locker.values():
        sort_items(items)
    return locker


def banner_entry(catalog: Catalog, banner_id: str) -> dict | None:
    info = catalog.banners.get(banner_id)
    if not info or not info.get("images", {}).get("icon"):
        return None
    cid = f"banner_{banner_id}"
    rarity = "Mythic" if cid in MYTHIC_SET else "Uncommon"
    return {
        "id": cid,
        "name": info.get("devName") or cid,
        "name_pt": info.get("devName") or cid,
        "rarity": rarity,
        "series": None,
        "type": "banner",
        "images": {
            "icon": info["images"]["icon"],
            "small_icon": info["images"].get("smallIcon"),
            "featured": None,
            "background": background_path(rarity, None),
        },
        "owned_styles": [],
        "is_exclusive": False,
        "is_mythic": cid in MYTHIC_SET,
        "in_catalog": True,
    }


# Locker Service slot -> /equipped field
EQUIPPED_SLOTS = {
    "LoadoutSlot_Character": "skin",
    "LoadoutSlot_Backpack": "backpack",
    "LoadoutSlot_Pickaxe": "pickaxe",
    "LoadoutSlot_Glider": "glider",
    "LoadoutSlot_Contrails": "contrail",
    "LoadoutSlot_Shoes": "shoes",
    "LoadoutSlot_Aura": "aura",
    "LoadoutSlot_Banner_Icon": "banner",
    "LoadoutSlot_LobbyMusic": "lobby_music",
    "LoadoutSlot_LoadingScreen": "loading_screen",
}
# numbered slots (LoadoutSlot_Emote_0, LoadoutSlot_Wrap_3…) become lists
EQUIPPED_LISTS = {"LoadoutSlot_Emote_": "emotes", "LoadoutSlot_Wrap_": "wraps"}


def _equipped_field(slot: str) -> str | None:
    for prefix, key in EQUIPPED_LISTS.items():
        if slot.startswith(prefix):
            return key
    return EQUIPPED_SLOTS.get(slot)


async def build_equipped(session: aiohttp.ClientSession, catalog: Catalog, loadouts: dict) -> dict:
    """Turns the Locker Service active loadouts into {field: item} with catalog data."""
    slots = []
    for loadout in loadouts.values():
        for slot in loadout.get("loadoutSlots", []):
            field = _equipped_field(slot.get("slotTemplate", "").split(":")[-1])
            item_id = slot.get("equippedItemId")
            if not field or not item_id:
                continue
            styles = [
                c["variantTag"] for c in slot.get("itemCustomizations", [])
                if c.get("variantTag") and c.get("channelTag") != "ProfileLoadout"
            ]
            slots.append((field, item_id.split(":")[-1].lower(), styles))

    cosmetic_slots = [s for s in slots if s[0] != "banner"]
    infos = await asyncio.gather(*[catalog.get(session, cid) for _, cid, _ in cosmetic_slots])

    equipped: dict = {key: None for key in EQUIPPED_SLOTS.values()}
    equipped.update({key: [] for key in EQUIPPED_LISTS.values()})
    for (field, cid, styles), info in zip(cosmetic_slots, infos):
        entry = {**cosmetic_entry(cid, styles, info, catalog.names_pt.get(cid)), "styles": styles}
        if field in EQUIPPED_LISTS.values():
            equipped[field].append(entry)
        else:
            equipped[field] = entry
    for field, cid, _ in slots:
        if field == "banner":
            entry = banner_entry(catalog, cid)
            equipped["banner"] = entry and {**entry, "styles": []}
    return equipped
