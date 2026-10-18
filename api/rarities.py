"""Rarity backgrounds: the square drawn behind each item, used by /render and served at /backgrounds."""
from pathlib import Path

SQUARES_DIR = Path(__file__).parent / "assets" / "squares"

# lowercase rarity from fortnite-api -> square file in assets/squares
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

# public names, as in /backgrounds/icon-series.png; "series" covers series without their own square
BACKGROUNDS = {rarity.replace(" ", "-"): square for rarity, square in SQUARES.items()} | {"series": "serie"}


def background_key(rarity: str, series: str | None) -> str:
    key = rarity.lower()
    if key in SQUARES:
        return key.replace(" ", "-")
    return "series" if series else "common"


def background_path(rarity: str, series: str | None) -> str:
    """Path of the background image on this API, e.g. /backgrounds/epic.png."""
    return f"/backgrounds/{background_key(rarity, series)}.png"


def square_file(key: str) -> Path:
    return SQUARES_DIR / f"{BACKGROUNDS[key]}.png"
