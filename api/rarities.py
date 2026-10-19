"""Rarity backgrounds: the square drawn behind each item, used by /render and served at /backgrounds."""
from pathlib import Path

SQUARES_DIR = Path(__file__).parent / "assets" / "squares"

# lowercase rarity from fortnite-api -> square file in assets/squares (also its public name in /backgrounds)
SQUARES = {
    "common": "common",
    "uncommon": "uncommon",
    "rare": "rare",
    "epic": "epic",
    "legendary": "legendary",
    "mythic": "mythic",
    "icon series": "icon-series",
    "dark series": "dark-series",
    "star wars series": "star-wars-series",
    "marvel series": "marvel-series",
    "dc series": "dc-series",
    "gaming legends series": "series",
    "shadow series": "shadow-series",
    "slurp series": "slurp-series",
    "lava series": "lava-series",
    "frozen series": "frozen-series",
    "crew series": "crew-series",
}

# public names, as in /backgrounds/icon-series.png; "series" covers series without their own square
BACKGROUNDS = {rarity.replace(" ", "-"): square for rarity, square in SQUARES.items()} | {"series": "series"}


def background_key(rarity: str, series: str | None) -> str:
    # mythic wins; then the series, since Crew items report a plain rarity (Epic, Rare…) with series "CREW SERIES"
    for key in ("mythic" if rarity.lower() == "mythic" else None, (series or "").lower(), rarity.lower()):
        if key in SQUARES:
            return key.replace(" ", "-")
    return "series" if series else "common"


def background_path(rarity: str, series: str | None) -> str:
    """Path of the background image on this API, e.g. /backgrounds/epic.png."""
    return f"/backgrounds/{background_key(rarity, series)}.png"


def square_file(key: str) -> Path:
    return SQUARES_DIR / f"{BACKGROUNDS[key]}.png"
