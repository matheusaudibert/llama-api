import aiohttp

from .epic_auth import EpicUser

ACCOUNT_URL = "https://account-public-service-prod03.ol.epicgames.com/account/api/public/account"
PROFILE_URL = "https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile"

VBUCKS_CATEGORIES = [
    "Currency:MtxPurchased",
    "Currency:MtxEarned",
    "Currency:MtxGiveaway",
    "Currency:MtxPurchaseBonus",
]

# console accounts a buyer can link, as named in externalAuths
LINKABLE_PLATFORMS = ["psn", "xbl", "nintendo"]


class EpicError(Exception):
    def __init__(self, what: str, status: int):
        super().__init__(f"Error fetching {what} ({status})")
        self.status = status


def _auth(user: EpicUser) -> dict:
    return {"Authorization": f"bearer {user.access_token}"}


async def query_profile(session: aiohttp.ClientSession, user: EpicUser, profile_id: str) -> dict:
    async with session.post(
        f"{PROFILE_URL}/{user.account_id}/client/QueryProfile?profileId={profile_id}&rvn=-1",
        headers={**_auth(user), "Content-Type": "application/json"},
        json={},
    ) as resp:
        if resp.status != 200:
            raise EpicError(f"{profile_id} profile", resp.status)
        data = await resp.json()
        return data.get("profileChanges", [{}])[0].get("profile", {})


async def get_account_info(session: aiohttp.ClientSession, user: EpicUser) -> dict:
    async with session.get(f"{ACCOUNT_URL}/{user.account_id}", headers=_auth(user)) as resp:
        if resp.status != 200:
            raise EpicError("account info", resp.status)
        return await resp.json()


async def get_external_auths(session: aiohttp.ClientSession, user: EpicUser) -> list:
    async with session.get(f"{ACCOUNT_URL}/{user.account_id}/externalAuths", headers=_auth(user)) as resp:
        if resp.status != 200:
            return []
        return await resp.json()


def get_vbucks(common_core: dict) -> int:
    return sum(
        item.get("quantity", 0)
        for item in common_core.get("items", {}).values()
        if item.get("templateId") in VBUCKS_CATEGORIES
    )


def get_vbucks_by_platform(common_core: dict) -> dict:
    """{platform: quantity}. V-Bucks bought on one platform can only be spent there; "Shared" works everywhere."""
    result: dict[str, int] = {}
    for item in common_core.get("items", {}).values():
        if item.get("templateId") in VBUCKS_CATEGORIES:
            platform = item.get("attributes", {}).get("platform", "Shared")
            result[platform] = result.get(platform, 0) + item.get("quantity", 0)
    return result


def get_purchase_info(common_core: dict) -> dict:
    attributes = common_core.get("stats", {}).get("attributes", {})
    history = attributes.get("mtx_purchase_history", {})
    return {
        "mtx_platform": attributes.get("current_mtx_platform"),
        "refund_credits": history.get("refundCredits", 0),
        "refunds_used": history.get("refundsUsed", 0),
    }


def get_linkable_platforms(external_auths: list) -> list:
    linked = {a.get("type") for a in external_auths}
    return [p for p in LINKABLE_PLATFORMS if p not in linked]


def get_banner_ids(common_core: dict) -> list:
    result = []
    for item in common_core.get("items", {}).values():
        template_id = item.get("templateId", "").lower()
        if template_id.startswith("homebasebanner:") or template_id.startswith("homebasebannericon:"):
            splitted = template_id.split(":")
            if len(splitted) == 2:
                result.append(splitted[1])
    return result


def get_account_stats(athena: dict) -> dict:
    attributes   = athena.get("stats", {}).get("attributes", {})
    past_seasons = attributes.get("past_seasons", [])

    return {
        "account_level": attributes.get("accountLevel", 0),
        "lifetime_wins": attributes.get("lifetime_wins", 0),
        "total_wins": sum(s.get("numWins", 0) for s in past_seasons),
        "total_matches": sum(s.get("numHighBracket", 0) + s.get("numLowBracket", 0) for s in past_seasons),
        "last_match_end": attributes.get("last_match_end_datetime"),
        "current_season": {
            "season": attributes.get("season_num"),
            "level": attributes.get("level"),
            # Epic only sends book_purchased when the pass was bought
            "battle_pass_purchased": attributes.get("book_purchased", False),
            "wins": attributes.get("season", {}).get("numWins", 0),
        },
        "past_seasons": [
            {
                "season": s.get("seasonNumber"),
                "level": s.get("seasonLevel"),
                "battle_pass_purchased": s.get("purchasedVIP", False),
                "wins": s.get("numWins", 0),
            }
            for s in past_seasons
        ],
    }
