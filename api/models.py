from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DeviceLoginResponse(BaseModel):
    session_id: str = Field(description="Opaque ID used in every other call of this login.")
    verification_url: str = Field(description="Epic Games page where the player authorizes the login.")
    expires_in: int = Field(description="Seconds until the verification link expires.")


class LoginStatusResponse(BaseModel):
    status: Literal["pending", "completed", "expired", "error"] = Field(description="Current login state.")
    account_id: str | None = Field(None, description="Epic account ID. Present when `completed`.")
    display_name: str | None = Field(None, description="Account display name. Present when `completed`.")
    error: str | None = Field(None, description="Error message when `error`.")


class ExternalAuth(BaseModel):
    type: str | None = Field(None, description="Platform, e.g. psn, xbl, nintendo, github, steam.")
    display_name: str | None = Field(None, description="Player name on the platform.")
    date_added: str | None = Field(None, description="When the platform was connected (ISO 8601).")


class PastSeason(BaseModel):
    season: int | None = Field(None, description="Season number.")
    level: int | None = Field(None, description="Level reached in the season.")
    battle_pass_purchased: bool = Field(False, description="Whether the battle pass was purchased.")
    wins: int = Field(0, description="Wins in the season.")


class AccountSummary(BaseModel):
    account_id: str
    display_name: str
    email: str | None = Field(None, description="Unmasked email. Mask it before showing it in public channels.")
    email_verified: bool
    name: str | None = None
    last_name: str | None = None
    country: str | None = Field(None, description="Country code (ISO 3166-1 alpha-2).")
    tfa_enabled: bool = Field(description="Whether two-factor authentication is on.")
    minor_verified: bool = Field(description="Whether the account has parental controls / minor verification.")
    profile_created: str | None = Field(None, description="When the account started playing Fortnite: the Fortnite profile creation date (ISO 8601). Epic does not share the Epic account creation date.")
    last_login: str | None = Field(None, description="Last login to the Epic account (ISO 8601).")
    can_change_display_name: bool = Field(description="Whether the display name can be changed right now.")
    display_name_changes: int = Field(description="How many times the display name was changed.")
    last_display_name_change: str | None = Field(None, description="Last display name change (ISO 8601).")
    display_name_change_available_at: str | None = Field(None, description="When a locked display name can be changed again (ISO 8601). Null when it can be changed now.")
    can_change_email: bool | None = Field(None, description="Whether the email can be changed right now. Null when Epic did not answer.")
    last_email_change: str | None = Field(None, description="Last email change (ISO 8601).")
    email_change_available_at: str | None = Field(None, description="When a locked email can be changed again (ISO 8601). Null when it can be changed now.")
    vbucks: int = Field(description="Total V-Bucks across all sources.")
    vbucks_by_platform: dict[str, int] = Field(description="V-Bucks per platform, e.g. {\"Shared\": 100, \"PSN\": 3300}. Platform V-Bucks can only be spent on that platform.")
    mtx_platform: str | None = Field(None, description="Platform the V-Bucks purchases are tied to, e.g. EpicPC, PSN, Live.")
    refund_credits: int = Field(description="Refund tickets left.")
    refunds_used: int = Field(description="Refund tickets already used.")
    external_auths: list[ExternalAuth] = Field(description="Every platform or sign-in provider linked to the account, as Epic reports it (psn, xbl, nintendo, steam, github, twitch, google, apple…).")
    linkable_platforms: list[str] = Field(description="Platforms that can be linked on epicgames.com (psn, xbl, nintendo, steam, github, twitch) and are not linked to the account yet, so a new owner can link them.")
    account_level: int
    lifetime_wins: int = Field(description="Wins over the whole account, current season included.")
    total_wins: int = Field(description="Wins summed over all past seasons.")
    total_matches: int = Field(description="Matches summed over all past seasons.")
    last_match_end: str | None = Field(None, description="End of the last match played (ISO 8601).")
    current_season: PastSeason = Field(description="Current season: number, level, battle pass and wins.")
    past_seasons: list[PastSeason]


class CosmeticImages(BaseModel):
    icon: str | None = None
    small_icon: str | None = None
    featured: str | None = None
    background: str | None = Field(None, description="Rarity background (the square behind the item), served by this API. Draw `icon` on top of it.")


class Cosmetic(BaseModel):
    id: str = Field(description="Lowercase cosmetic ID, e.g. cid_028_athena_commando_f.")
    name: str = Field(description="Item name. Same as `id` when the item is not in the catalog.")
    name_pt: str = Field(description="Item name in Brazilian Portuguese. Same as `name` when there is no translation yet.")
    rarity: str = Field(description="Common, Uncommon, Rare, Epic, Legendary, Mythic or a series, such as Icon Series.")
    series: str | None = Field(None, description="Item series, if any.")
    type: str | None = Field(None, description="Type on fortnite-api, e.g. outfit, backpack, pickaxe, emote, glider.")
    images: CosmeticImages
    owned_styles: list[str] = Field(description="Tags of the styles the player unlocked.")
    is_exclusive: bool = Field(description="Part of the exclusive items list (Renegade Raider, Ghoul Trooper…).")
    is_mythic: bool = Field(description="Rare/OG item: on the rare items list and out of the shop for 2 years, or with the original owners' exclusive style.")
    from_shop: bool = Field(False, description="Sold in the item shop at least once. Battle pass, packs and promotional items are not.")
    estimated_price: int | None = Field(None, description="Estimated item shop price in V-Bucks, from the usual price for its type and rarity. Null when the item is not from the shop or its type is not sold alone.")
    in_catalog: bool = Field(description="False when fortnite-api has no data for this item yet.")


class EquippedCosmetic(BaseModel):
    id: str = Field(description="Lowercase cosmetic ID, e.g. cid_028_athena_commando_f.")
    name: str = Field(description="Item name. Same as `id` when the item is not in the catalog.")
    name_pt: str = Field(description="Item name in Brazilian Portuguese. Same as `name` when there is no translation yet.")
    rarity: str = Field(description="Common, Uncommon, Rare, Epic, Legendary, Mythic or a series, such as Icon Series.")
    series: str | None = Field(None, description="Item series, if any.")
    type: str | None = Field(None, description="Type on fortnite-api, e.g. outfit, backpack, pickaxe, emote, glider.")
    images: CosmeticImages
    styles: list[str] = Field(description="Tags of the styles selected on the equipped item.")
    is_mythic: bool = Field(description="Rare/OG item: on the rare items list and out of the shop for 2 years, or with the original owners' exclusive style.")
    from_shop: bool = Field(False, description="Sold in the item shop at least once. Battle pass, packs and promotional items are not.")
    estimated_price: int | None = Field(None, description="Estimated item shop price in V-Bucks, from the usual price for its type and rarity. Null when the item is not from the shop or its type is not sold alone.")
    in_catalog: bool = Field(description="False when fortnite-api has no data for this item yet.")


class Equipped(BaseModel):
    skin: EquippedCosmetic | None = None
    backpack: EquippedCosmetic | None = None
    pickaxe: EquippedCosmetic | None = None
    glider: EquippedCosmetic | None = None
    contrail: EquippedCosmetic | None = None
    shoes: EquippedCosmetic | None = None
    aura: EquippedCosmetic | None = None
    emotes: list[EquippedCosmetic] = Field(description="Emotes in the emote wheel, in slot order. Empty slots are skipped.")
    wraps: list[EquippedCosmetic] = Field(description="Wraps, in slot order. Empty slots are skipped.")
    banner: EquippedCosmetic | None = None
    lobby_music: EquippedCosmetic | None = None
    loading_screen: EquippedCosmetic | None = None


class LockerCounts(BaseModel):
    skins: int
    backpacks: int
    pickaxes: int
    emotes: int
    gliders: int
    wraps: int
    sprays: int
    others: int
    banners: int


class ShopSummary(BaseModel):
    counts: LockerCounts = Field(description="Items sold in the item shop, per category.")
    estimated_vbucks: int = Field(description="Sum of `estimated_price` over every shop item: a rough value of the locker, not what was paid.")


class Locker(BaseModel):
    counts: LockerCounts = Field(description="Item count per category.")
    shop: ShopSummary = Field(description="Items from the item shop and their estimated value.")
    skins: list[Cosmetic]
    backpacks: list[Cosmetic]
    pickaxes: list[Cosmetic]
    emotes: list[Cosmetic]
    gliders: list[Cosmetic]
    wraps: list[Cosmetic]
    sprays: list[Cosmetic]
    others: list[Cosmetic]
    banners: list[Cosmetic]


class RenderCategory(str, Enum):
    skins = "skins"
    backpacks = "backpacks"
    pickaxes = "pickaxes"
    gliders = "gliders"
    emotes = "emotes"
    mythics = "mythics"


class RenderItem(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$", description="Cosmetic ID, as returned by `/locker`.")
    owned_styles: list[str] = Field(default_factory=list, description="Unlocked styles. Used to recognize OGs.")


class RenderRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=64, description="Account nickname, shown in the header.")
    language: Literal["en", "pt-BR"] = Field("en", description="Language of the image: the header (LOCKER / ARMÁRIO, the category name) and the item names on the cards.")
    items: list[RenderItem] = Field(
        max_length=5000,
        description="Account items. You can send the `/locker` items as they are: extra fields are ignored and only the requested category is drawn.",
    )


class Health(BaseModel):
    status: Literal["ok"]
    cosmetics_loaded: int = Field(description="Cosmetics in the in-memory catalog.")
    active_sessions: int = Field(description="Login sessions in memory.")


class ErrorResponse(BaseModel):
    detail: str
