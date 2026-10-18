import asyncio
import os
import platform
import time

import aiohttp

# Epic OAuth clients, as base64 "client_id:client_secret". Never hardcode them: they come from the environment
SWITCH_TOKEN = os.environ.get("EPIC_SWITCH_CLIENT", "")
IOS_TOKEN    = os.environ.get("EPIC_IOS_CLIENT", "")

OAUTH_URL = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth"
OAUTH_URL_03 = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth"


class DeviceCodeExpired(Exception):
    pass


class EpicUser:
    def __init__(self, data: dict = {}):
        self.raw = data
        self.access_token  = data.get("access_token", "")
        self.expires_in    = data.get("expires_in", 0)
        self.expires_at    = data.get("expires_at", "")
        self.token_type    = data.get("token_type", "")
        self.refresh_token = data.get("refresh_token", "")
        self.refresh_expires    = data.get("refresh_expires", "")
        self.refresh_expires_at = data.get("refresh_expires_at", "")
        self.account_id    = data.get("account_id", "")
        self.client_id     = data.get("client_id", "")
        self.internal_client = data.get("internal_client", False)
        self.client_service   = data.get("client_service", "")
        self.display_name     = data.get("displayName", "")
        self.app              = data.get("app", "")
        self.in_app_id        = data.get("in_app_id", "")


class EpicGenerator:
    def __init__(self) -> None:
        self.http: aiohttp.ClientSession
        self.user_agent = f"DeviceAuthGenerator/{platform.system()}/{platform.version()}"
        self.access_token = ""

    async def start(self) -> None:
        self.http = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        self.access_token = await self.get_access_token()

    async def close(self) -> None:
        await self.http.close()

    async def get_access_token(self) -> str:
        async with self.http.post(
            f"{OAUTH_URL}/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"basic {SWITCH_TOKEN}",
            },
            data={"grant_type": "client_credentials"},
        ) as response:
            data = await response.json()
            return data["access_token"]

    async def create_device_code(self) -> dict:
        async with self.http.post(
            f"{OAUTH_URL_03}/deviceAuthorization",
            headers={
                "Authorization": f"bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        ) as response:
            data = await response.json()
            return {
                "verification_url": data["verification_uri_complete"],
                "device_code": data["device_code"],
                "expires_in": data.get("expires_in", 600),
                "interval": data.get("interval", 5),
            }

    async def poll_device_code(self, device_code: str, expires_in: int, interval: int = 5) -> EpicUser:
        deadline = time.monotonic() + expires_in
        while True:
            async with self.http.post(
                f"{OAUTH_URL_03}/token",
                headers={
                    "Authorization": f"basic {SWITCH_TOKEN}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "device_code", "device_code": device_code},
            ) as request:
                token = await request.json()
                if request.status == 200:
                    break
                error_code = token.get("errorCode", "")
                if "not_found" in error_code or "expired" in error_code:
                    raise DeviceCodeExpired(error_code)

            if time.monotonic() >= deadline:
                raise DeviceCodeExpired("device code expired")
            await asyncio.sleep(interval)

        async with self.http.get(
            f"{OAUTH_URL_03}/exchange",
            headers={"Authorization": f"bearer {token['access_token']}"},
        ) as request:
            exchange = await request.json()

        async with self.http.post(
            f"{OAUTH_URL_03}/token",
            headers={
                "Authorization": f"basic {IOS_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "exchange_code",
                "exchange_code": exchange["code"],
                # a JWT (eg1) token: EOS Connect, used by /equipped, refuses opaque tokens
                "token_type": "eg1",
            },
        ) as request:
            auth_information = await request.json()

        # the Switch token is only a stepping stone to the iOS one
        await kill_token(self.http, token["access_token"])
        return EpicUser(data=auth_information)


async def kill_token(session: aiohttp.ClientSession, access_token: str) -> int:
    """Revokes the token at Epic. Returns the HTTP status (204 when it worked)."""
    async with session.delete(
        f"{OAUTH_URL}/sessions/kill/{access_token}",
        headers={"Authorization": f"bearer {access_token}"},
    ) as resp:
        return resp.status
