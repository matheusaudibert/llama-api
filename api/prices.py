"""Estimated item shop prices in V-Bucks.

fortnite-api has no price history, so items sold in the item shop are priced by type and rarity with
the shop's usual prices. Sales, bundles and collab prices are not taken into account.
"""

TIERS = ("common", "uncommon", "rare", "epic", "legendary")

# type on fortnite-api -> price per rarity tier, plus "series" for Icon, Marvel, DC, Star Wars…
PRICES = {
    "outfit": {"common": 800, "uncommon": 800, "rare": 1200, "epic": 1500, "legendary": 2000, "series": 1500},
    "backpack": {"common": 200, "uncommon": 200, "rare": 300, "epic": 400, "legendary": 500, "series": 400},
    "pickaxe": {"common": 500, "uncommon": 500, "rare": 800, "epic": 1200, "legendary": 1500, "series": 800},
    "glider": {"common": 500, "uncommon": 500, "rare": 800, "epic": 1200, "legendary": 1500, "series": 1200},
    "emote": {"common": 200, "uncommon": 200, "rare": 500, "epic": 800, "legendary": 800, "series": 500},
    "wrap": {"common": 300, "uncommon": 300, "rare": 500, "epic": 700, "legendary": 700, "series": 500},
    "contrail": {"common": 300, "uncommon": 300, "rare": 500, "epic": 700, "legendary": 700, "series": 500},
    "music": {"common": 200, "uncommon": 200, "rare": 200, "epic": 200, "legendary": 200, "series": 200},
}


def estimated_price(item_type: str | None, rarity_value: str | None) -> int | None:
    """rarity_value is fortnite-api's rarity.value (epic, icon, marvel…), before our Mythic label."""
    table = PRICES.get(item_type or "")
    if not table:
        return None
    rarity = (rarity_value or "common").lower()
    return table[rarity if rarity in TIERS else "series"]
